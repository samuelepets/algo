"""Backtest engine for tf16_linreg_channel."""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD, ENTRY_BOUNCE, ENTRY_BREAKOUT

SPREAD = 0.00008
MAX_TRADES = 200_000
RR_RATIO = 2.0


@njit(cache=True)
def _compute_metrics(trades, n_trades, ts_start, ts_end):
    if n_trades < 2:
        return 0.0, 0.0, 0.0, 0.0, n_trades
    mean_r = 0.0
    for i in range(n_trades): mean_r += trades[i]
    mean_r /= n_trades
    var_r = 0.0
    for i in range(n_trades):
        diff = trades[i] - mean_r
        var_r += diff * diff
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
def backtest_core(open_, high, low, close, ts, center, sigma, atr_vals,
                  warm_bars, entry_type, channel_k, atr_mult, rr):
    n = len(close)
    if n < 2: return 0.0, 0.0, 0.0, 0.0, 0
    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0
    in_pos = False; is_long = False
    entry = 0.0; stop = 0.0; target = 0.0; risk_r = 0.0
    warm = max(warm_bars, ATR_PERIOD) + 1

    for i in range(warm, n):
        if np.isnan(center[i]) or np.isnan(sigma[i]) or np.isnan(atr_vals[i]):
            continue
        if np.isnan(center[i-1]) or np.isnan(sigma[i-1]):
            continue

        upper = center[i] + channel_k * sigma[i]
        lower = center[i] - channel_k * sigma[i]
        upper_prev = center[i-1] + channel_k * sigma[i-1]
        lower_prev = center[i-1] - channel_k * sigma[i-1]

        if entry_type == ENTRY_BOUNCE:
            # Long: close crossed above center line
            bull_sig = close[i-1] < center[i-1] and close[i] > center[i]
            # Short: close crossed below center line
            bear_sig = close[i-1] > center[i-1] and close[i] < center[i]
        else:  # ENTRY_BREAKOUT
            # Long: close broke above upper band
            bull_sig = close[i-1] <= upper_prev and close[i] > upper
            # Short: close broke below lower band
            bear_sig = close[i-1] >= lower_prev and close[i] < lower

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
def search_range(open_, high, low, close, ts, center_matrix, sigma_matrix, atr_vals,
                 lr_rows, warm_bars, entry_type, channel_k, atr_mult, rr,
                 s, e, out_sharpe, out_pf, out_mdd, out_ret, out_ntrades):
    n_grid = len(lr_rows)
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        ctr = center_matrix[lr_rows[g], s:e]
        sig = sigma_matrix[lr_rows[g], s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e], high[s:e], low[s:e], close[s:e], ts[s:e],
            ctr, sig, atr_slice,
            int(warm_bars[g]), int(entry_type[g]), channel_k[g], atr_mult[g], rr,
        )
        out_sharpe[g] = sharpe; out_pf[g] = pf; out_mdd[g] = mdd
        out_ret[g] = ret; out_ntrades[g] = ntrades
