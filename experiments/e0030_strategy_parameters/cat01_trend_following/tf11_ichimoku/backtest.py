"""Event-driven backtest engine for tf11_ichimoku.

Ichimoku entries with three signal variants (full signal, TK cross, cloud
breakout). The Kijun-sen acts as the trailing stop; a fixed 2:1 target provides
the profit exit. Senkou spans are displaced forward by the Kijun period and the
Chikou test compares the close to the close ``disp`` bars ago.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

SPREAD = 0.00008
MAX_TRADES = 200_000
RR_RATIO = 2.0

SIGNAL_FULL = 0
SIGNAL_TK = 1
SIGNAL_CLOUD = 2


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
    tenkan: np.ndarray,
    kijun: np.ndarray,
    senkb_base: np.ndarray,
    disp: int,
    senkou_b_p: int,
    signal_type: int,
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
    target = 0.0
    risk_r = 0.0

    warm = senkou_b_p + disp + 2

    for i in range(warm, n):
        if (
            np.isnan(tenkan[i])
            or np.isnan(kijun[i])
            or np.isnan(tenkan[i - 1])
            or np.isnan(kijun[i - 1])
            or np.isnan(senkb_base[i - disp])
            or np.isnan(tenkan[i - disp])
            or np.isnan(kijun[i - disp])
        ):
            continue

        span_a = (tenkan[i - disp] + kijun[i - disp]) / 2.0
        span_b = senkb_base[i - disp]
        span_a_prev = (tenkan[i - 1 - disp] + kijun[i - 1 - disp]) / 2.0
        span_b_prev = senkb_base[i - 1 - disp]
        cloud_top = span_a if span_a > span_b else span_b
        cloud_bot = span_a if span_a < span_b else span_b
        cloud_top_prev = span_a_prev if span_a_prev > span_b_prev else span_b_prev
        cloud_bot_prev = span_a_prev if span_a_prev < span_b_prev else span_b_prev

        tk_up = tenkan[i - 1] <= kijun[i - 1] and tenkan[i] > kijun[i]
        tk_dn = tenkan[i - 1] >= kijun[i - 1] and tenkan[i] < kijun[i]

        just_exited = False
        if in_pos:
            exit_r = np.nan
            stop = kijun[i]
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry - SPREAD) / risk_r
                elif high[i] >= target:
                    exit_r = (target - entry - SPREAD) / risk_r
                elif tk_dn:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry - stop - SPREAD) / risk_r
                elif low[i] <= target:
                    exit_r = (entry - target - SPREAD) / risk_r
                elif tk_up:
                    exit_r = (entry - close[i] - SPREAD) / risk_r

            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
                just_exited = True

        if not in_pos and not just_exited:
            chikou_up = close[i] > close[i - disp]
            chikou_dn = close[i] < close[i - disp]
            long_ok = False
            short_ok = False
            if signal_type == SIGNAL_TK:
                long_ok = tk_up and close[i] > cloud_top
                short_ok = tk_dn and close[i] < cloud_bot
            elif signal_type == SIGNAL_CLOUD:
                long_ok = close[i] > cloud_top and close[i - 1] <= cloud_top_prev
                short_ok = close[i] < cloud_bot and close[i - 1] >= cloud_bot_prev
            else:  # SIGNAL_FULL
                long_ok = tk_up and close[i] > cloud_top and span_a > span_b and chikou_up
                short_ok = tk_dn and close[i] < cloud_bot and span_a < span_b and chikou_dn

            stop0 = kijun[i]
            if long_ok:
                dist = close[i] - stop0
                if dist > 1e-10:
                    entry = close[i]
                    risk_r = dist
                    target = entry + rr * dist
                    is_long = True
                    in_pos = True
            elif short_ok:
                dist = stop0 - close[i]
                if dist > 1e-10:
                    entry = close[i]
                    risk_r = dist
                    target = entry - rr * dist
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
    mid_matrix: np.ndarray,
    tenkan_rows: np.ndarray,
    kijun_rows: np.ndarray,
    senkb_rows: np.ndarray,
    disp: np.ndarray,
    senkou_b_p: np.ndarray,
    signal_type: np.ndarray,
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
    n_grid = len(tenkan_rows)
    for g in prange(n_grid):
        tenkan = mid_matrix[tenkan_rows[g], s:e]
        kijun = mid_matrix[kijun_rows[g], s:e]
        senkb = mid_matrix[senkb_rows[g], s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            tenkan,
            kijun,
            senkb,
            int(disp[g]),
            int(senkou_b_p[g]),
            int(signal_type[g]),
            rr,
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
