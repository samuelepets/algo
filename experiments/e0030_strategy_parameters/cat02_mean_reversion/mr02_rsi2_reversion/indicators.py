"""Technical indicators for mr02_rsi2_reversion.

SMA, Wilder ATR (both copied verbatim from mr01_bollinger_band since they are
fully generic), and a new Wilder-smoothed RSI implementation.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
RSI_PERIODS = [2, 3, 4]
TREND_PERIODS = [100, 200]


@njit(cache=True)
def sma(close: np.ndarray, period: int) -> np.ndarray:
    """Rolling SMA using a sliding-window accumulator."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out
    s = 0.0
    for i in range(period):
        s += close[i]
    out[period - 1] = s / period
    for i in range(period, n):
        s += close[i] - close[i - period]
        out[i] = s / period
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
def rsi(close: np.ndarray, period: int) -> np.ndarray:
    """Wilder-smoothed RSI.

    Differencing consumes the first point, so the ``period``-bar seed average
    is built from ``gain[1..period]`` / ``loss[1..period]`` and the first
    valid output lands at index ``period`` (one bar later than a same-period
    ATR seed, which starts differencing at index 0).

    Edge cases: flat series (avg_gain == avg_loss == 0) -> RSI = 50.0
    (no movement, neutral); strictly rising series with avg_loss == 0 and
    avg_gain > 0 -> RSI = 100.0.
    """
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if period < 1 or n < period + 1:
        return out

    gain = np.zeros(n, dtype=np.float64)
    loss = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        diff = close[i] - close[i - 1]
        if diff > 0.0:
            gain[i] = diff
        elif diff < 0.0:
            loss[i] = -diff

    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(1, period + 1):
        avg_gain += gain[i]
        avg_loss += loss[i]
    avg_gain /= period
    avg_loss /= period

    if avg_loss < 1e-12:
        out[period] = 50.0 if avg_gain < 1e-12 else 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - 100.0 / (1.0 + rs)

    k = 1.0 / period
    for i in range(period + 1, n):
        avg_gain = avg_gain - avg_gain * k + gain[i]
        avg_loss = avg_loss - avg_loss * k + loss[i]
        if avg_loss < 1e-12:
            out[i] = 50.0 if avg_gain < 1e-12 else 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - 100.0 / (1.0 + rs)

    return out


def build_rsi_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute RSI arrays for all unique periods.

    Returns ``(rsi_matrix, period_index)`` where each matrix row corresponds
    to one period and ``period_index[p]`` gives the row.
    """
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = rsi(close, p)
        period_index[p] = row
    return matrix, period_index


def build_sma_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute SMA arrays for all unique periods (used for the trend filter).

    Returns ``(sma_matrix, period_index)`` mirroring ``build_rsi_cache``.
    """
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = sma(close, p)
        period_index[p] = row
    return matrix, period_index
