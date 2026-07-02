"""Technical indicators for mr09_ema_distance.

EMA, Wilder ATR, Wilder ADX, and ATR-normalised price/EMA distance.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ADX_PERIOD = 14
EMA_PERIODS = [10, 20, 50, 100]
ATR_PERIODS = [10, 14]

# EURUSD ATR can decay to near-zero (down to ~1e-37) during illiquid,
# fully-flat stretches (Wilder smoothing of a run of zero true-range bars).
# Dividing by such a degenerate ATR — both for the distance signal and the
# stop distance — produces pathological, meaningless R-multiples. Floor ATR
# at roughly 0.1 pip; anything below is treated as an invalid/no-signal bar.
ATR_FLOOR = 1e-5


@njit(cache=True)
def ema(close: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average, SMA-seeded, standard alpha = 2/(period+1)."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out
    seed = 0.0
    for i in range(period):
        seed += close[i]
    seed /= period
    out[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    for i in range(period, n):
        out[i] = out[i - 1] + alpha * (close[i] - out[i - 1])
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


@njit(cache=True)
def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ADX."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < 2 or period < 1:
        return out

    tr = np.empty(n, dtype=np.float64)
    pdm = np.empty(n, dtype=np.float64)
    ndm = np.empty(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    pdm[0] = 0.0
    ndm[0] = 0.0
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        pdm[i] = up if (up > down and up > 0.0) else 0.0
        ndm[i] = down if (down > up and down > 0.0) else 0.0

    if n < period:
        return out

    satr = 0.0
    spdm = 0.0
    sndm = 0.0
    for i in range(period):
        satr += tr[i]
        spdm += pdm[i]
        sndm += ndm[i]

    k = 1.0 / period

    dx_buf = np.empty(n, dtype=np.float64)
    for i in range(n):
        dx_buf[i] = np.nan

    def _dx(satr_: float, spdm_: float, sndm_: float) -> float:
        if satr_ < 1e-12:
            return 0.0
        pdi = 100.0 * spdm_ / satr_
        ndi = 100.0 * sndm_ / satr_
        denom = pdi + ndi
        return 100.0 * abs(pdi - ndi) / denom if denom > 1e-12 else 0.0

    dx_buf[period - 1] = _dx(satr, spdm, sndm)
    for i in range(period, n):
        satr = satr - satr * k + tr[i]
        spdm = spdm - spdm * k + pdm[i]
        sndm = sndm - sndm * k + ndm[i]
        dx_buf[i] = _dx(satr, spdm, sndm)

    adx_start = 2 * period - 2
    if adx_start >= n:
        return out

    adx_seed = 0.0
    cnt = 0
    for i in range(period - 1, 2 * period - 1):
        if not np.isnan(dx_buf[i]):
            adx_seed += dx_buf[i]
            cnt += 1
    if cnt == 0:
        return out
    out[adx_start] = adx_seed / cnt
    for i in range(adx_start + 1, n):
        if not np.isnan(dx_buf[i]):
            out[i] = out[i - 1] + k * (dx_buf[i] - out[i - 1])
        else:
            out[i] = out[i - 1]

    return out


@njit(cache=True)
def distance(close: np.ndarray, ema_vals: np.ndarray, atr_vals: np.ndarray) -> np.ndarray:
    """ATR-normalised deviation of price from EMA: (Close - EMA) / ATR."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        e = ema_vals[i]
        a = atr_vals[i]
        if np.isnan(e) or np.isnan(a) or a < ATR_FLOOR:
            out[i] = np.nan
        else:
            out[i] = (close[i] - e) / a
    return out


def build_ema_cache(close: np.ndarray, periods: list[int]) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute EMA arrays for all unique periods."""
    unique_periods = sorted(set(periods))
    n = len(close)
    ema_matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        ema_matrix[row] = ema(close, p)
        period_index[p] = row
    return ema_matrix, period_index


def build_atr_cache(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute ATR arrays for all unique periods."""
    unique_periods = sorted(set(periods))
    n = len(close)
    atr_matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        atr_matrix[row] = atr(high, low, close, p)
        period_index[p] = row
    return atr_matrix, period_index
