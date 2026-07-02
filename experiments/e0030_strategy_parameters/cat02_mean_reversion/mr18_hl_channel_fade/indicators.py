"""Technical indicators for mr18_hl_channel_fade.

Rolling range high/low (lookback excludes the current bar, to avoid
lookahead) and Wilder ATR for the range-confirmation filter and stop sizing.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
RANGE_PERIODS = [20, 30, 50, 100]

# Same numerical-stability guard used in mr09/mr14/mr15/mr20: Wilder ATR can
# decay to near machine-epsilon during extended flat-price stretches, which
# would otherwise let ``atr_range_ratio`` trivially pass (near-zero ATR /
# near-zero range) and produce an economically meaningless near-zero-risk
# stop. EURUSD ATR is never legitimately below this.
ATR_FLOOR = 1e-6


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR (identical formulation to mr01/mr03/mr13/mr15)."""
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
def rolling_range(
    high: np.ndarray, low: np.ndarray, period: int
) -> tuple[np.ndarray, np.ndarray]:
    """Rolling range high/low over the ``period`` bars BEFORE the current bar.

    ``range_high[i] = max(High[i-period:i])``, ``range_low[i] =
    min(Low[i-period:i])`` -- the lookback window excludes bar ``i`` itself,
    so the range is fully known before evaluating any signal at ``i`` (no
    lookahead). First valid index is ``period`` (needs ``period`` prior bars).
    """
    n = len(high)
    range_high = np.empty(n, dtype=np.float64)
    range_low = np.empty(n, dtype=np.float64)
    for i in range(n):
        range_high[i] = np.nan
        range_low[i] = np.nan
    if n <= period or period < 1:
        return range_high, range_low
    for i in range(period, n):
        hi = high[i - period]
        lo = low[i - period]
        for j in range(i - period + 1, i):
            if high[j] > hi:
                hi = high[j]
            if low[j] < lo:
                lo = low[j]
        range_high[i] = hi
        range_low[i] = lo
    return range_high, range_low


def build_range_cache(
    high: np.ndarray, low: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    """Precompute rolling range high/low for all unique periods.

    Returns ``(high_matrix, low_matrix, period_index)``.
    """
    unique_periods = sorted(set(periods))
    n = len(high)
    high_matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    low_matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        rh, rl = rolling_range(high, low, p)
        high_matrix[row] = rh
        low_matrix[row] = rl
        period_index[p] = row
    return high_matrix, low_matrix, period_index
