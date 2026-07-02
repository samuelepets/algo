"""Backtest engine for mr16_opening_range_reversion.

Strategy: fade *failed* opening-range breakouts. Once the OR window
(session-anchored, N minutes) closes for the day, watch for a bar that
closes beyond ORH/ORL (a breakout attempt). If price closes back inside the
range within ``reversal_bars`` bars, enter a fade trade in the direction of
the opposite side of the range; otherwise the setup is invalidated for the
day. Only the first qualifying breakout per session per day is evaluated —
see README "Implementation Semantics" for the exact state machine.

Stop: outside (breakout) bar's extreme +/- ``atr_stop_mult`` x ATR(14).
Target: either the opposite side of the range, or the range midpoint.
Forced exit: end of the calendar day (last bar of the day), to stay
faithful to the day-scoped nature of an opening-range strategy.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
SECONDS_PER_DAY = 86400

TARGET_MID = 0        # range midpoint (ORH+ORL)/2
TARGET_OPPOSITE = 1   # opposite side of the range

PENDING_NONE = 0
PENDING_SHORT = 1   # breakout above ORH; watching for a fade-short reversal
PENDING_LONG = 2    # breakout below ORL; watching for a fade-long reversal


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    atr_vals: np.ndarray,
    orh_bar: np.ndarray,
    orl_bar: np.ndarray,
    or_window_end_min: int,
    reversal_bars: int,
    target_mode: int,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run the OR-fade backtest on aligned slices; returns metrics tuple."""
    n = len(close)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry_price = 0.0
    stop = 0.0
    target_price = 0.0
    risk_r = 0.0

    cur_day = -1
    day_signal_used = False
    pending = PENDING_NONE
    pending_remaining = 0
    breakout_extreme = 0.0

    for i in range(warm_bars, n):
        day = ts[i] // SECONDS_PER_DAY
        if day != cur_day:
            cur_day = day
            day_signal_used = False
            pending = PENDING_NONE

        is_last_of_day = (i == n - 1) or ((ts[i + 1] // SECONDS_PER_DAY) != day)

        if in_pos:
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif high[i] >= target_price:
                    exit_r = (target_price - entry_price - SPREAD) / risk_r
                elif is_last_of_day:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif low[i] <= target_price:
                    exit_r = (entry_price - target_price - SPREAD) / risk_r
                elif is_last_of_day:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        a = atr_vals[i]
        orh = orh_bar[i]
        orl = orl_bar[i]
        if np.isnan(a) or np.isnan(orh) or np.isnan(orl):
            continue

        minute = (ts[i] % SECONDS_PER_DAY) // 60
        if minute < or_window_end_min:
            continue
        if day_signal_used:
            continue

        if pending != PENDING_NONE:
            inside = (close[i] >= orl) and (close[i] <= orh)
            if inside:
                dist = atr_stop_mult * a
                if pending == PENDING_SHORT:
                    cand_entry = close[i]
                    cand_stop = breakout_extreme + dist
                    cand_target = orl if target_mode == TARGET_OPPOSITE else (orh + orl) * 0.5
                    cand_risk = cand_stop - cand_entry
                    if cand_risk > 1e-10:
                        entry_price = cand_entry
                        stop = cand_stop
                        target_price = cand_target
                        risk_r = cand_risk
                        is_long = False
                        in_pos = True
                else:  # PENDING_LONG
                    cand_entry = close[i]
                    cand_stop = breakout_extreme - dist
                    cand_target = orh if target_mode == TARGET_OPPOSITE else (orh + orl) * 0.5
                    cand_risk = cand_entry - cand_stop
                    if cand_risk > 1e-10:
                        entry_price = cand_entry
                        stop = cand_stop
                        target_price = cand_target
                        risk_r = cand_risk
                        is_long = True
                        in_pos = True
                pending = PENDING_NONE
                day_signal_used = True
            else:
                pending_remaining -= 1
                if pending_remaining <= 0:
                    pending = PENDING_NONE
                    day_signal_used = True
            continue

        if close[i] > orh:
            pending = PENDING_SHORT
            breakout_extreme = high[i]
            pending_remaining = reversal_bars
        elif close[i] < orl:
            pending = PENDING_LONG
            breakout_extreme = low[i]
            pending_remaining = reversal_bars

    if in_pos and risk_r > 1e-10:
        last = n - 1
        if is_long:
            r = (close[last] - entry_price - SPREAD) / risk_r
        else:
            r = (entry_price - close[last] - SPREAD) / risk_r
        trades[n_trades] = r
        n_trades += 1

    return compute_metrics(trades, n_trades, ts[0], ts[n - 1])


@njit(parallel=True, cache=True)
def search_range(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    atr_vals: np.ndarray,
    orh_matrix: np.ndarray,
    orl_matrix: np.ndarray,
    row_idx: np.ndarray,
    or_window_end_min: np.ndarray,
    reversal_bars: np.ndarray,
    target_mode: np.ndarray,
    atr_stop_mult: np.ndarray,
    warm_bars: np.ndarray,
    s: int,
    e: int,
    out_sharpe: np.ndarray,
    out_pf: np.ndarray,
    out_mdd: np.ndarray,
    out_ret: np.ndarray,
    out_ntrades: np.ndarray,
) -> None:
    """Parallel grid search over ``[s, e)`` using precomputed indicators."""
    n_grid = len(row_idx)
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        row = row_idx[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            atr_slice,
            orh_matrix[row, s:e],
            orl_matrix[row, s:e],
            int(or_window_end_min[g]),
            int(reversal_bars[g]),
            int(target_mode[g]),
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
