"""Technical indicators for mr17_ema_touch_return.

EMA (mean reference line), Wilder ATR(14) (distance unit + stop), Wilder
ADX(14) (non-trending regime filter). ATR and ADX periods are fixed at 14 per
the strategy spec (not grid-searched).
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
ADX_PERIOD = 14
EMA_PERIODS = [10, 20, 50]


@njit(cache=True)
def ema(series: np.ndarray, period: int) -> np.ndarray:
    """EMA seeded with an SMA of the first ``period`` values."""
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if period < 1 or n < period:
        return out
    seed = 0.0
    for i in range(period):
        seed += series[i]
    seed /= period
    out[period - 1] = seed
    mult = 2.0 / (period + 1)
    for i in range(period, n):
        out[i] = (series[i] - out[i - 1]) * mult + out[i - 1]
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


def build_ema_cache(close: np.ndarray, periods: list[int]) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute EMA arrays for all unique periods."""
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = ema(close, p)
        period_index[p] = row
    return matrix, period_index
