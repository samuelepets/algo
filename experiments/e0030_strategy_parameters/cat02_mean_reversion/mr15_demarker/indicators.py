"""Technical indicators for mr15_demarker.

DeMarker oscillator and Wilder ATR for stop sizing.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
DEMARKER_PERIODS = [5, 10, 14, 20]

# Wilder ATR can decay to near machine-epsilon during extended flat-price
# stretches (weekend/holiday gaps in the resampled bars). DeMarker is built
# from High/Low deltas and is not scale-invariant in the same way RSI-based
# oscillators are, but the ATR-based stop still needs a realistic floor to
# avoid an economically meaningless near-zero-risk trade (see mr09/mr14/mr20
# for the same fix). EURUSD ATR is never legitimately below this.
ATR_FLOOR = 1e-6


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR (identical formulation to mr01/mr03/mr13)."""
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
def demarker(high: np.ndarray, low: np.ndarray, period: int) -> np.ndarray:
    """DeMarker oscillator over ``period`` bars, result in [0, 1].

    ``DeMax[i] = max(High[i] - High[i-1], 0)``, ``DeMin[i] = max(Low[i-1] -
    Low[i], 0)``. ``DeMarker = mean(DeMax, period) / (mean(DeMax, period) +
    mean(DeMin, period))``. The first bar has no prior High/Low to compare
    against, so it contributes zero to both sums (same warm-up convention as
    RSI/MFI elsewhere in this repo) -- the first valid value is at index
    ``period``.
    """
    n = len(high)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period + 1 or period < 1:
        return out

    demax = np.empty(n, dtype=np.float64)
    demin = np.empty(n, dtype=np.float64)
    demax[0] = 0.0
    demin[0] = 0.0
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        demax[i] = up if up > 0.0 else 0.0
        demin[i] = down if down > 0.0 else 0.0

    sum_max = 0.0
    sum_min = 0.0
    for i in range(1, period + 1):
        sum_max += demax[i]
        sum_min += demin[i]

    def _value(sm: float, sn: float) -> float:
        denom = sm + sn
        if denom < 1e-12:
            return 0.5
        return sm / denom

    out[period] = _value(sum_max, sum_min)
    for i in range(period + 1, n):
        sum_max += demax[i] - demax[i - period]
        sum_min += demin[i] - demin[i - period]
        out[i] = _value(sum_max, sum_min)

    return out


def build_demarker_cache(
    high: np.ndarray, low: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    """Precompute DeMarker arrays for all unique periods.

    Returns ``(dem_matrix, period_index)`` where each row corresponds to one
    period and ``period_index[p]`` gives the row.
    """
    unique_periods = sorted(set(periods))
    n = len(high)
    dem_matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        dem_matrix[row] = demarker(high, low, p)
        period_index[p] = row
    return dem_matrix, period_index
