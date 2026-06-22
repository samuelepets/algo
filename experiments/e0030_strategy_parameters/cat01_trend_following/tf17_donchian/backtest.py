"""Backtest engine for tf17_donchian."""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD

SPREAD = 0.00008
MAX_TRADES = 200_000
ATR_HARD_STOP_MULT = 2.0  # hard stop in case channel exit doesn't trigger


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
                  entry_upper, entry_lower, exit_upper, exit_lower,
                  atr_vals, warm_bars, buffer_atr, rr):
    """Donchian channel backtest.

    rr is unused (exit is channel-based), kept for interface consistency with hard stop sizing.
    The 'risk_r' is defined as ATR_HARD_STOP_MULT * ATR at entry.
    """
    n = len(close)
    if n < 2: return 0.0, 0.0, 0.0, 0.0, 0
    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0
    in_pos = False; is_long = False
    entry = 0.0; hard_stop = 0.0; risk_r = 0.0

    warm = max(warm_bars, ATR_PERIOD) + 1

    for i in range(warm, n):
        if (np.isnan(entry_upper[i]) or np.isnan(entry_lower[i]) or
                np.isnan(exit_upper[i]) or np.isnan(exit_lower[i]) or
                np.isnan(atr_vals[i])):
            continue

        a = atr_vals[i]
        buf = buffer_atr * a
        long_entry_lvl = entry_upper[i] + buf
        short_entry_lvl = entry_lower[i] - buf
        bull_sig = close[i] > long_entry_lvl
        bear_sig = close[i] < short_entry_lvl

        just_exited = False
        if in_pos:
            exit_r = np.nan
            if is_long:
                # Channel exit or hard stop
                if low[i] <= hard_stop:
                    exit_r = (hard_stop - entry - SPREAD) / risk_r
                elif close[i] < exit_lower[i]:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= hard_stop:
                    exit_r = (entry - hard_stop - SPREAD) / risk_r
                elif close[i] > exit_upper[i]:
                    exit_r = (entry - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r; n_trades += 1
                in_pos = False; just_exited = True

        if not in_pos and not just_exited:
            a2 = atr_vals[i] * ATR_HARD_STOP_MULT
            if bull_sig and a2 > 1e-10:
                entry = close[i]; hard_stop = entry - a2
                risk_r = a2; is_long = True; in_pos = True
            elif bear_sig and a2 > 1e-10:
                entry = close[i]; hard_stop = entry + a2
                risk_r = a2; is_long = False; in_pos = True

    if in_pos and risk_r > 1e-10:
        last = n - 1
        r = (close[last] - entry - SPREAD) / risk_r if is_long else (entry - close[last] - SPREAD) / risk_r
        trades[n_trades] = r; n_trades += 1

    return _compute_metrics(trades, n_trades, ts[0], ts[n-1])


@njit(parallel=True, cache=True)
def search_range(open_, high, low, close, ts,
                 upper_matrix, lower_matrix, atr_vals,
                 entry_rows, exit_rows, warm_bars, buffer_atr, rr,
                 s, e, out_sharpe, out_pf, out_mdd, out_ret, out_ntrades):
    n_grid = len(entry_rows)
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        eu = upper_matrix[entry_rows[g], s:e]
        el = lower_matrix[entry_rows[g], s:e]
        xu = upper_matrix[exit_rows[g], s:e]
        xl = lower_matrix[exit_rows[g], s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e], high[s:e], low[s:e], close[s:e], ts[s:e],
            eu, el, xu, xl, atr_slice,
            int(warm_bars[g]), buffer_atr[g], rr,
        )
        out_sharpe[g] = sharpe; out_pf[g] = pf; out_mdd[g] = mdd
        out_ret[g] = ret; out_ntrades[g] = ntrades
