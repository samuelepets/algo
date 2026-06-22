"""Event-driven backtest engine for tf10_parabolic_sar.

Two modes. ``standalone``: enter on a SAR flip, the SAR dot is the trailing stop,
exit on the opposite flip. ``exit_only``: enter on an EMA(9/21) crossover (only when
the SAR already supports the direction, giving a valid trailing stop) and exit on a
SAR flip. P&L is normalised by the initial SAR distance. The SAR is reconstructed
inside the kernel from the high/low arrays and the AF parameters.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import parabolic_sar

SPREAD = 0.00008
MAX_TRADES = 200_000

MODE_STANDALONE = 0
MODE_EXIT_ONLY = 1
EXIT_FAST_EMA = 9
EXIT_SLOW_EMA = 21


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
    ema_fast: np.ndarray,
    ema_slow: np.ndarray,
    af_start: float,
    af_step: float,
    af_max: float,
    mode: int,
    slow_p: int,
) -> tuple[float, float, float, float, int]:
    """Run backtest on aligned slices; returns metrics tuple."""
    n = len(close)
    if n < 3:
        return 0.0, 0.0, 0.0, 0.0, 0

    sar, direction = parabolic_sar(high, low, af_start, af_step, af_max)

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry = 0.0
    risk_r = 0.0

    warm = slow_p + 1
    if warm < 3:
        warm = 3

    for i in range(warm, n):
        if direction[i] == 0 or direction[i - 1] == 0 or np.isnan(sar[i]):
            continue

        flip_up = direction[i - 1] == -1 and direction[i] == 1
        flip_dn = direction[i - 1] == 1 and direction[i] == -1

        just_exited = False
        if in_pos:
            exit_r = np.nan
            stop = sar[i]
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry - SPREAD) / risk_r
                elif direction[i] == -1:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry - stop - SPREAD) / risk_r
                elif direction[i] == 1:
                    exit_r = (entry - close[i] - SPREAD) / risk_r

            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
                just_exited = True

        if not in_pos and not just_exited:
            long_sig = False
            short_sig = False
            if mode == MODE_STANDALONE:
                long_sig = flip_up
                short_sig = flip_dn
            else:
                if (
                    not np.isnan(ema_fast[i])
                    and not np.isnan(ema_slow[i])
                    and not np.isnan(ema_fast[i - 1])
                    and not np.isnan(ema_slow[i - 1])
                ):
                    long_sig = ema_fast[i - 1] < ema_slow[i - 1] and ema_fast[i] > ema_slow[i]
                    short_sig = ema_fast[i - 1] > ema_slow[i - 1] and ema_fast[i] < ema_slow[i]

            stop0 = sar[i]
            if long_sig:
                dist = close[i] - stop0
                if dist > 1e-10:
                    entry = close[i]
                    risk_r = dist
                    is_long = True
                    in_pos = True
            elif short_sig:
                dist = stop0 - close[i]
                if dist > 1e-10:
                    entry = close[i]
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
    ema_fast: np.ndarray,
    ema_slow: np.ndarray,
    af_start: np.ndarray,
    af_step: np.ndarray,
    af_max: np.ndarray,
    mode: np.ndarray,
    slow_p: int,
    s: int,
    e: int,
    out_sharpe: np.ndarray,
    out_pf: np.ndarray,
    out_mdd: np.ndarray,
    out_ret: np.ndarray,
    out_ntrades: np.ndarray,
) -> None:
    """Parallel grid search over ``[s, e)`` using precomputed indicators."""
    n_grid = len(af_start)
    ema_fast_slice = ema_fast[s:e]
    ema_slow_slice = ema_slow[s:e]
    for g in prange(n_grid):
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            ema_fast_slice,
            ema_slow_slice,
            af_start[g],
            af_step[g],
            af_max[g],
            int(mode[g]),
            slow_p,
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
