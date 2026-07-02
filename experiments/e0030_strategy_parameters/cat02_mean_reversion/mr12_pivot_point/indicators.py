"""Technical indicators for mr12_pivot_point.

Classic (daily/weekly) pivot points computed from the PRIOR period's
High/Low/Close and broadcast to every bar of the following period, plus
Wilder ATR for the touch/stop distances.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
DAY_SECS = 86400
WEEK_SECS = 7 * 86400

PIVOT_DAILY = 0
PIVOT_WEEKLY = 1

# Same numerical-stability guard used across the other mean-reversion
# strategies in this category (mr09/mr14/mr15/mr18/mr19/mr20).
ATR_FLOOR = 1e-5


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
def pivot_levels(
    ts: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    bucket_secs: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Classic pivot levels from the prior completed bucket, broadcast forward.

    ``bucket_secs`` is 86400 for daily buckets (calendar-day aligned, since
    the corpus timestamps are already whole-day-aligned epoch seconds) or
    7*86400 for weekly buckets (contiguous 7-day windows anchored to the
    Unix epoch -- NOT calendar ISO weeks; a documented simplification).

    Returns ``(P, R1, R2, S1, S2)`` arrays, one value per bar, using the
    High/Low/Close of the immediately preceding COMPLETED bucket. Bars in
    the first bucket (no prior bucket exists yet) get NaN.
    """
    n = len(ts)
    p = np.empty(n, dtype=np.float64)
    r1 = np.empty(n, dtype=np.float64)
    r2 = np.empty(n, dtype=np.float64)
    s1 = np.empty(n, dtype=np.float64)
    s2 = np.empty(n, dtype=np.float64)
    for i in range(n):
        p[i] = np.nan
        r1[i] = np.nan
        r2[i] = np.nan
        s1[i] = np.nan
        s2[i] = np.nan
    if n == 0:
        return p, r1, r2, s1, s2

    have_prior = False
    prior_h = 0.0
    prior_l = 0.0
    prior_c = 0.0

    cur_bucket = ts[0] // bucket_secs
    cur_h = high[0]
    cur_l = low[0]
    cur_c = close[0]

    # Bar 0 starts the first bucket -- no prior bucket exists yet, so it
    # stays NaN (already set above).

    for i in range(1, n):
        b = ts[i] // bucket_secs
        if b != cur_bucket:
            # Finalise the completed bucket as the new "prior" reference.
            prior_h = cur_h
            prior_l = cur_l
            prior_c = cur_c
            have_prior = True
            cur_bucket = b
            cur_h = high[i]
            cur_l = low[i]
            cur_c = close[i]
        else:
            if high[i] > cur_h:
                cur_h = high[i]
            if low[i] < cur_l:
                cur_l = low[i]
            cur_c = close[i]

        if have_prior:
            pivot = (prior_h + prior_l + prior_c) / 3.0
            p[i] = pivot
            r1[i] = 2.0 * pivot - prior_l
            r2[i] = pivot + (prior_h - prior_l)
            s1[i] = 2.0 * pivot - prior_h
            s2[i] = pivot - (prior_h - prior_l)

    return p, r1, r2, s1, s2


def build_pivot_cache(
    ts: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray
) -> dict[int, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Precompute pivot level arrays for both daily and weekly buckets."""
    return {
        PIVOT_DAILY: pivot_levels(ts, high, low, close, DAY_SECS),
        PIVOT_WEEKLY: pivot_levels(ts, high, low, close, WEEK_SECS),
    }
