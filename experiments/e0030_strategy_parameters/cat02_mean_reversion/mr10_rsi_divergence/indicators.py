"""Technical indicators for mr10_rsi_divergence.

Wilder RSI, Wilder ATR, and fractal-style swing pivot (low/high) detection.

Pivot semantics: a bar ``p`` is a pivot low if ``low[p]`` is the minimum of the
window ``low[p - lookback : p + lookback + 1]`` (inclusive on both sides), with
ties broken in favour of the *last* bar achieving the minimum within that
window. Because the window extends ``lookback`` bars into the future, a pivot
at index ``p`` is only knowable — without lookahead — starting at bar
``p + lookback``. Callers (the backtest engine) must respect this and only
treat a pivot as "confirmed" once that many bars have elapsed.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
RSI_PERIODS = [7, 10, 14]
SWING_LOOKBACKS = [3, 5, 8, 10]


@njit(cache=True)
def rsi(close: np.ndarray, period: int) -> np.ndarray:
    """Wilder RSI. First valid value at index ``period`` (needs period+1 closes)."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period + 1 or period < 1:
        return out

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        diff = close[i] - close[i - 1]
        if diff > 0.0:
            gains += diff
        else:
            losses += -diff
    avg_gain = gains / period
    avg_loss = losses / period

    def _rsi_val(ag: float, al: float) -> float:
        if al < 1e-12:
            return 100.0
        rs = ag / al
        return 100.0 - 100.0 / (1.0 + rs)

    out[period] = _rsi_val(avg_gain, avg_loss)

    for i in range(period + 1, n):
        diff = close[i] - close[i - 1]
        gain = diff if diff > 0.0 else 0.0
        loss = -diff if diff < 0.0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_val(avg_gain, avg_loss)

    return out


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < 2 or period == 0:
        return out
    tr = np.empty(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)
    if n < period:
        return out
    seed = 0.0
    for i in range(period):
        seed += tr[i]
    seed /= period
    out[period - 1] = seed
    k = 1.0 / period
    for i in range(period, n):
        out[i] = out[i - 1] + k * (tr[i] - out[i - 1])
    return out


@njit(cache=True)
def pivot_lows(low: np.ndarray, lookback: int) -> np.ndarray:
    """Fractal swing-low detector. ``out[p] = low[p]`` if p is a pivot low, else NaN.

    Only indices ``p`` in ``[lookback, n - 1 - lookback]`` can be evaluated
    (the window must fit fully inside the array).
    """
    n = len(low)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if lookback < 1 or n < 2 * lookback + 1:
        return out
    for p in range(lookback, n - lookback):
        m = low[p]
        for q in range(p - lookback, p + lookback + 1):
            if low[q] < m:
                m = low[q]
        if low[p] != m:
            continue
        tie = False
        for q in range(p + 1, p + lookback + 1):
            if low[q] == m:
                tie = True
                break
        if tie:
            continue
        out[p] = low[p]
    return out


@njit(cache=True)
def pivot_highs(high: np.ndarray, lookback: int) -> np.ndarray:
    """Fractal swing-high detector, mirror of :func:`pivot_lows`."""
    n = len(high)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if lookback < 1 or n < 2 * lookback + 1:
        return out
    for p in range(lookback, n - lookback):
        m = high[p]
        for q in range(p - lookback, p + lookback + 1):
            if high[q] > m:
                m = high[q]
        if high[p] != m:
            continue
        tie = False
        for q in range(p + 1, p + lookback + 1):
            if high[q] == m:
                tie = True
                break
        if tie:
            continue
        out[p] = high[p]
    return out


def build_rsi_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute RSI for all unique periods. Returns ``(matrix, period_index)``."""
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = rsi(close, p)
        period_index[p] = row
    return matrix, period_index


def build_pivot_cache(
    high: np.ndarray, low: np.ndarray, lookbacks: list[int]
) -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    """Precompute pivot-low/high arrays for all unique lookbacks.

    Returns ``(pivot_low_matrix, pivot_high_matrix, lookback_index)``.
    """
    unique_lb = sorted(set(lookbacks))
    n = len(high)
    pl_matrix = np.empty((len(unique_lb), n), dtype=np.float64)
    ph_matrix = np.empty((len(unique_lb), n), dtype=np.float64)
    lookback_index: dict[int, int] = {}
    for row, lb in enumerate(unique_lb):
        pl_matrix[row] = pivot_lows(low, lb)
        ph_matrix[row] = pivot_highs(high, lb)
        lookback_index[lb] = row
    return pl_matrix, ph_matrix, lookback_index
