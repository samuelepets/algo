"""Technical indicators for mr07_williams_r.

Williams %R and Wilder ATR.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
WR_PERIODS = [5, 10, 14, 20]


@njit(cache=True)
def williams_r(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Williams %R: (HighestHigh[n] - Close) / (HighestHigh[n] - LowestLow[n]) * -100.

    Range is [-100, 0]. NaN during warm-up and when the n-bar range is ~0.
    """
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out
    for i in range(period - 1, n):
        hh = high[i - period + 1]
        ll = low[i - period + 1]
        for j in range(i - period + 2, i + 1):
            if high[j] > hh:
                hh = high[j]
            if low[j] < ll:
                ll = low[j]
        rng = hh - ll
        if rng < 1e-12:
            out[i] = np.nan
        else:
            out[i] = (hh - close[i]) / rng * -100.0
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


def build_wr_cache(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute Williams %R arrays for all unique periods.

    Returns ``(wr_matrix, period_index)`` where each matrix row corresponds to
    one period and ``period_index[p]`` gives the row.
    """
    unique_periods = sorted(set(periods))
    n = len(close)
    wr_matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        wr_matrix[row] = williams_r(high, low, close, p)
        period_index[p] = row
    return wr_matrix, period_index
