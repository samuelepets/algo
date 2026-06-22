"""Event-driven backtest engine for tf14_hma.

Two modes. ``slope``: enter when the (fast) HMA has risen for ``slope_bars``
consecutive bars and price is above it; exit when the slope turns down. ``crossover``:
enter on a fast/slow HMA crossover; exit on the opposite cross. Both also exit on a
fixed ATR stop or a 2:1 target.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD

SPREAD = 0.00008
MAX_TRADES = 200_000
RR_RATIO = 2.0

MODE_SLOPE = 0
MODE_CROSSOVER = 1


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
def _rising(line: np.ndarray, i: int, bars: int) -> bool:
    for k in range(bars):
        a = line[i - k]
        b = line[i - k - 1]
        if np.isnan(a) or np.isnan(b) or a <= b:
            return False
    return True


@njit(cache=True)
def _falling(line: np.ndarray, i: int, bars: int) -> bool:
    for k in range(bars):
        a = line[i - k]
        b = line[i - k - 1]
        if np.isnan(a) or np.isnan(b) or a >= b:
            return False
    return True


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    hma_fast: np.ndarray,
    hma_slow: np.ndarray,
    atr_vals: np.ndarray,
    warm_bars: int,
    mode: int,
    slope_bars: int,
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

    warm = warm_bars + slope_bars
    if ATR_PERIOD > warm:
        warm = ATR_PERIOD
    warm += 1

    for i in range(warm, n):
        if np.isnan(hma_fast[i]) or np.isnan(hma_fast[i - 1]) or np.isnan(atr_vals[i]):
            continue
        if mode == MODE_CROSSOVER and (np.isnan(hma_slow[i]) or np.isnan(hma_slow[i - 1])):
            continue

        if mode == MODE_CROSSOVER:
            bull_sig = hma_fast[i - 1] <= hma_slow[i - 1] and hma_fast[i] > hma_slow[i]
            bear_sig = hma_fast[i - 1] >= hma_slow[i - 1] and hma_fast[i] < hma_slow[i]
            bull_exit = bear_sig
            bear_exit = bull_sig
        else:
            rising = _rising(hma_fast, i, slope_bars)
            falling = _falling(hma_fast, i, slope_bars)
            bull_sig = rising and close[i] > hma_fast[i]
            bear_sig = falling and close[i] < hma_fast[i]
            bull_exit = hma_fast[i] < hma_fast[i - 1]
            bear_exit = hma_fast[i] > hma_fast[i - 1]

        just_exited = False
        if in_pos:
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry - SPREAD) / risk_r
                elif high[i] >= target:
                    exit_r = (target - entry - SPREAD) / risk_r
                elif bull_exit:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry - stop - SPREAD) / risk_r
                elif low[i] <= target:
                    exit_r = (entry - target - SPREAD) / risk_r
                elif bear_exit:
                    exit_r = (entry - close[i] - SPREAD) / risk_r

            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
                just_exited = True

        if not in_pos and not just_exited:
            dist = atr_vals[i] * atr_mult
            if bull_sig and dist > 1e-10:
                entry = close[i]
                stop = entry - dist
                target = entry + dist * rr
                risk_r = dist
                is_long = True
                in_pos = True
            elif bear_sig and dist > 1e-10:
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
    hma_matrix: np.ndarray,
    atr_vals: np.ndarray,
    fast_rows: np.ndarray,
    slow_rows: np.ndarray,
    warm_bars: np.ndarray,
    mode: np.ndarray,
    slope_bars: np.ndarray,
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
    n_grid = len(fast_rows)
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        hma_fast = hma_matrix[fast_rows[g], s:e]
        hma_slow = hma_matrix[slow_rows[g], s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            hma_fast,
            hma_slow,
            atr_slice,
            int(warm_bars[g]),
            int(mode[g]),
            int(slope_bars[g]),
            atr_mult[g],
            rr,
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
