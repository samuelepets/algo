"""Technical indicators for tf05_ema_rsi.

Pure Numba kernels: EMA, ATR, and Wilder's RSI.
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
def rsi(close: np.ndarray, period: int) -> np.ndarray:
    """Wilder's Relative Strength Index. First valid value at index ``period``."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan

    if n < period + 1 or period == 0:
        return out

    gain_sum = 0.0
    loss_sum = 0.0
    for i in range(1, period + 1):
        delta = close[i] - close[i - 1]
        if delta > 0.0:
            gain_sum += delta
        else:
            loss_sum += -delta
    avg_gain = gain_sum / period
    avg_loss = loss_sum / period

    if avg_loss < 1e-12:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - 100.0 / (1.0 + rs)

    for i in range(period + 1, n):
        delta = close[i] - close[i - 1]
        gain = delta if delta > 0.0 else 0.0
        loss = -delta if delta < 0.0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss < 1e-12:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - 100.0 / (1.0 + rs)

    return out


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


def build_rsi_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute RSI for all ``periods`` into a 2-D matrix ``[n_periods, n_bars]``."""
    unique = sorted(set(periods))
    matrix = np.empty((len(unique), len(close)), dtype=np.float64)
    index: dict[int, int] = {}
    for row, period in enumerate(unique):
        matrix[row] = rsi(close, period)
        index[period] = row
    return matrix, index
