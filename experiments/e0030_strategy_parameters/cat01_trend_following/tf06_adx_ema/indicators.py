"""Technical indicators for tf06_adx_ema.

Pure Numba kernels: EMA, ATR, and the Wilder ADX / +DI / -DI directional system.
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
def adx_dmi(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Wilder ADX, +DI, -DI.

    +DI/-DI are valid from index ``period``; ADX from index ``2*period - 1``.
    """
    n = len(close)
    adx = np.empty(n, dtype=np.float64)
    plus_di = np.empty(n, dtype=np.float64)
    minus_di = np.empty(n, dtype=np.float64)
    for i in range(n):
        adx[i] = np.nan
        plus_di[i] = np.nan
        minus_di[i] = np.nan

    if n < 2 * period + 1 or period == 0:
        return adx, plus_di, minus_di

    tr = np.empty(n, dtype=np.float64)
    plus_dm = np.empty(n, dtype=np.float64)
    minus_dm = np.empty(n, dtype=np.float64)
    tr[0] = 0.0
    plus_dm[0] = 0.0
    minus_dm[0] = 0.0
    for i in range(1, n):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0.0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0.0) else 0.0
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)

    # Wilder smoothed sums seeded at index `period` (sum of indices 1..period).
    sm_tr = 0.0
    sm_plus = 0.0
    sm_minus = 0.0
    for i in range(1, period + 1):
        sm_tr += tr[i]
        sm_plus += plus_dm[i]
        sm_minus += minus_dm[i]

    dx = np.empty(n, dtype=np.float64)
    for i in range(n):
        dx[i] = np.nan

    for i in range(period, n):
        if i > period:
            sm_tr = sm_tr - sm_tr / period + tr[i]
            sm_plus = sm_plus - sm_plus / period + plus_dm[i]
            sm_minus = sm_minus - sm_minus / period + minus_dm[i]
        pdi = 100.0 * sm_plus / sm_tr if sm_tr > 1e-12 else 0.0
        mdi = 100.0 * sm_minus / sm_tr if sm_tr > 1e-12 else 0.0
        plus_di[i] = pdi
        minus_di[i] = mdi
        denom = pdi + mdi
        dx[i] = 100.0 * abs(pdi - mdi) / denom if denom > 1e-12 else 0.0

    # ADX: seed at index 2*period-1 with the mean of DX[period .. 2*period-1].
    seed_idx = 2 * period - 1
    seed = 0.0
    for i in range(period, seed_idx + 1):
        seed += dx[i]
    seed /= period
    adx[seed_idx] = seed
    for i in range(seed_idx + 1, n):
        adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return adx, plus_di, minus_di


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


def build_adx_cache(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[int, int]]:
    """Precompute ADX/+DI/-DI for all ``periods`` into 2-D matrices."""
    unique = sorted(set(periods))
    n = len(close)
    adx_m = np.empty((len(unique), n), dtype=np.float64)
    plus_m = np.empty((len(unique), n), dtype=np.float64)
    minus_m = np.empty((len(unique), n), dtype=np.float64)
    index: dict[int, int] = {}
    for row, period in enumerate(unique):
        a, p, m = adx_dmi(high, low, close, period)
        adx_m[row] = a
        plus_m[row] = p
        minus_m[row] = m
        index[period] = row
    return adx_m, plus_m, minus_m, index
