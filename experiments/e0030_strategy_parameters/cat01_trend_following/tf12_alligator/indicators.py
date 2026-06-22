"""Technical indicators for tf12_alligator.

Pure Numba kernels: ATR and the Smoothed Moving Average (SMMA / Wilder RMA) used
for the Alligator's Jaw/Teeth/Lips lines.
"""

from __future__ import annotations

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
def smma(series: np.ndarray, period: int) -> np.ndarray:
    """Smoothed Moving Average (Wilder RMA), SMA-seeded at index ``period - 1``."""
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period == 0:
        return out
    seed = 0.0
    for i in range(period):
        seed += series[i]
    seed /= period
    out[period - 1] = seed
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + series[i]) / period
    return out


def shifted(line: np.ndarray, shift: int) -> np.ndarray:
    """Shift a line forward by ``shift`` bars (the value at i comes from i-shift)."""
    n = len(line)
    out = np.full(n, np.nan, dtype=np.float64)
    if shift <= 0:
        out[:] = line
        return out
    if shift < n:
        out[shift:] = line[: n - shift]
    return out
