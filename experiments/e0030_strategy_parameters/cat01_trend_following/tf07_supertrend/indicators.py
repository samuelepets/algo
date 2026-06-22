"""Technical indicators for tf07_supertrend.

Pure Numba kernels: EMA, ATR, and the SuperTrend trailing line / direction.
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
def supertrend(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr_vals: np.ndarray,
    mult: float,
) -> tuple[np.ndarray, np.ndarray]:
    """SuperTrend line and direction (+1 bullish, -1 bearish, 0 = warmup).

    Uses the precomputed ``atr_vals`` (any ATR period). The line is the active band:
    the lower band in an uptrend, the upper band in a downtrend.
    """
    n = len(close)
    st_line = np.empty(n, dtype=np.float64)
    direction = np.zeros(n, dtype=np.int64)
    for i in range(n):
        st_line[i] = np.nan

    # First valid ATR index.
    first = -1
    for i in range(n):
        if not np.isnan(atr_vals[i]):
            first = i
            break
    if first < 0:
        return st_line, direction

    final_upper = 0.0
    final_lower = 0.0
    prev_dir = 1
    for i in range(first, n):
        hl2 = (high[i] + low[i]) / 2.0
        basic_upper = hl2 + mult * atr_vals[i]
        basic_lower = hl2 - mult * atr_vals[i]

        if i == first:
            final_upper = basic_upper
            final_lower = basic_lower
            direction[i] = 1
            st_line[i] = final_lower
            prev_dir = 1
            continue

        prev_upper = final_upper
        prev_lower = final_lower

        if basic_upper < prev_upper or close[i - 1] > prev_upper:
            final_upper = basic_upper
        else:
            final_upper = prev_upper

        if basic_lower > prev_lower or close[i - 1] < prev_lower:
            final_lower = basic_lower
        else:
            final_lower = prev_lower

        if close[i] > final_upper:
            cur_dir = 1
        elif close[i] < final_lower:
            cur_dir = -1
        else:
            cur_dir = prev_dir

        direction[i] = cur_dir
        st_line[i] = final_lower if cur_dir == 1 else final_upper
        prev_dir = cur_dir

    return st_line, direction


def build_atr_cache(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute ATR for all ``periods`` into a 2-D matrix ``[n_periods, n_bars]``."""
    unique = sorted(set(periods))
    matrix = np.empty((len(unique), len(close)), dtype=np.float64)
    index: dict[int, int] = {}
    for row, period in enumerate(unique):
        matrix[row] = atr(high, low, close, period)
        index[period] = row
    return matrix, index
