"""Backtest engine for tf18_nbar_breakout."""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD, CONFIRM_CLOSE, CONFIRM_HIGH

SPREAD = 0.00008
MAX_TRADES = 200_000


@njit(cache=True)
def _compute_metrics(trades, n_trades, ts_start, ts_end):
    if n_trades < 2:
        return 0.0, 0.0, 0.0, 0.0, n_trades
    mean_r = 0.0
    for i in range(n_trades): mean_r += trades[i]
    mean_r /= n_trades
    var_r = 0.0
    for i in range(n_trades):
        diff = trades[i] - mean_r; var_r += diff * diff
    var_r /= n_trades - 1
    std_r = var_r ** 0.5
    span_years = max((ts_end - ts_start) / (365.25 * 24.0 * 3600.0), 0.01) if ts_end > ts_start else 0.01
    trades_per_year = n_trades / span_years
    sharpe = (mean_r / std_r) * (trades_per_year ** 0.5) if std_r > 1e-12 else 0.0
    gross_win = 0.0; gross_loss = 0.0; total_return = 0.0
    for i in range(n_trades):
        r = trades[i]; total_return += r
        if r > 0.0: gross_win += r
        elif r < 0.0: gross_loss += -r
    profit_factor = (gross_win / gross_loss) if gross_loss > 1e-12 else (np.inf if gross_win > 0.0 else 0.0)
    cum_r = 0.0; peak = 0.0; max_dd = 0.0
    for i in range(n_trades):
        cum_r += trades[i]
        if cum_r > peak: peak = cum_r
        dd = peak - cum_r
        if dd > max_dd: max_dd = dd
    return sharpe, profit_factor, max_dd, total_return, n_trades


@njit(cache=True)
def backtest_core(open_, high, low, close, ts, volume,
                  breakout_high, breakout_low, vol_avg,
                  atr_vals, warm_bars, confirm, use_vol_filter,
                  atr_mult, rr):
    n = len(close)
    if n < 2: return 0.0, 0.0, 0.0, 0.0, 0
    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0
    in_pos = False; is_long = False
    entry = 0.0; stop = 0.0; target = 0.0; risk_r = 0.0

    warm = max(warm_bars, ATR_PERIOD) + 1

    for i in range(warm, n):
        if (np.isnan(breakout_high[i]) or np.isnan(breakout_low[i]) or
                np.isnan(atr_vals[i])):
            continue
        if use_vol_filter and np.isnan(vol_avg[i]):
            continue

        # Volume filter: current volume > average
        vol_ok = (not use_vol_filter) or (volume[i] > vol_avg[i])

        # Breakout signal
        if confirm == CONFIRM_CLOSE:
            bull_sig = close[i] > breakout_high[i] and vol_ok
            bear_sig = close[i] < breakout_low[i] and vol_ok
        else:  # CONFIRM_HIGH
            bull_sig = high[i] > breakout_high[i] and vol_ok
            bear_sig = low[i] < breakout_low[i] and vol_ok

        just_exited = False
        if in_pos:
            exit_r = np.nan
            if is_long:
                if low[i] <= stop: exit_r = (stop - entry - SPREAD) / risk_r
                elif high[i] >= target: exit_r = (target - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop: exit_r = (entry - stop - SPREAD) / risk_r
                elif low[i] <= target: exit_r = (entry - target - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r; n_trades += 1
                in_pos = False; just_exited = True

        if not in_pos and not just_exited:
            dist = atr_vals[i] * atr_mult
            if bull_sig and dist > 1e-10:
                entry = close[i]; stop = entry - dist; target = entry + dist * rr
                risk_r = dist; is_long = True; in_pos = True
            elif bear_sig and dist > 1e-10:
                entry = close[i]; stop = entry + dist; target = entry - dist * rr
                risk_r = dist; is_long = False; in_pos = True

    if in_pos and risk_r > 1e-10:
        last = n - 1
        r = (close[last] - entry - SPREAD) / risk_r if is_long else (entry - close[last] - SPREAD) / risk_r
        trades[n_trades] = r; n_trades += 1

    return _compute_metrics(trades, n_trades, ts[0], ts[n-1])


@njit(parallel=True, cache=True)
def search_range(open_, high, low, close, ts, volume,
                 max_matrix, min_matrix, vol_matrix, atr_vals,
                 bo_rows, warm_bars, confirm, use_vol_filter,
                 atr_mult, rr,
                 s, e, out_sharpe, out_pf, out_mdd, out_ret, out_ntrades):
    n_grid = len(bo_rows)
    atr_slice = atr_vals[s:e]
    vol_slice = volume[s:e]
    for g in prange(n_grid):
        bh = max_matrix[bo_rows[g], s:e]
        bl = min_matrix[bo_rows[g], s:e]
        va = vol_matrix[bo_rows[g], s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e], high[s:e], low[s:e], close[s:e], ts[s:e], vol_slice,
            bh, bl, va, atr_slice,
            int(warm_bars[g]), int(confirm[g]), bool(use_vol_filter[g]),
            atr_mult[g], rr[g],
        )
        out_sharpe[g] = sharpe; out_pf[g] = pf; out_mdd[g] = mdd
        out_ret[g] = ret; out_ntrades[g] = ntrades
