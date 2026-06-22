"""Technical indicators for tf17_donchian.

ATR (Wilder) and Donchian channel (rolling max/min).
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14


@njit(cache=True)
def atr(high, low, close, period):
    """Wilder ATR."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n): out[i] = np.nan
    if n < 2 or period == 0: return out
    tr = np.empty(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)
    if n < period: return out
    seed = 0.0
    for i in range(period): seed += tr[i]
    seed /= period
    out[period-1] = seed
    k = 1.0 / period
    for i in range(period, n):
        out[i] = out[i-1] + k * (tr[i] - out[i-1])
    return out


@njit(cache=True)
def donchian_upper(high, period):
    """Rolling max of High over the previous ``period`` bars (exclusive of current)."""
    n = len(high)
    out = np.empty(n, dtype=np.float64)
    for i in range(n): out[i] = np.nan
    for i in range(period, n):
        mx = high[i - period]
        for j in range(1, period):
            if high[i - period + j] > mx:
                mx = high[i - period + j]
        out[i] = mx
    return out


@njit(cache=True)
def donchian_lower(low, period):
    """Rolling min of Low over the previous ``period`` bars (exclusive of current)."""
    n = len(low)
    out = np.empty(n, dtype=np.float64)
    for i in range(n): out[i] = np.nan
    for i in range(period, n):
        mn = low[i - period]
        for j in range(1, period):
            if low[i - period + j] < mn:
                mn = low[i - period + j]
        out[i] = mn
    return out


def build_donchian_cache(high, low, entry_periods, exit_periods):
    """Precompute Donchian upper/lower for all unique periods.

    Returns (upper_matrix, lower_matrix, index_dict).
    """
    all_periods = sorted(set(entry_periods) | set(exit_periods))
    n = len(high)
    upper_matrix = np.empty((len(all_periods), n), dtype=np.float64)
    lower_matrix = np.empty((len(all_periods), n), dtype=np.float64)
    index = {}
    for row, p in enumerate(all_periods):
        upper_matrix[row] = donchian_upper(high, p)
        lower_matrix[row] = donchian_lower(low, p)
        index[p] = row
    return upper_matrix, lower_matrix, index
