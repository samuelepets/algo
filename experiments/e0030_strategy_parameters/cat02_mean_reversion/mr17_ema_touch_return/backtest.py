"""Backtest engine for mr17_ema_touch_return.

Strategy: during a non-trending regime (ADX < adx_max), when the prior bar's
close is more than ``distance_thresh_atr`` ATR units away from the EMA and the
current bar's close moves back toward the EMA (a simple one-bar reversal
confirmation), enter in that direction expecting a return to the EMA.
Exit target: either the (dynamically updated) EMA itself, or a static level
set at entry — half the ATR-distance observed at entry, toward the EMA.
A fixed forced-exit safety net (``MAX_HOLD_BARS``) protects against
indefinitely stuck positions since ``max_hold_bars`` is not part of the grid.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
MAX_HOLD_BARS = 100  # fixed forced-exit safety net (not grid-searched)

EXIT_EMA_TOUCH = 0
EXIT_HALF_DISTANCE = 1


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    ema_vals: np.ndarray,
    atr_vals: np.ndarray,
    adx_vals: np.ndarray,
    distance_thresh_atr: float,
    adx_max: float,
    atr_stop_mult: float,
    exit_type: int,
    max_hold_bars: int,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run EMA Touch Return mean-reversion backtest; returns metrics tuple."""
    n = len(close)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry_price = 0.0
    stop = 0.0
    target_static = 0.0
    risk_r = 0.0
    bars_held = 0

    warm = warm_bars + 1

    for i in range(warm, n):
        e = ema_vals[i]
        a = atr_vals[i]
        if np.isnan(e) or np.isnan(a):
            continue

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            target = e if exit_type == EXIT_EMA_TOUCH else target_static
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif close[i] >= target:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif close[i] <= target:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        adx_val = adx_vals[i]
        if np.isnan(adx_val) or adx_val >= adx_max:
            continue

        e_prev = ema_vals[i - 1]
        a_prev = atr_vals[i - 1]
        if np.isnan(e_prev) or np.isnan(a_prev) or a_prev < 1e-12:
            continue

        prev_close = close[i - 1]
        below_dist = e_prev - prev_close  # positive if close was below EMA
        above_dist = prev_close - e_prev  # positive if close was above EMA

        bull_sig = below_dist > distance_thresh_atr * a_prev and close[i] > prev_close
        bear_sig = above_dist > distance_thresh_atr * a_prev and close[i] < prev_close

        dist = a * atr_stop_mult
        if bull_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price - dist
            risk_r = dist
            is_long = True
            in_pos = True
            bars_held = 0
            half_dist_price = abs(e - entry_price) * 0.5
            target_static = entry_price + half_dist_price
        elif bear_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price + dist
            risk_r = dist
            is_long = False
            in_pos = True
            bars_held = 0
            half_dist_price = abs(e - entry_price) * 0.5
            target_static = entry_price - half_dist_price

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
    ema_matrix: np.ndarray,
    atr_vals: np.ndarray,
    adx_vals: np.ndarray,
    ema_rows: np.ndarray,
    distance_thresh_atr: np.ndarray,
    adx_max: np.ndarray,
    atr_stop_mult: np.ndarray,
    exit_type: np.ndarray,
    max_hold_bars: np.ndarray,
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
    n_grid = len(ema_rows)
    atr_slice = atr_vals[s:e]
    adx_slice = adx_vals[s:e]
    for g in prange(n_grid):
        row = ema_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            ema_matrix[row, s:e],
            atr_slice,
            adx_slice,
            distance_thresh_atr[g],
            adx_max[g],
            atr_stop_mult[g],
            int(exit_type[g]),
            int(max_hold_bars[g]),
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
