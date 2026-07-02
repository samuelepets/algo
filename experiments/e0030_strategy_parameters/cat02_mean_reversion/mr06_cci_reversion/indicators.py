"""Technical indicators for mr06_cci_reversion.

SMA, Wilder ATR, Wilder ADX (copied verbatim from mr01_bollinger_band — same
generic implementations), plus typical price and CCI (new for this strategy).
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
ADX_PERIOD = 14
CCI_PERIODS = [10, 14, 20, 30]


@njit(cache=True)
def sma(close: np.ndarray, period: int) -> np.ndarray:
    """Rolling SMA using a sliding-window accumulator."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out
    s = 0.0
    for i in range(period):
        s += close[i]
    out[period - 1] = s / period
    for i in range(period, n):
        s += close[i] - close[i - period]
        out[i] = s / period
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

    # Seed Wilder smoothed TR, +DM, -DM from first `period` bars
    satr = 0.0
    spdm = 0.0
    sndm = 0.0
    for i in range(period):
        satr += tr[i]
        spdm += pdm[i]
        sndm += ndm[i]

    k = 1.0 / period

    # DX buffer — first valid at index period-1
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

    # ADX = Wilder smooth of DX; seed = mean of `period` DX values starting at period-1
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
def typical_price(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Bar-by-bar typical price ``(H + L + C) / 3``."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = (high[i] + low[i] + close[i]) / 3.0
    return out


@njit(cache=True)
def cci(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Commodity Channel Index.

    ``cci[i] = (tp[i] - tp_sma[i]) / (0.015 * mad[i])`` where ``tp`` is the
    typical price, ``tp_sma`` its rolling SMA, and ``mad[i]`` the mean absolute
    deviation of ``tp`` from ``tp_sma[i]`` over the same trailing window
    (standard CCI convention: every point in the window is compared against
    that window's own SMA value, not a per-point rolling reference).
    NaN during warm-up or when ``mad[i]`` is ~0 (flat typical price).
    """
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out

    tp = typical_price(high, low, close)
    tp_sma = sma(tp, period)

    for i in range(period - 1, n):
        ref = tp_sma[i]
        if np.isnan(ref):
            continue
        mad = 0.0
        for j in range(i - period + 1, i + 1):
            mad += abs(tp[j] - ref)
        mad /= period
        if mad < 1e-12:
            continue
        out[i] = (tp[i] - ref) / (0.015 * mad)
    return out


def build_cci_cache(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute CCI arrays for all unique periods.

    Returns ``(cci_matrix, period_index)`` where each matrix row corresponds
    to one period and ``period_index[p]`` gives the row.
    """
    unique_periods = sorted(set(periods))
    n = len(close)
    cci_matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        cci_matrix[row] = cci(high, low, close, p)
        period_index[p] = row
    return cci_matrix, period_index
