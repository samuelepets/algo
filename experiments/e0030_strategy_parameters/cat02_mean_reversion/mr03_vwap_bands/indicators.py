"""Technical indicators for mr03_vwap_bands.

Session-anchored VWAP with running (cumulative, within-session) population
standard-deviation bands, plus Wilder ATR.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14

# Session-reset modes and their anchor offsets (seconds after 00:00 EET).
# The market-data timestamps are parsed "as if UTC" from naive EET labels
# (see algo_shared.data), so 00:00 EET local wall-clock lines up with epoch
# seconds divisible by 86400 -- no timezone conversion is needed here.
VWAP_RESET_MODES = ["daily", "session_london", "session_ny"]
RESET_ANCHOR_SECS = {
    "daily": 0,
    "session_london": 8 * 3600,
    "session_ny": 13 * 3600,
}
BUCKET_SECS = 86400


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR (identical formulation to mr01)."""
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
    ts: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    anchor_offset_secs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Session-anchored VWAP and running population std of (TP - VWAP).

    Session buckets reset every 86400s starting at ``anchor_offset_secs``
    past local midnight. Within a bucket, VWAP is the cumulative
    volume-weighted typical price and the band is the cumulative
    (running, population, ddof=0) standard deviation of the per-bar
    deviation ``typical_price[j] - vwap[j]`` for all bars ``j`` seen so far
    in that same session -- both reset at each bucket boundary.
    """
    n = len(close)
    vwap = np.empty(n, dtype=np.float64)
    band_std = np.empty(n, dtype=np.float64)
    if n == 0:
        return vwap, band_std

    cur_bucket = -(2**62)
    cum_vol = 0.0
    cum_tpvol = 0.0
    cum_dev = 0.0
    cum_dev2 = 0.0
    cnt = 0

    for i in range(n):
        b = (ts[i] - anchor_offset_secs) // BUCKET_SECS
        if b != cur_bucket:
            cur_bucket = b
            cum_vol = 0.0
            cum_tpvol = 0.0
            cum_dev = 0.0
            cum_dev2 = 0.0
            cnt = 0

        tp = (high[i] + low[i] + close[i]) / 3.0
        vol = volume[i]
        cum_vol += vol
        cum_tpvol += tp * vol

        if cum_vol > 1e-12:
            v = cum_tpvol / cum_vol
        else:
            v = tp
        vwap[i] = v

        dev = tp - v
        cum_dev += dev
        cum_dev2 += dev * dev
        cnt += 1

        mean_dev = cum_dev / cnt
        var = cum_dev2 / cnt - mean_dev * mean_dev
        if var < 0.0:
            var = 0.0
        band_std[i] = var**0.5

    return vwap, band_std


def build_vwap_cache(
    ts: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    modes: list[str],
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Precompute VWAP + running-std band arrays for all reset modes.

    Returns ``(vwap_matrix, std_matrix, mode_index)`` where each row
    corresponds to one reset mode and ``mode_index[mode]`` gives the row.
    """
    unique_modes = list(dict.fromkeys(modes))
    n = len(close)
    vwap_matrix = np.empty((len(unique_modes), n), dtype=np.float64)
    std_matrix = np.empty((len(unique_modes), n), dtype=np.float64)
    mode_index: dict[str, int] = {}
    for row, mode in enumerate(unique_modes):
        offset = RESET_ANCHOR_SECS[mode]
        v, s = vwap_bands(ts, high, low, close, volume, offset)
        vwap_matrix[row] = v
        std_matrix[row] = s
        mode_index[mode] = row
    return vwap_matrix, std_matrix, mode_index
