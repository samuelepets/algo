"""Technical indicators for mr16_opening_range_reversion.

Wilder ATR (copied verbatim from mr01_bollinger_band, fully generic) plus
opening-range (OR) indicators: per-calendar-day ORH/ORL computed from 1-min
bars for a given session start and OR duration, then expanded onto a target
timeframe's bar array so entries can be evaluated at 1-min or 5-min
resolution while the OR window itself is always defined from 1-min data.

Session anchors are expressed in minutes-since-midnight, EET (the corpus's
native timestamp convention — see AGENTS.md). London open = 08:00 -> 480,
NY open = 13:00 -> 780.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
SECONDS_PER_DAY = 86400

SESSIONS: dict[str, int] = {"london": 480, "ny": 780}
OR_DURATIONS = [5, 10, 15, 30]


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
def compute_daily_or(
    ts: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    session_start_min: int,
    or_duration_min: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute per-calendar-day opening-range high/low from 1-min bars.

    A day is only emitted if at least one bar fell inside its OR window
    ``[session_start_min, session_start_min + or_duration_min)``. Days with
    no bars in the window (e.g. weekends, data gaps) are skipped, which the
    caller observes as a missing entry when expanding onto a bar array
    (``expand_or_to_bars`` returns NaN for those days).
    """
    n = len(ts)
    day_out = np.empty(n, dtype=np.int64)
    orh_out = np.empty(n, dtype=np.float64)
    orl_out = np.empty(n, dtype=np.float64)
    count = 0

    window_end = session_start_min + or_duration_min
    cur_day = -1
    h = -1.0e18
    lo = 1.0e18
    have_bar = False

    for i in range(n):
        day = ts[i] // SECONDS_PER_DAY
        if day != cur_day:
            if cur_day != -1 and have_bar:
                day_out[count] = cur_day
                orh_out[count] = h
                orl_out[count] = lo
                count += 1
            cur_day = day
            h = -1.0e18
            lo = 1.0e18
            have_bar = False

        minute = (ts[i] % SECONDS_PER_DAY) // 60
        if session_start_min <= minute < window_end:
            if high[i] > h:
                h = high[i]
            if low[i] < lo:
                lo = low[i]
            have_bar = True

    if cur_day != -1 and have_bar:
        day_out[count] = cur_day
        orh_out[count] = h
        orl_out[count] = lo
        count += 1

    return day_out[:count], orh_out[:count], orl_out[:count]


@njit(cache=True)
def expand_or_to_bars(
    ts: np.ndarray,
    unique_days: np.ndarray,
    orh_day: np.ndarray,
    orl_day: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Broadcast per-day OR values onto every bar of that calendar day.

    ``ts`` and ``unique_days`` are both ascending, so a single monotonic
    pointer walk (merge-style) is enough — O(n_bars + n_days) total.
    Bars whose day has no cached OR (window never traded, or day absent
    from ``unique_days``) get NaN.
    """
    n = len(ts)
    orh_bar = np.empty(n, dtype=np.float64)
    orl_bar = np.empty(n, dtype=np.float64)
    m = len(unique_days)
    j = 0
    for i in range(n):
        day = ts[i] // SECONDS_PER_DAY
        while j < m and unique_days[j] < day:
            j += 1
        if j < m and unique_days[j] == day:
            orh_bar[i] = orh_day[j]
            orl_bar[i] = orl_day[j]
        else:
            orh_bar[i] = np.nan
            orl_bar[i] = np.nan
    return orh_bar, orl_bar


def build_or_daily_cache(
    ts_1min: np.ndarray, high_1min: np.ndarray, low_1min: np.ndarray
) -> dict[tuple[str, int], tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Precompute per-day OR (days, ORH, ORL) for every (session, duration) pair."""
    cache: dict[tuple[str, int], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for session_name, start_min in SESSIONS.items():
        for dur in OR_DURATIONS:
            days, orh, orl = compute_daily_or(ts_1min, high_1min, low_1min, start_min, dur)
            cache[(session_name, dur)] = (days, orh, orl)
    return cache


def build_or_matrix(
    ts_tf: np.ndarray,
    daily_cache: dict[tuple[str, int], tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray, dict[tuple[str, int], int]]:
    """Expand the per-day OR cache onto a target-timeframe bar array.

    Returns ``(orh_matrix, orl_matrix, row_index)`` where each matrix row
    corresponds to one ``(session, duration)`` pair and
    ``row_index[(session, duration)]`` gives the row.
    """
    keys = sorted(daily_cache.keys())
    n = len(ts_tf)
    orh_matrix = np.empty((len(keys), n), dtype=np.float64)
    orl_matrix = np.empty((len(keys), n), dtype=np.float64)
    row_index: dict[tuple[str, int], int] = {}
    for row, key in enumerate(keys):
        days, orh_day, orl_day = daily_cache[key]
        orh_bar, orl_bar = expand_or_to_bars(ts_tf, days, orh_day, orl_day)
        orh_matrix[row] = orh_bar
        orl_matrix[row] = orl_bar
        row_index[key] = row
    return orh_matrix, orl_matrix, row_index
