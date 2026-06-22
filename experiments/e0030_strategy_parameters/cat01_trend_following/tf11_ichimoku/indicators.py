"""Technical indicators for tf11_ichimoku.

Pure Numba kernels: the Ichimoku midpoint line ``(max(High, n) + min(Low, n)) / 2``
used for Tenkan-sen, Kijun-sen, and the Senkou Span B base.
"""

from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def midpoint(high: np.ndarray, low: np.ndarray, period: int) -> np.ndarray:
    """Ichimoku midpoint: ``(highest high + lowest low) / 2`` over ``period`` bars."""
    n = len(high)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if period == 0 or n < period:
        return out
    for i in range(period - 1, n):
        hmax = high[i - period + 1]
        lmin = low[i - period + 1]
        for j in range(i - period + 2, i + 1):
            if high[j] > hmax:
                hmax = high[j]
            if low[j] < lmin:
                lmin = low[j]
        out[i] = (hmax + lmin) / 2.0
    return out


def build_midpoint_cache(
    high: np.ndarray, low: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute midpoint lines for all ``periods`` into a 2-D matrix."""
    unique = sorted(set(periods))
    matrix = np.empty((len(unique), len(high)), dtype=np.float64)
    index: dict[int, int] = {}
    for row, period in enumerate(unique):
        matrix[row] = midpoint(high, low, period)
        index[period] = row
    return matrix, index
