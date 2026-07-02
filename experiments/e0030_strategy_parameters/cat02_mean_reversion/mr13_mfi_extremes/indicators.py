"""Technical indicators for mr13_mfi_extremes.

Money Flow Index (volume-weighted RSI) and Wilder ATR.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
MFI_PERIODS = [7, 10, 14, 20]


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR (identical formulation to mr01/mr03)."""
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
def _mfi_value(sum_pos: float, sum_neg: float) -> float:
    if sum_neg < 1e-12:
        if sum_pos < 1e-12:
            return 50.0
        return 100.0
    ratio = sum_pos / sum_neg
    return 100.0 - 100.0 / (1.0 + ratio)


@njit(cache=True)
def mfi(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, period: int
) -> np.ndarray:
    """Money Flow Index over ``period`` bars.

    Typical Price ``TP = (H+L+C)/3``; Money Flow ``MF = TP * Volume``. Each
    bar after the first is classified "positive" money flow if
    ``TP[i] > TP[i-1]``, "negative" if ``TP[i] < TP[i-1]``, and contributes
    to neither if unchanged. ``MFI = 100 - 100/(1 + sum_pos/sum_neg)`` over a
    rolling ``period``-bar window. The first bar has no prior TP to compare
    against, so it contributes zero to both sums (standard RSI-style
    warm-up convention) -- the first valid MFI value is at index
    ``period - 1``.
    """
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out

    pos = np.empty(n, dtype=np.float64)
    neg = np.empty(n, dtype=np.float64)
    pos[0] = 0.0
    neg[0] = 0.0
    tp_prev = (high[0] + low[0] + close[0]) / 3.0
    for i in range(1, n):
        tp = (high[i] + low[i] + close[i]) / 3.0
        mf = tp * volume[i]
        if tp > tp_prev:
            pos[i] = mf
            neg[i] = 0.0
        elif tp < tp_prev:
            pos[i] = 0.0
            neg[i] = mf
        else:
            pos[i] = 0.0
            neg[i] = 0.0
        tp_prev = tp

    sum_pos = 0.0
    sum_neg = 0.0
    for i in range(period):
        sum_pos += pos[i]
        sum_neg += neg[i]
    out[period - 1] = _mfi_value(sum_pos, sum_neg)

    for i in range(period, n):
        sum_pos += pos[i] - pos[i - period]
        sum_neg += neg[i] - neg[i - period]
        out[i] = _mfi_value(sum_pos, sum_neg)

    return out


def build_mfi_cache(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute MFI arrays for all unique periods.

    Returns ``(mfi_matrix, period_index)`` where each row corresponds to one
    period and ``period_index[p]`` gives the row.
    """
    unique_periods = sorted(set(periods))
    n = len(close)
    mfi_matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        mfi_matrix[row] = mfi(high, low, close, volume, p)
        period_index[p] = row
    return mfi_matrix, period_index
