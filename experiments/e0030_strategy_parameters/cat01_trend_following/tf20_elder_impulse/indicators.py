"""Technical indicators for tf20_elder_impulse.

EMA, MACD histogram, ATR, and Elder Impulse bar color coding.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14

# Bar color codes
COLOR_NEUTRAL = 0
COLOR_GREEN = 1
COLOR_RED = 2

# Entry/exit condition constants
ENTRY_FIRST = 0  # first colored bar after neutral
ENTRY_ANY = 1  # any colored bar

EXIT_NEUTRAL = 0  # exit on neutral bar
EXIT_OPPOSITE = 1  # exit on opposite color


@njit(cache=True)
def atr(high, low, close, period):
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
def ema(series, period):
    """Exponential moving average."""
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if period == 0 or n < period:
        return out
    seed = 0.0
    for i in range(period):
        seed += series[i]
    out[period - 1] = seed / period
    k = 2.0 / (period + 1.0)
    for i in range(period, n):
        out[i] = series[i] * k + out[i - 1] * (1.0 - k)
    return out


@njit(cache=True)
def macd_histogram(close, fast, slow, signal):
    """MACD histogram = MACD_line - signal_line."""
    n = len(close)
    hist = np.empty(n, dtype=np.float64)
    for i in range(n):
        hist[i] = np.nan
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = np.empty(n, dtype=np.float64)
    for i in range(n):
        if np.isnan(ema_fast[i]) or np.isnan(ema_slow[i]):
            macd_line[i] = np.nan
        else:
            macd_line[i] = ema_fast[i] - ema_slow[i]
    sig = ema(macd_line, signal)
    for i in range(n):
        if np.isnan(macd_line[i]) or np.isnan(sig[i]):
            hist[i] = np.nan
        else:
            hist[i] = macd_line[i] - sig[i]
    return hist


@njit(cache=True)
def elder_impulse_colors(ema_vals, hist_vals):
    """Compute Elder Impulse bar colors from EMA and MACD histogram arrays."""
    n = len(ema_vals)
    colors = np.empty(n, dtype=np.int64)
    for i in range(n):
        colors[i] = COLOR_NEUTRAL
    for i in range(1, n):
        if np.isnan(ema_vals[i]) or np.isnan(ema_vals[i - 1]):
            colors[i] = COLOR_NEUTRAL
            continue
        if np.isnan(hist_vals[i]) or np.isnan(hist_vals[i - 1]):
            colors[i] = COLOR_NEUTRAL
            continue
        ema_rising = ema_vals[i] > ema_vals[i - 1]
        hist_rising = hist_vals[i] > hist_vals[i - 1]
        if ema_rising and hist_rising:
            colors[i] = COLOR_GREEN
        elif not ema_rising and not hist_rising:
            colors[i] = COLOR_RED
        else:
            colors[i] = COLOR_NEUTRAL
    return colors


def build_impulse_cache(
    close,
    high,
    low,
    ema_periods,
    macd_fast_periods,
    macd_slow_periods,
    macd_signal_periods,
):
    """Precompute Elder Impulse color arrays for all unique parameter combinations.

    Key: (ema_period, macd_fast, macd_slow, macd_signal)
    Returns (colors_dict, atr_vals).
    """
    atr_vals = atr(high, low, close, ATR_PERIOD)
    colors_dict = {}
    seen = set()
    for ep in ema_periods:
        for mf in macd_fast_periods:
            for ms in macd_slow_periods:
                for sig in macd_signal_periods:
                    if mf >= ms:
                        continue
                    key = (ep, mf, ms, sig)
                    if key in seen:
                        continue
                    seen.add(key)
                    e_vals = ema(close, ep)
                    h_vals = macd_histogram(close, mf, ms, sig)
                    colors_dict[key] = elder_impulse_colors(e_vals, h_vals)
    return colors_dict, atr_vals
