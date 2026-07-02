"""Technical indicators for mr20_tema_distance.

TEMA (Triple EMA): TEMA = 3*EMA1 - 3*EMA2 + EMA3, where EMA1 = EMA(close, n),
EMA2 = EMA(EMA1, n), EMA3 = EMA(EMA2, n). Plus Wilder ATR for the distance
unit and stop.
"""

from __future__ import annotations

import numpy as np
from numba import njit

TEMA_PERIODS = [9, 14, 21, 30]
ATR_PERIODS = [10, 14]


@njit(cache=True)
def ema(series: np.ndarray, period: int) -> np.ndarray:
    """EMA seeded with an SMA of the first ``period`` valid values.

    Supports series with leading NaNs (chained EMAs) by seeding from the
    first run of non-NaN values.
    """
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if period < 1 or n == 0:
        return out

    start = 0
    while start < n and np.isnan(series[start]):
        start += 1
    if start + period > n:
        return out

    seed = 0.0
    for i in range(start, start + period):
        seed += series[i]
    seed /= period
    idx0 = start + period - 1
    out[idx0] = seed

    mult = 2.0 / (period + 1)
    for i in range(idx0 + 1, n):
        out[i] = (series[i] - out[i - 1]) * mult + out[i - 1]
    return out


@njit(cache=True)
def tema(close: np.ndarray, period: int) -> np.ndarray:
    """Triple Exponential Moving Average: 3*EMA1 - 3*EMA2 + EMA3."""
    ema1 = ema(close, period)
    ema2 = ema(ema1, period)
    ema3 = ema(ema2, period)
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = 3.0 * ema1[i] - 3.0 * ema2[i] + ema3[i]
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


def build_tema_cache(close: np.ndarray, periods: list[int]) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute TEMA arrays for all unique periods."""
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = tema(close, p)
        period_index[p] = row
    return matrix, period_index


def build_atr_cache(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute ATR arrays for all unique periods."""
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = atr(high, low, close, p)
        period_index[p] = row
    return matrix, period_index
