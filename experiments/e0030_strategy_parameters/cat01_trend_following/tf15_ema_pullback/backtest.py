"""Event-driven backtest engine for tf15_ema_pullback.

Strategy: EMA Pullback to Dynamic Support. In an uptrend (Close > slow_ema),
wait for price to pull back to touch the fast EMA, then confirm entry with a
rejection bar. Mirror logic for shorts.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD

SPREAD = 0.00008
MAX_TRADES = 200_000
RR_RATIO = 2.0

# Candle pattern constants
PATTERN_ENGULFING = 0
PATTERN_HAMMER = 1
PATTERN_ANY = 2
PATTERN_NONE = 3

# Pullback touch constants
TOUCH_LOW = 0    # Low <= fast_ema (for long) / High >= fast_ema (for short)
TOUCH_CLOSE = 1  # |Close - fast_ema| / fast_ema < 0.001


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
def _check_pattern_long(pattern: int, open_: np.ndarray, close: np.ndarray, high: np.ndarray, low: np.ndarray, i: int) -> bool:
    """Return True if bar i matches the bullish candle pattern."""
    if pattern == PATTERN_ENGULFING:
        return (
            close[i] > open_[i]
            and close[i] > close[i - 1]
            and open_[i] < open_[i - 1]
        )
    elif pattern == PATTERN_HAMMER:
        body = abs(close[i] - open_[i])
        lower_shadow = min(close[i], open_[i]) - low[i]
        upper_shadow = high[i] - max(close[i], open_[i])
        return lower_shadow > 2.0 * body and upper_shadow < body
    elif pattern == PATTERN_ANY:
        return close[i] > open_[i]
    else:  # PATTERN_NONE
        return True


@njit(cache=True)
def _check_pattern_short(pattern: int, open_: np.ndarray, close: np.ndarray, high: np.ndarray, low: np.ndarray, i: int) -> bool:
    """Return True if bar i matches the bearish candle pattern."""
    if pattern == PATTERN_ENGULFING:
        return (
            close[i] < open_[i]
            and close[i] < close[i - 1]
            and open_[i] > open_[i - 1]
        )
    elif pattern == PATTERN_HAMMER:
        body = abs(close[i] - open_[i])
        upper_shadow = high[i] - max(close[i], open_[i])
        lower_shadow = min(close[i], open_[i]) - low[i]
        return upper_shadow > 2.0 * body and lower_shadow < body
    elif pattern == PATTERN_ANY:
        return close[i] < open_[i]
    else:  # PATTERN_NONE
        return True


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    ema_fast: np.ndarray,
    ema_slow: np.ndarray,
    atr_vals: np.ndarray,
    warm_bars: int,
    touch_type: int,
    pattern: int,
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

    warm = warm_bars
    if ATR_PERIOD > warm:
        warm = ATR_PERIOD
    warm += 1

    for i in range(warm, n):
        if np.isnan(ema_fast[i]) or np.isnan(ema_slow[i]) or np.isnan(atr_vals[i]):
            continue

        if not in_pos:
            uptrend_long = close[i] > ema_slow[i]
            uptrend_short = close[i] < ema_slow[i]

            # Pullback touch check
            if touch_type == TOUCH_LOW:
                touched_long = low[i] <= ema_fast[i]
                touched_short = high[i] >= ema_fast[i]
            else:  # TOUCH_CLOSE
                rel_diff = abs(close[i] - ema_fast[i]) / ema_fast[i]
                touched_long = rel_diff < 0.001
                touched_short = rel_diff < 0.001

            # Rejection (price bounced away from fast_ema)
            rejected_long = close[i] > ema_fast[i]
            rejected_short = close[i] < ema_fast[i]

            bull_pattern = _check_pattern_long(pattern, open_, close, high, low, i)
            bear_pattern = _check_pattern_short(pattern, open_, close, high, low, i)

            bull_sig = uptrend_long and touched_long and rejected_long and bull_pattern
            bear_sig = uptrend_short and touched_short and rejected_short and bear_pattern

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

        if in_pos:
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry - SPREAD) / risk_r
                elif high[i] >= target:
                    exit_r = (target - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry - stop - SPREAD) / risk_r
                elif low[i] <= target:
                    exit_r = (entry - target - SPREAD) / risk_r

            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False

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
    fast_rows: np.ndarray,
    slow_rows: np.ndarray,
    warm_bars: np.ndarray,
    touch_type: np.ndarray,
    pattern: np.ndarray,
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
        ema_fast = ema_matrix[fast_rows[g], s:e]
        ema_slow = ema_matrix[slow_rows[g], s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            ema_fast,
            ema_slow,
            atr_slice,
            int(warm_bars[g]),
            int(touch_type[g]),
            int(pattern[g]),
            atr_mult[g],
            rr,
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
