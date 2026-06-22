"""Technical indicators for tf10_parabolic_sar.

Pure Numba kernels: EMA and the Parabolic SAR (stop-and-reverse) line / direction.
"""

from __future__ import annotations

import numpy as np
from numba import njit


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
def parabolic_sar(
    high: np.ndarray,
    low: np.ndarray,
    af_start: float,
    af_step: float,
    af_max: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Parabolic SAR line and direction (+1 long, -1 short, 0 = warmup).

    Wilder's stop-and-reverse: the SAR accelerates toward the extreme price as the
    trend extends and flips side when price crosses it.
    """
    n = len(high)
    sar = np.empty(n, dtype=np.float64)
    direction = np.zeros(n, dtype=np.int64)
    for i in range(n):
        sar[i] = np.nan
    if n < 3:
        return sar, direction

    long_pos = high[1] >= high[0]
    if long_pos:
        sar_v = low[0]
        ep = high[1] if high[1] > high[0] else high[0]
    else:
        sar_v = high[0]
        ep = low[1] if low[1] < low[0] else low[0]
    af = af_start
    direction[1] = 1 if long_pos else -1
    sar[1] = sar_v

    for i in range(2, n):
        sar_v = sar_v + af * (ep - sar_v)
        if long_pos:
            if sar_v > low[i - 1]:
                sar_v = low[i - 1]
            if sar_v > low[i - 2]:
                sar_v = low[i - 2]
            if low[i] < sar_v:
                long_pos = False
                sar_v = ep
                ep = low[i]
                af = af_start
                direction[i] = -1
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = af + af_step
                    if af > af_max:
                        af = af_max
                direction[i] = 1
        else:
            if sar_v < high[i - 1]:
                sar_v = high[i - 1]
            if sar_v < high[i - 2]:
                sar_v = high[i - 2]
            if high[i] > sar_v:
                long_pos = True
                sar_v = ep
                ep = high[i]
                af = af_start
                direction[i] = 1
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = af + af_step
                    if af > af_max:
                        af = af_max
                direction[i] = -1
        sar[i] = sar_v

    return sar, direction


def build_ema_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute EMAs into a 2-D matrix ``[n_periods, n_bars]``."""
    unique = sorted(set(periods))
    matrix = np.empty((len(unique), len(close)), dtype=np.float64)
    index: dict[int, int] = {}
    for row, period in enumerate(unique):
        matrix[row] = ema(close, period)
        index[period] = row
    return matrix, index
