"""Technical indicators for tf19_roc_breakout.

ATR (Wilder) and Rate of Change (ROC).
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14

ROC_FILTER_NONE = 0


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
def roc(close, period):
    """Rate of Change: ((Close[i] - Close[i-period]) / Close[i-period]) * 100."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n): out[i] = np.nan
    for i in range(period, n):
        prev = close[i - period]
        if prev != 0.0:
            out[i] = (close[i] - prev) / prev * 100.0
    return out


def build_roc_cache(close, periods):
    """Precompute ROC for all unique periods; return (matrix, index_dict)."""
    unique = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique), n), dtype=np.float64)
    index = {}
    for row, p in enumerate(unique):
        matrix[row] = roc(close, p)
        index[p] = row
    return matrix, index
