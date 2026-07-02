"""Technical indicators for mr05_stochastic_reversion.

Wilder ATR, generic rolling SMA, raw Stochastic %K, and a precomputation cache
for the (smoothed %K, %D) pairs used by the slow-stochastic reversion signal.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
K_PERIODS = [5, 9, 14, 21]
D_PERIODS = [3, 5]
SLOWINGS = [1, 3]


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR (copied verbatim from mr01_bollinger_band/indicators.py)."""
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
def sma(series: np.ndarray, period: int) -> np.ndarray:
    """Rolling SMA via direct per-window sum (not a sliding accumulator).

    ``mr01``'s ``sma`` uses a sliding-window accumulator (``s += x[i] -
    x[i-period]``) that is fast but has a NaN-propagation pitfall: once the
    accumulator is contaminated by a single NaN input it stays NaN forever,
    because IEEE-754 arithmetic never "cancels out" a NaN term. That is
    harmless in mr01 because ``sma`` there is only ever applied to raw close
    prices (never NaN). Here it is also applied to ``stoch_raw_k`` output and
    to the smoothed %K series, both of which carry NaN warm-up prefixes (and,
    in degenerate flat-range inputs, interior NaNs) — verified numerically
    that the accumulator form makes the *entire* output NaN in that case, not
    just the windows touching the NaN.

    This direct-sum form recomputes each window independently: a window's
    output is NaN if and only if that window contains a NaN input, and the
    output is valid again as soon as the window has fully moved past it. For
    ``period == 1`` this reduces to echoing the input value (NaN stays NaN,
    finite stays finite) — the documented "slowing=1" identity case.
    """
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out
    for i in range(period - 1, n):
        s = 0.0
        has_nan = False
        for j in range(i - period + 1, i + 1):
            v = series[j]
            if np.isnan(v):
                has_nan = True
                break
            s += v
        if not has_nan:
            out[i] = s / period
    return out


@njit(cache=True)
def stoch_raw_k(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, k_period: int
) -> np.ndarray:
    """Raw (fast) Stochastic %K.

    ``%K[i] = (close[i] - lowest_low[i-k+1..i]) / (highest_high[i-k+1..i] -
    lowest_low[i-k+1..i]) * 100``. NaN for the warm-up (``i < k_period - 1``)
    and for degenerate flat ranges (``highest_high - lowest_low`` ~ 0), to
    avoid division by zero.
    """
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < k_period or k_period < 1:
        return out
    for i in range(k_period - 1, n):
        hh = high[i - k_period + 1]
        ll = low[i - k_period + 1]
        for j in range(i - k_period + 2, i + 1):
            if high[j] > hh:
                hh = high[j]
            if low[j] < ll:
                ll = low[j]
        rng = hh - ll
        if rng < 1e-12:
            out[i] = np.nan
        else:
            out[i] = (close[i] - ll) / rng * 100.0
    return out


def build_stoch_cache(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    k_periods: list[int],
    slowings: list[int],
    d_periods: list[int],
) -> tuple[np.ndarray, np.ndarray, dict[tuple[int, int, int], int]]:
    """Precompute smoothed %K and %D for all unique (k, slowing, d) triples.

    Returns ``(smoothed_k_matrix, d_matrix, combo_index)`` where each matrix
    row corresponds to one unique ``(k_period, slowing, d_period)`` triple and
    ``combo_index[(k_period, slowing, d_period)]`` gives the row. ``raw %K``
    is computed once per unique ``k_period`` and reused across all
    ``(slowing, d_period)`` combinations that share it.
    """
    combos = sorted({(k, s, d) for k in k_periods for s in slowings for d in d_periods})
    n = len(close)
    smoothed_k_matrix = np.empty((len(combos), n), dtype=np.float64)
    d_matrix = np.empty((len(combos), n), dtype=np.float64)
    combo_index: dict[tuple[int, int, int], int] = {}
    raw_k_cache: dict[int, np.ndarray] = {}
    for row, (k_period, slowing, d_period) in enumerate(combos):
        if k_period not in raw_k_cache:
            raw_k_cache[k_period] = stoch_raw_k(high, low, close, k_period)
        raw_k = raw_k_cache[k_period]
        smoothed_k = sma(raw_k, slowing)
        d = sma(smoothed_k, d_period)
        smoothed_k_matrix[row] = smoothed_k
        d_matrix[row] = d
        combo_index[(k_period, slowing, d_period)] = row
    return smoothed_k_matrix, d_matrix, combo_index
