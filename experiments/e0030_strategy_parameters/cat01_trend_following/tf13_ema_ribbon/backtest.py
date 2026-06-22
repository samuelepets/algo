"""Event-driven backtest engine for tf13_ema_ribbon.

A ribbon of geometrically-spaced EMAs. Enter on a pullback to the fastest EMA when
the ribbon is sufficiently aligned (fraction of in-order adjacent pairs ≥
alignment_pct) and expanding (fast−slow spacing widening over ``expansion_bars``).
Exit on stop, fixed 2:1 target, or loss of ribbon alignment. The stop is a fixed
ATR(14) multiple (no ATR parameter in this grid, so 1.5× is used).
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD

SPREAD = 0.00008
MAX_TRADES = 200_000
RR_RATIO = 2.0
STOP_ATR_MULT = 1.5  # fixed; ribbon grid has no ATR stop parameter
MAX_RIBBON = 6


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
    ema_slice: np.ndarray,
    rows: np.ndarray,
    count: int,
    atr_vals: np.ndarray,
    slow_period: int,
    alignment_pct: float,
    expansion_bars: int,
    rr: float,
) -> tuple[float, float, float, float, int]:
    """Run backtest on aligned slices; returns metrics tuple.

    ``ema_slice`` is the full ``[n_periods, m]`` EMA matrix sliced to the window;
    ``rows[0:count]`` index its rows fastest-first.
    """
    n = len(close)
    if n < 2 or count < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    fast_row = rows[0]
    slow_row = rows[count - 1]

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry = 0.0
    stop = 0.0
    target = 0.0
    risk_r = 0.0

    warm = slow_period + expansion_bars
    if ATR_PERIOD > warm:
        warm = ATR_PERIOD
    warm += 1

    n_pairs = count - 1
    for i in range(warm, n):
        fast_now = ema_slice[fast_row, i]
        slow_now = ema_slice[slow_row, i]
        if np.isnan(fast_now) or np.isnan(slow_now) or np.isnan(atr_vals[i]):
            continue
        slow_prev = ema_slice[slow_row, i - expansion_bars]
        fast_prev = ema_slice[fast_row, i - expansion_bars]
        if np.isnan(slow_prev) or np.isnan(fast_prev):
            continue

        # Alignment fractions over adjacent ribbon pairs.
        bull_pairs = 0
        bear_pairs = 0
        valid = True
        for k in range(n_pairs):
            a = ema_slice[rows[k], i]
            b = ema_slice[rows[k + 1], i]
            if np.isnan(a) or np.isnan(b):
                valid = False
                break
            if a > b:
                bull_pairs += 1
            elif a < b:
                bear_pairs += 1
        if not valid:
            continue
        bull_frac = bull_pairs / n_pairs
        bear_frac = bear_pairs / n_pairs

        spacing = fast_now - slow_now
        spacing_prev = fast_prev - slow_prev

        just_exited = False
        if in_pos:
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry - SPREAD) / risk_r
                elif high[i] >= target:
                    exit_r = (target - entry - SPREAD) / risk_r
                elif spacing <= 0.0:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry - stop - SPREAD) / risk_r
                elif low[i] <= target:
                    exit_r = (entry - target - SPREAD) / risk_r
                elif spacing >= 0.0:
                    exit_r = (entry - close[i] - SPREAD) / risk_r

            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
                just_exited = True

        if not in_pos and not just_exited:
            dist = atr_vals[i] * STOP_ATR_MULT
            bull = (
                bull_frac >= alignment_pct
                and spacing > spacing_prev
                and low[i] <= fast_now
                and close[i] > fast_now
            )
            bear = (
                bear_frac >= alignment_pct
                and spacing < spacing_prev
                and high[i] >= fast_now
                and close[i] < fast_now
            )
            if bull and dist > 1e-10:
                entry = close[i]
                stop = entry - dist
                target = entry + dist * rr
                risk_r = dist
                is_long = True
                in_pos = True
            elif bear and dist > 1e-10:
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
    atr_vals: np.ndarray,
    ribbon_rows: np.ndarray,
    counts: np.ndarray,
    slow_period: np.ndarray,
    alignment_pct: np.ndarray,
    expansion_bars: np.ndarray,
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
    n_grid = len(counts)
    ema_slice = ema_matrix[:, s:e]
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        rows = ribbon_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            ema_slice,
            rows,
            int(counts[g]),
            atr_slice,
            int(slow_period[g]),
            alignment_pct[g],
            int(expansion_bars[g]),
            rr,
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
