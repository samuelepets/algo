"""Technical indicators for tf09_vwap_trend.

Pure Numba kernels: ATR and anchored VWAP with a volume-weighted standard deviation
band (reset daily or per session).
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
SECONDS_PER_DAY = 86_400
SESSION_ANCHOR_SECS = 7 * 3600  # ~07:00 in the EET-labelled timestamps (London open)


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
def vwap_bands(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    ts: np.ndarray,
    anchor_secs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Anchored VWAP and volume-weighted standard deviation of typical price.

    The anchor period is ``(ts - anchor_secs) // 86400``; the cumulative sums reset
    whenever that period changes. ``anchor_secs = 0`` is a daily (midnight) reset;
    ``anchor_secs = SESSION_ANCHOR_SECS`` shifts the boundary to the session open.
    Returns ``(vwap, std)``; ``std`` is 0 until variance is defined.
    """
    n = len(close)
    vwap = np.empty(n, dtype=np.float64)
    std = np.empty(n, dtype=np.float64)
    if n == 0:
        return vwap, std

    cum_v = 0.0
    cum_pv = 0.0
    cum_pv2 = 0.0
    cur_period = (ts[0] - anchor_secs) // SECONDS_PER_DAY
    for i in range(n):
        period = (ts[i] - anchor_secs) // SECONDS_PER_DAY
        if period != cur_period:
            cum_v = 0.0
            cum_pv = 0.0
            cum_pv2 = 0.0
            cur_period = period
        tp = (high[i] + low[i] + close[i]) / 3.0
        cum_v += volume[i]
        cum_pv += tp * volume[i]
        cum_pv2 += tp * tp * volume[i]
        if cum_v > 1e-12:
            mean = cum_pv / cum_v
            var = cum_pv2 / cum_v - mean * mean
            vwap[i] = mean
            # Clamp negligible variances (floating-point cancellation on
            # near-constant prices) to zero using a scale-invariant relative
            # threshold, so a flat session has exactly zero band width.
            rel = var / (mean * mean) if mean * mean > 1e-30 else 0.0
            std[i] = var**0.5 if rel > 1e-12 else 0.0
        else:
            vwap[i] = tp
            std[i] = 0.0
    return vwap, std


def build_vwap_cache(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    ts: np.ndarray,
    anchors: list[int],
) -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    """Precompute VWAP/std for each anchor into 2-D matrices ``[n_anchors, n_bars]``."""
    n = len(close)
    vwap_m = np.empty((len(anchors), n), dtype=np.float64)
    std_m = np.empty((len(anchors), n), dtype=np.float64)
    index: dict[int, int] = {}
    for row, anchor in enumerate(anchors):
        v, s = vwap_bands(high, low, close, volume, ts, anchor)
        vwap_m[row] = v
        std_m[row] = s
        index[anchor] = row
    return vwap_m, std_m, index
