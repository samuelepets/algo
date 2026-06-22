"""Technical indicators for tf14_hma.

Pure Numba kernels: ATR, the Weighted Moving Average (WMA) and the Hull Moving
Average (HMA).
"""

from __future__ import annotations

import math

import numpy as np
from numba import njit

ATR_PERIOD = 14


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Average True Range with Wilder smoothing."""
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
def wma(series: np.ndarray, period: int) -> np.ndarray:
    """Weighted moving average with linear weights 1..period (most recent heaviest)."""
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if period == 0 or n < period:
        return out
    denom = period * (period + 1) / 2.0
    for i in range(period - 1, n):
        acc = 0.0
        valid = True
        for j in range(period):
            v = series[i - period + 1 + j]
            if np.isnan(v):
                valid = False
                break
            acc += v * (j + 1)
        out[i] = acc / denom if valid else np.nan
    return out


@njit(cache=True)
def hma(close: np.ndarray, period: int) -> np.ndarray:
    """Hull MA: ``WMA(2·WMA(n/2) − WMA(n), round(sqrt(n)))``."""
    n = len(close)
    if period < 2:
        out = np.empty(n, dtype=np.float64)
        for i in range(n):
            out[i] = np.nan
        return out
    half = period // 2
    sqrt_p = int(round(period**0.5))
    if sqrt_p < 1:
        sqrt_p = 1
    wma_half = wma(close, half)
    wma_full = wma(close, period)
    raw = np.empty(n, dtype=np.float64)
    for i in range(n):
        if np.isnan(wma_half[i]) or np.isnan(wma_full[i]):
            raw[i] = np.nan
        else:
            raw[i] = 2.0 * wma_half[i] - wma_full[i]
    return wma(raw, sqrt_p)


def hma_warmup(period: int) -> int:
    """Bars before HMA(period) is defined."""
    return period + int(round(math.sqrt(period)))


def build_hma_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute HMA for all ``periods`` into a 2-D matrix ``[n_periods, n_bars]``."""
    unique = sorted(set(periods))
    matrix = np.empty((len(unique), len(close)), dtype=np.float64)
    index: dict[int, int] = {}
    for row, period in enumerate(unique):
        matrix[row] = hma(close, period)
        index[period] = row
    return matrix, index
