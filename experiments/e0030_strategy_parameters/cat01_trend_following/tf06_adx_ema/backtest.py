"""Event-driven backtest engine for tf06_adx_ema.

ADX confirms a trending regime; +DI/-DI and price vs. a trend EMA determine the
direction. Long entries require ADX above the threshold, +DI above -DI (or a fresh
+DI/-DI cross when ``di_cross`` is set), and close above the trend EMA. Exit on
stop, fixed R:R target, or a directional flip (-DI rising above +DI for longs).
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD

SPREAD = 0.00008
MAX_TRADES = 200_000
RR_RATIO = 2.0  # fixed reward-to-risk; not a grid parameter for TF-06


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
    trend: np.ndarray,
    adx_vals: np.ndarray,
    plus_di: np.ndarray,
    minus_di: np.ndarray,
    atr_vals: np.ndarray,
    adx_p: int,
    trend_p: int,
    threshold: float,
    di_cross: int,
    atr_mult: float,
    rr: float,
) -> tuple[float, float, float, float, int]:
    """Run backtest on aligned slices; returns metrics tuple."""
    n = len(close)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry = 0.0
    stop = 0.0
    target = 0.0
    risk_r = 0.0

    warm = 2 * adx_p
    if trend_p > warm:
        warm = trend_p
    if ATR_PERIOD > warm:
        warm = ATR_PERIOD
    warm += 1

    for i in range(warm, n):
        if (
            np.isnan(adx_vals[i])
            or np.isnan(plus_di[i])
            or np.isnan(minus_di[i])
            or np.isnan(plus_di[i - 1])
            or np.isnan(minus_di[i - 1])
            or np.isnan(trend[i])
            or np.isnan(atr_vals[i])
        ):
            continue

        pdi = plus_di[i]
        mdi = minus_di[i]
        pdi_prev = plus_di[i - 1]
        mdi_prev = minus_di[i - 1]

        di_cross_up = pdi_prev <= mdi_prev and pdi > mdi
        di_cross_dn = pdi_prev >= mdi_prev and pdi < mdi

        just_exited = False
        if in_pos:
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry - SPREAD) / risk_r
                elif high[i] >= target:
                    exit_r = (target - entry - SPREAD) / risk_r
                elif mdi > pdi:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry - stop - SPREAD) / risk_r
                elif low[i] <= target:
                    exit_r = (entry - target - SPREAD) / risk_r
                elif pdi > mdi:
                    exit_r = (entry - close[i] - SPREAD) / risk_r

            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
                just_exited = True

        if not in_pos and not just_exited:
            atr_v = atr_vals[i]
            adx_ok = adx_vals[i] > threshold
            if di_cross == 1:
                long_dir = di_cross_up
                short_dir = di_cross_dn
            else:
                long_dir = pdi > mdi
                short_dir = mdi > pdi
            long_ok = adx_ok and long_dir and close[i] > trend[i]
            short_ok = adx_ok and short_dir and close[i] < trend[i]

            if long_ok:
                dist = atr_v * atr_mult
                if dist > 1e-10:
                    entry = close[i]
                    stop = entry - dist
                    target = entry + dist * rr
                    risk_r = dist
                    is_long = True
                    in_pos = True
            elif short_ok:
                dist = atr_v * atr_mult
                if dist > 1e-10:
                    entry = close[i]
                    stop = entry + dist
                    target = entry - dist * rr
                    risk_r = dist
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
    ema_matrix: np.ndarray,
    adx_matrix: np.ndarray,
    plus_matrix: np.ndarray,
    minus_matrix: np.ndarray,
    atr_vals: np.ndarray,
    trend_rows: np.ndarray,
    adx_rows: np.ndarray,
    adx_p: np.ndarray,
    trend_p: np.ndarray,
    threshold: np.ndarray,
    di_cross: np.ndarray,
    atr_mult: np.ndarray,
    rr: float,
    s: int,
    e: int,
    out_sharpe: np.ndarray,
    out_pf: np.ndarray,
    out_mdd: np.ndarray,
    out_ret: np.ndarray,
    out_ntrades: np.ndarray,
) -> None:
    """Parallel grid search over ``[s, e)`` using precomputed indicators."""
    n_grid = len(trend_rows)
    for g in prange(n_grid):
        trend = ema_matrix[trend_rows[g], s:e]
        adx_v = adx_matrix[adx_rows[g], s:e]
        plus = plus_matrix[adx_rows[g], s:e]
        minus = minus_matrix[adx_rows[g], s:e]
        atr_slice = atr_vals[s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            trend,
            adx_v,
            plus,
            minus,
            atr_slice,
            int(adx_p[g]),
            int(trend_p[g]),
            threshold[g],
            int(di_cross[g]),
            atr_mult[g],
            rr,
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
