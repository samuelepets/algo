"""Technical indicators for tf16_linreg_channel.

ATR (Wilder) and rolling linear regression channel (LinReg center + sigma bands).
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14

ENTRY_BOUNCE = 0
ENTRY_BREAKOUT = 1


@njit(cache=True)
def atr(high, low, close, period):
    """Wilder ATR."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n): out[i] = np.nan
    if n < 2 or period == 0: return out
    tr = np.empty(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)
    if n < period: return out
    seed = 0.0
    for i in range(period): seed += tr[i]
    seed /= period
    out[period-1] = seed
    k = 1.0 / period
    for i in range(period, n):
        out[i] = out[i-1] + k * (tr[i] - out[i-1])
    return out


@njit(cache=True)
def linreg_channel(close, period):
    """Rolling OLS LinReg center, upper band, lower band (k=1 sigma).

    Returns (center, sigma) arrays; caller scales sigma by channel_width_k.
    """
    n = len(close)
    center = np.empty(n, dtype=np.float64)
    sigma = np.empty(n, dtype=np.float64)
    for i in range(n):
        center[i] = np.nan
        sigma[i] = np.nan
    if n < period:
        return center, sigma

    # Precompute x values (0..period-1) and their mean/variance
    x_mean = (period - 1.0) / 2.0
    sx2 = 0.0
    for j in range(period):
        sx2 += (j - x_mean) ** 2

    for i in range(period - 1, n):
        # OLS: y = slope*x + intercept, x in [0..period-1]
        sy = 0.0
        sxy = 0.0
        for j in range(period):
            y = close[i - period + 1 + j]
            sy += y
            sxy += j * y
        y_mean = sy / period
        sxy_centered = sxy - period * x_mean * y_mean
        slope = sxy_centered / sx2 if sx2 > 1e-14 else 0.0
        intercept = y_mean - slope * x_mean

        # LinReg value at last bar (x = period-1)
        lr = slope * (period - 1) + intercept
        center[i] = lr

        # Residual std dev
        ss = 0.0
        for j in range(period):
            predicted = slope * j + intercept
            r = close[i - period + 1 + j] - predicted
            ss += r * r
        sigma[i] = (ss / period) ** 0.5

    return center, sigma


def build_linreg_cache(close, periods):
    """Precompute linreg_channel for all periods; return (center_matrix, sigma_matrix, index)."""
    unique = sorted(set(periods))
    n = len(close)
    center_matrix = np.empty((len(unique), n), dtype=np.float64)
    sigma_matrix = np.empty((len(unique), n), dtype=np.float64)
    index = {}
    for row, p in enumerate(unique):
        c, s = linreg_channel(close, p)
        center_matrix[row] = c
        sigma_matrix[row] = s
        index[p] = row
    return center_matrix, sigma_matrix, index
