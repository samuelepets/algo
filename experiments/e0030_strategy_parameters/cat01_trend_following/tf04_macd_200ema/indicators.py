"""Technical indicators for tf04_macd_200ema.

Pure Numba kernels: EMA, ATR, and MACD (line / signal / histogram).
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14


@njit(cache=True)
def ema(close: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average with SMA seed at index ``period - 1``."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan

    if n < period or period == 0:
        return out

    seed = 0.0
    for i in range(period):
        seed += close[i]
    seed /= period
    out[period - 1] = seed

    k = 2.0 / (period + 1.0)
    for i in range(period, n):
        out[i] = out[i - 1] + k * (close[i] - out[i - 1])

    return out


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
def ema_of_series(series: np.ndarray, period: int) -> np.ndarray:
    """EMA over a series that may have a leading NaN prefix.

    Seeds with the SMA of the first ``period`` non-NaN values and applies the
    standard EMA recurrence afterwards.
    """
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if period == 0:
        return out

    first = -1
    for i in range(n):
        if not np.isnan(series[i]):
            first = i
            break
    if first < 0 or first + period > n:
        return out

    seed = 0.0
    for i in range(first, first + period):
        seed += series[i]
    seed /= period
    out[first + period - 1] = seed

    k = 2.0 / (period + 1.0)
    for i in range(first + period, n):
        out[i] = out[i - 1] + k * (series[i] - out[i - 1])
    return out


@njit(cache=True)
def macd(
    close: np.ndarray, fast: int, slow: int, signal: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD line, signal line, and histogram.

    ``macd_line = EMA(fast) - EMA(slow)``; ``signal = EMA(macd_line, signal)``;
    ``hist = macd_line - signal``.
    """
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    n = len(close)
    macd_line = np.empty(n, dtype=np.float64)
    for i in range(n):
        if np.isnan(fast_ema[i]) or np.isnan(slow_ema[i]):
            macd_line[i] = np.nan
        else:
            macd_line[i] = fast_ema[i] - slow_ema[i]
    signal_line = ema_of_series(macd_line, signal)
    hist = np.empty(n, dtype=np.float64)
    for i in range(n):
        if np.isnan(macd_line[i]) or np.isnan(signal_line[i]):
            hist[i] = np.nan
        else:
            hist[i] = macd_line[i] - signal_line[i]
    return macd_line, signal_line, hist


def build_ema_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute EMAs for all ``periods`` into a 2-D matrix ``[n_periods, n_bars]``."""
    unique = sorted(set(periods))
    matrix = np.empty((len(unique), len(close)), dtype=np.float64)
    index: dict[int, int] = {}
    for row, period in enumerate(unique):
        matrix[row] = ema(close, period)
        index[period] = row
    return matrix, index
