"""Event-driven backtest engine for tf08_supertrend_vwap_adx.

Triple-confirmation entry: SuperTrend direction, price vs. session VWAP, price vs.
a trend EMA, and ADX above a threshold must all agree. The SuperTrend line is the
trailing stop; a fixed ATR-multiple target provides the profit exit. SuperTrend is
reconstructed inside the kernel from a per-period ATR cache.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import supertrend

SPREAD = 0.00008
MAX_TRADES = 200_000


@njit(cache=True)
def _compute_metrics(
    trades: np.ndarray,
    n_trades: int,
    ts_start: int,
    ts_end: int,
) -> tuple[float, float, float, float, int]:
    if n_trades < 2:
        return 0.0, 0.0, 0.0, 0.0, n_trades

    mean_r = 0.0
    for i in range(n_trades):
        mean_r += trades[i]
    mean_r /= n_trades

    var_r = 0.0
    for i in range(n_trades):
        diff = trades[i] - mean_r
        var_r += diff * diff
    var_r /= n_trades - 1
    std_r = var_r**0.5

    span_years = 1.0
    if ts_end > ts_start:
        span_years = (ts_end - ts_start) / (365.25 * 24.0 * 3600.0)
    if span_years < 0.01:
        span_years = 0.01
    trades_per_year = n_trades / span_years

    sharpe = 0.0
    if std_r > 1e-12:
        sharpe = (mean_r / std_r) * (trades_per_year**0.5)

    gross_win = 0.0
    gross_loss = 0.0
    total_return = 0.0
    for i in range(n_trades):
        r = trades[i]
        total_return += r
        if r > 0.0:
            gross_win += r
        elif r < 0.0:
            gross_loss += -r

    profit_factor = 0.0
    if gross_loss > 1e-12:
        profit_factor = gross_win / gross_loss
    elif gross_win > 0.0:
        profit_factor = np.inf

    cum_r = 0.0
    peak = 0.0
    max_dd = 0.0
    for i in range(n_trades):
        cum_r += trades[i]
        if cum_r > peak:
            peak = cum_r
        dd = peak - cum_r
        if dd > max_dd:
            max_dd = dd

    return sharpe, profit_factor, max_dd, total_return, n_trades


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    atr_vals: np.ndarray,
    vwap: np.ndarray,
    trend: np.ndarray,
    adx_vals: np.ndarray,
    st_atr_p: int,
    trend_p: int,
    adx_p: int,
    mult: float,
    threshold: float,
    atr_target: float,
) -> tuple[float, float, float, float, int]:
    """Run backtest on aligned slices; returns metrics tuple."""
    n = len(close)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    st_line, direction = supertrend(high, low, close, atr_vals, mult)

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry = 0.0
    target = 0.0
    risk_r = 0.0

    warm = st_atr_p
    if 2 * adx_p > warm:
        warm = 2 * adx_p
    if trend_p > warm:
        warm = trend_p
    warm += 1

    for i in range(warm, n):
        if (
            direction[i] == 0
            or np.isnan(st_line[i])
            or np.isnan(atr_vals[i])
            or np.isnan(vwap[i])
            or np.isnan(trend[i])
            or np.isnan(adx_vals[i])
        ):
            continue

        just_exited = False
        if in_pos:
            exit_r = np.nan
            stop = st_line[i]
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry - SPREAD) / risk_r
                elif high[i] >= target:
                    exit_r = (target - entry - SPREAD) / risk_r
                elif direction[i] == -1:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry - stop - SPREAD) / risk_r
                elif low[i] <= target:
                    exit_r = (entry - target - SPREAD) / risk_r
                elif direction[i] == 1:
                    exit_r = (entry - close[i] - SPREAD) / risk_r

            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
                just_exited = True

        if not in_pos and not just_exited:
            adx_ok = adx_vals[i] > threshold
            long_ok = (
                direction[i] == 1
                and close[i] > vwap[i]
                and close[i] > trend[i]
                and adx_ok
            )
            short_ok = (
                direction[i] == -1
                and close[i] < vwap[i]
                and close[i] < trend[i]
                and adx_ok
            )
            if long_ok:
                stop0 = st_line[i]
                dist = close[i] - stop0
                if dist > 1e-10:
                    entry = close[i]
                    risk_r = dist
                    target = entry + atr_target * atr_vals[i]
                    is_long = True
                    in_pos = True
            elif short_ok:
                stop0 = st_line[i]
                dist = stop0 - close[i]
                if dist > 1e-10:
                    entry = close[i]
                    risk_r = dist
                    target = entry - atr_target * atr_vals[i]
                    is_long = False
                    in_pos = True

    if in_pos and risk_r > 1e-10:
        last = n - 1
        if is_long:
            r = (close[last] - entry - SPREAD) / risk_r
        else:
            r = (entry - close[last] - SPREAD) / risk_r
        trades[n_trades] = r
        n_trades += 1

    ts_start = ts[0]
    ts_end = ts[n - 1]
    return _compute_metrics(trades, n_trades, ts_start, ts_end)


@njit(parallel=True, cache=True)
def search_range(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    atr_matrix: np.ndarray,
    vwap: np.ndarray,
    ema_matrix: np.ndarray,
    adx_matrix: np.ndarray,
    st_atr_rows: np.ndarray,
    trend_rows: np.ndarray,
    adx_rows: np.ndarray,
    st_atr_p: np.ndarray,
    trend_p: np.ndarray,
    adx_p: np.ndarray,
    mult: np.ndarray,
    threshold: np.ndarray,
    atr_target: np.ndarray,
    s: int,
    e: int,
    out_sharpe: np.ndarray,
    out_pf: np.ndarray,
    out_mdd: np.ndarray,
    out_ret: np.ndarray,
    out_ntrades: np.ndarray,
) -> None:
    """Parallel grid search over ``[s, e)`` using precomputed indicators."""
    n_grid = len(st_atr_rows)
    vwap_slice = vwap[s:e]
    for g in prange(n_grid):
        atr_slice = atr_matrix[st_atr_rows[g], s:e]
        trend = ema_matrix[trend_rows[g], s:e]
        adx_v = adx_matrix[adx_rows[g], s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            atr_slice,
            vwap_slice,
            trend,
            adx_v,
            int(st_atr_p[g]),
            int(trend_p[g]),
            int(adx_p[g]),
            mult[g],
            threshold[g],
            atr_target[g],
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
