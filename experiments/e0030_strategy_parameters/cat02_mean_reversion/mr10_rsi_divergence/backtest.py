"""Backtest engine for mr10_rsi_divergence.

Strategy: detect RSI divergence between the two most recent *confirmed*
fractal swing pivots (lows for bullish divergence, highs for bearish), enter
on the confirmation bar (optionally requiring a directional candle), stop
beyond the divergence pivot capped by an ATR multiple, target a fixed 2:1
reward:risk from entry.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
REWARD_RISK = 2.0
FORCED_EXIT_BARS = 50

CONFIRM_ANY_BAR = 0
CONFIRM_BULLISH_CANDLE = 1  # directional-candle confirmation (both directions)


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    rsi_vals: np.ndarray,
    pivot_low_vals: np.ndarray,
    pivot_high_vals: np.ndarray,
    atr_vals: np.ndarray,
    lookback: int,
    div_tolerance: float,
    confirmation: int,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run the RSI-divergence backtest on aligned slices; returns metrics tuple."""
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
    bars_held = 0

    have_prev_low = False
    have_cur_low = False
    prev_low_price = 0.0
    prev_low_rsi = 0.0
    cur_low_price = 0.0
    cur_low_rsi = 0.0

    have_prev_high = False
    have_cur_high = False
    prev_high_price = 0.0
    prev_high_rsi = 0.0
    cur_high_price = 0.0
    cur_high_rsi = 0.0

    warm = max(warm_bars, lookback + 1)

    for i in range(warm, n):
        # 1. Pivot bookkeeping — always runs, independent of position state.
        #    p = i - lookback is only knowable (no lookahead) as of bar i.
        new_signal_long = False
        new_signal_short = False
        p = i - lookback
        if p >= 0:
            plv = pivot_low_vals[p]
            if not np.isnan(plv):
                p_rsi = rsi_vals[p]
                if have_cur_low:
                    have_prev_low = True
                    prev_low_price = cur_low_price
                    prev_low_rsi = cur_low_rsi
                cur_low_price = plv
                cur_low_rsi = p_rsi
                have_cur_low = True
                if (
                    have_prev_low
                    and not np.isnan(cur_low_rsi)
                    and not np.isnan(prev_low_rsi)
                    and cur_low_price < prev_low_price
                    and cur_low_rsi > prev_low_rsi - div_tolerance
                ):
                    new_signal_long = True

            phv = pivot_high_vals[p]
            if not np.isnan(phv):
                p_rsi = rsi_vals[p]
                if have_cur_high:
                    have_prev_high = True
                    prev_high_price = cur_high_price
                    prev_high_rsi = cur_high_rsi
                cur_high_price = phv
                cur_high_rsi = p_rsi
                have_cur_high = True
                if (
                    have_prev_high
                    and not np.isnan(cur_high_rsi)
                    and not np.isnan(prev_high_rsi)
                    and cur_high_price > prev_high_price
                    and cur_high_rsi <= prev_high_rsi + div_tolerance
                ):
                    new_signal_short = True

        # 2. Manage an open position.
        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif high[i] >= target_price:
                    exit_r = (target_price - entry_price - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif low[i] <= target_price:
                    exit_r = (entry_price - target_price - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        # 3. Entry logic — only when flat.
        a = atr_vals[i]
        if np.isnan(a):
            continue

        if new_signal_long and confirmation == CONFIRM_BULLISH_CANDLE:
            if not (close[i] > open_[i]):
                new_signal_long = False
        if new_signal_short and confirmation == CONFIRM_BULLISH_CANDLE:
            if not (close[i] < open_[i]):
                new_signal_short = False

        if new_signal_long and new_signal_short:
            continue  # ambiguous same-bar signal — skip

        if new_signal_long:
            entry_price = close[i]
            pivot_dist = entry_price - cur_low_price
            atr_cap = atr_stop_mult * a
            dist = pivot_dist if pivot_dist < atr_cap else atr_cap
            if dist > 1e-8:
                stop = entry_price - dist
                risk_r = dist
                target_price = entry_price + REWARD_RISK * dist
                is_long = True
                in_pos = True
                bars_held = 0
        elif new_signal_short:
            entry_price = close[i]
            pivot_dist = cur_high_price - entry_price
            atr_cap = atr_stop_mult * a
            dist = pivot_dist if pivot_dist < atr_cap else atr_cap
            if dist > 1e-8:
                stop = entry_price + dist
                risk_r = dist
                target_price = entry_price - REWARD_RISK * dist
                is_long = False
                in_pos = True
                bars_held = 0

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
    rsi_matrix: np.ndarray,
    pivot_low_matrix: np.ndarray,
    pivot_high_matrix: np.ndarray,
    atr_vals: np.ndarray,
    rsi_rows: np.ndarray,
    lookback_rows: np.ndarray,
    lookback: np.ndarray,
    div_tolerance: np.ndarray,
    confirmation: np.ndarray,
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
    n_grid = len(rsi_rows)
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        r_row = rsi_rows[g]
        lb_row = lookback_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            rsi_matrix[r_row, s:e],
            pivot_low_matrix[lb_row, s:e],
            pivot_high_matrix[lb_row, s:e],
            atr_slice,
            int(lookback[g]),
            div_tolerance[g],
            int(confirmation[g]),
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
