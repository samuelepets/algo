"""Technical indicators for mr14_stochrsi.

Wilder RSI, StochRSI (Stochastic formula applied to the RSI series), K/D
smoothing, and Wilder ATR for stop sizing.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
RSI_PERIODS = [10, 14]
STOCH_PERIODS = [10, 14]
SMOOTH_K_LIST = [3, 5]
SMOOTH_D = 3

# No max_hold_bars dimension in the MR-14 grid. A generous fixed forced-exit
# safety net avoids indefinitely-held positions; 100 bars applied uniformly
# across both timeframes (5-min and 15-min).
FORCED_EXIT_BARS = 100


@njit(cache=True)
def rsi(close: np.ndarray, period: int) -> np.ndarray:
    """Wilder RSI."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period + 1 or period < 1:
        return out

    gains = np.empty(n, dtype=np.float64)
    losses = np.empty(n, dtype=np.float64)
    gains[0] = 0.0
    losses[0] = 0.0
    for i in range(1, n):
        delta = close[i] - close[i - 1]
        gains[i] = delta if delta > 0.0 else 0.0
        losses[i] = -delta if delta < 0.0 else 0.0

    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(1, period + 1):
        avg_gain += gains[i]
        avg_loss += losses[i]
    avg_gain /= period
    avg_loss /= period

    def _rsi_from(ag: float, al: float) -> float:
        if al < 1e-12:
            return 100.0
        rs = ag / al
        return 100.0 - (100.0 / (1.0 + rs))

    out[period] = _rsi_from(avg_gain, avg_loss)
    k = 1.0 / period
    for i in range(period + 1, n):
        avg_gain = avg_gain + k * (gains[i] - avg_gain)
        avg_loss = avg_loss + k * (losses[i] - avg_loss)
        out[i] = _rsi_from(avg_gain, avg_loss)

    return out


@njit(cache=True)
def stoch_rsi(rsi_vals: np.ndarray, period: int) -> np.ndarray:
    """Stochastic formula applied to the RSI series, result in [0, 1]."""
    n = len(rsi_vals)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    for i in range(n):
        if np.isnan(rsi_vals[i]):
            continue
        # need `period` consecutive non-NaN RSI values ending at i
        if i - period + 1 < 0:
            continue
        lo = rsi_vals[i - period + 1]
        hi = rsi_vals[i - period + 1]
        valid = True
        for j in range(i - period + 1, i + 1):
            v = rsi_vals[j]
            if np.isnan(v):
                valid = False
                break
            if v < lo:
                lo = v
            if v > hi:
                hi = v
        if not valid:
            continue
        rng = hi - lo
        if rng < 1e-12:
            out[i] = 0.5
        else:
            out[i] = (rsi_vals[i] - lo) / rng
    return out


@njit(cache=True)
def sma(series: np.ndarray, period: int) -> np.ndarray:
    """Rolling SMA over a (possibly NaN-prefixed) series."""
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if period < 1:
        return out
    for i in range(period - 1, n):
        s = 0.0
        valid = True
        for j in range(i - period + 1, i + 1):
            v = series[j]
            if np.isnan(v):
                valid = False
                break
            s += v
        if valid:
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


def build_k_cache(
    close: np.ndarray,
    rsi_periods: list[int],
    stoch_periods: list[int],
    smooth_k_list: list[int],
) -> tuple[np.ndarray, dict[tuple[int, int, int], int]]:
    """Precompute the smoothed K line for every (rsi_period, stoch_period, smooth_k) combo.

    Returns ``(k_matrix, combo_index)`` where each matrix row corresponds to
    one combination and ``combo_index[(rsi_p, stoch_p, smooth_k)]`` gives the
    row.
    """
    n = len(close)
    combos = sorted(
        {
            (rp, sp, sk)
            for rp in rsi_periods
            for sp in stoch_periods
            for sk in smooth_k_list
        }
    )
    k_matrix = np.empty((len(combos), n), dtype=np.float64)
    combo_index: dict[tuple[int, int, int], int] = {}
    rsi_cache: dict[int, np.ndarray] = {}
    for row, (rp, sp, sk) in enumerate(combos):
        if rp not in rsi_cache:
            rsi_cache[rp] = rsi(close, rp)
        stochrsi_vals = stoch_rsi(rsi_cache[rp], sp)
        k_matrix[row] = sma(stochrsi_vals, sk)
        combo_index[(rp, sp, sk)] = row
    return k_matrix, combo_index
