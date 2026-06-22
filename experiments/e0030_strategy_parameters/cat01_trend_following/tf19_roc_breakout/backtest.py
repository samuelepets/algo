"""Backtest engine for tf19_roc_breakout."""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD, ROC_FILTER_NONE

SPREAD = 0.00008
MAX_TRADES = 200_000
ATR_HARD_STOP_MULT = 2.0


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
def backtest_core(open_, high, low, close, ts,
                  roc_vals, roc_filter_vals,
                  atr_vals, warm_bars,
                  threshold_pct, filter_type, holding_bars):
    """ROC breakout backtest.

    filter_type: 0 = no filter, else use roc_filter_vals > 0 (long) / < 0 (short).
    Exit: fixed holding_bars OR ATR hard stop.
    """
    n = len(close)
    if n < 2: return 0.0, 0.0, 0.0, 0.0, 0
    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0
    in_pos = False; is_long = False
    entry = 0.0; hard_stop = 0.0; risk_r = 0.0
    bars_held = 0

    warm = max(warm_bars, ATR_PERIOD) + 1

    for i in range(warm, n):
        if np.isnan(roc_vals[i]) or np.isnan(atr_vals[i]):
            continue
        if filter_type != ROC_FILTER_NONE and np.isnan(roc_filter_vals[i]):
            continue

        # Filter check
        if filter_type == ROC_FILTER_NONE:
            filter_long = True
            filter_short = True
        else:
            filter_long = roc_filter_vals[i] > 0.0
            filter_short = roc_filter_vals[i] < 0.0

        bull_sig = roc_vals[i] > threshold_pct and filter_long
        bear_sig = roc_vals[i] < -threshold_pct and filter_short

        just_exited = False
        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= hard_stop:
                    exit_r = (hard_stop - entry - SPREAD) / risk_r
                elif bars_held >= holding_bars:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= hard_stop:
                    exit_r = (entry - hard_stop - SPREAD) / risk_r
                elif bars_held >= holding_bars:
                    exit_r = (entry - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r; n_trades += 1
                in_pos = False; just_exited = True; bars_held = 0

        if not in_pos and not just_exited:
            dist = atr_vals[i] * ATR_HARD_STOP_MULT
            if bull_sig and dist > 1e-10:
                entry = close[i]; hard_stop = entry - dist
                risk_r = dist; is_long = True; in_pos = True; bars_held = 0
            elif bear_sig and dist > 1e-10:
                entry = close[i]; hard_stop = entry + dist
                risk_r = dist; is_long = False; in_pos = True; bars_held = 0

    if in_pos and risk_r > 1e-10:
        last = n - 1
        r = (close[last] - entry - SPREAD) / risk_r if is_long else (entry - close[last] - SPREAD) / risk_r
        trades[n_trades] = r; n_trades += 1

    return _compute_metrics(trades, n_trades, ts[0], ts[n-1])


@njit(parallel=True, cache=True)
def search_range(open_, high, low, close, ts,
                 roc_matrix, atr_vals,
                 roc_rows, filter_rows, warm_bars,
                 threshold_pct, filter_type, holding_bars,
                 s, e, out_sharpe, out_pf, out_mdd, out_ret, out_ntrades):
    n_grid = len(roc_rows)
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        rv = roc_matrix[roc_rows[g], s:e]
        # filter_rows[g] == -1 means no filter
        if filter_rows[g] >= 0:
            fv = roc_matrix[filter_rows[g], s:e]
        else:
            fv = rv  # unused placeholder when filter_type==NONE
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e], high[s:e], low[s:e], close[s:e], ts[s:e],
            rv, fv, atr_slice,
            int(warm_bars[g]), threshold_pct[g], int(filter_type[g]), int(holding_bars[g]),
        )
        out_sharpe[g] = sharpe; out_pf[g] = pf; out_mdd[g] = mdd
        out_ret[g] = ret; out_ntrades[g] = ntrades
