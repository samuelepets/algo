"""Technical indicators for tf18_nbar_breakout.

ATR (Wilder), rolling N-bar high/low breakout levels, and volume average.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14

CONFIRM_CLOSE = 0  # Close exceeds previous N-bar high/low
CONFIRM_HIGH = 1   # High/Low exceeds previous N-bar high/low (intra-bar)


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
def rolling_max(high, period):
    """Max of high[i-period .. i-1] (exclusive of current bar)."""
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
def rolling_min(low, period):
    """Min of low[i-period .. i-1] (exclusive of current bar)."""
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


@njit(cache=True)
def rolling_vol_avg(volume, period):
    """Simple average of volume over previous ``period`` bars (exclusive of current)."""
    n = len(volume)
    out = np.empty(n, dtype=np.float64)
    for i in range(n): out[i] = np.nan
    for i in range(period, n):
        s = 0.0
        for j in range(period):
            s += volume[i - period + j]
        out[i] = s / period
    return out


def build_breakout_cache(high, low, volume, periods):
    """Precompute rolling_max, rolling_min, vol_avg for all unique periods."""
    unique = sorted(set(periods))
    n = len(high)
    max_matrix = np.empty((len(unique), n), dtype=np.float64)
    min_matrix = np.empty((len(unique), n), dtype=np.float64)
    vol_matrix = np.empty((len(unique), n), dtype=np.float64)
    index = {}
    for row, p in enumerate(unique):
        max_matrix[row] = rolling_max(high, p)
        min_matrix[row] = rolling_min(low, p)
        vol_matrix[row] = rolling_vol_avg(volume, p)
        index[p] = row
    return max_matrix, min_matrix, vol_matrix, index
