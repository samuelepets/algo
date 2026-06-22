"""Event-driven backtest engine for tf04_macd_200ema.

MACD line/signal crossover gated by a long-term trend EMA: long entries are only
taken when the close is above EMA(trend), short entries only when below. Exit on
stop, fixed R:R target, or the opposite MACD crossover. The MACD line and signal
are reconstructed inside the kernel from precomputed fast/slow EMAs so the grid
search can share one EMA cache.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from indicators import ATR_PERIOD

SPREAD = 0.00008
MAX_TRADES = 200_000
RR_RATIO = 2.0  # fixed reward-to-risk; not a grid parameter for TF-04


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
def _macd_and_signal(
    fast: np.ndarray, slow: np.ndarray, signal_p: int
) -> tuple[np.ndarray, np.ndarray]:
    """Build MACD line (fast - slow) and its signal EMA over a NaN-prefixed series."""
    n = len(fast)
    macd_line = np.empty(n, dtype=np.float64)
    for i in range(n):
        if np.isnan(fast[i]) or np.isnan(slow[i]):
            macd_line[i] = np.nan
        else:
            macd_line[i] = fast[i] - slow[i]

    signal_line = np.empty(n, dtype=np.float64)
    for i in range(n):
        signal_line[i] = np.nan

    first = -1
    for i in range(n):
        if not np.isnan(macd_line[i]):
            first = i
            break
    if first < 0 or signal_p == 0 or first + signal_p > n:
        return macd_line, signal_line

    seed = 0.0
    for i in range(first, first + signal_p):
        seed += macd_line[i]
    seed /= signal_p
    signal_line[first + signal_p - 1] = seed

    k = 2.0 / (signal_p + 1.0)
    for i in range(first + signal_p, n):
        signal_line[i] = signal_line[i - 1] + k * (macd_line[i] - signal_line[i - 1])
    return macd_line, signal_line


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    fast: np.ndarray,
    slow: np.ndarray,
    trend: np.ndarray,
    atr_vals: np.ndarray,
    slow_p: int,
    trend_p: int,
    signal_p: int,
    atr_mult: float,
    rr: float,
) -> tuple[float, float, float, float, int]:
    """Run backtest on aligned slices; returns metrics tuple."""
    n = len(close)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    macd_line, signal_line = _macd_and_signal(fast, slow, signal_p)

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry = 0.0
    stop = 0.0
    target = 0.0
    risk_r = 0.0

    warm = slow_p + signal_p
    if trend_p > warm:
        warm = trend_p
    if ATR_PERIOD > warm:
        warm = ATR_PERIOD
    warm += 1

    for i in range(warm, n):
        if (
            np.isnan(macd_line[i])
            or np.isnan(signal_line[i])
            or np.isnan(macd_line[i - 1])
            or np.isnan(signal_line[i - 1])
            or np.isnan(trend[i])
            or np.isnan(atr_vals[i])
        ):
            continue

        m_now = macd_line[i]
        m_prev = macd_line[i - 1]
        s_now = signal_line[i]
        s_prev = signal_line[i - 1]

        bull_cross = m_prev <= s_prev and m_now > s_now
        bear_cross = m_prev >= s_prev and m_now < s_now

        just_exited = False
        if in_pos:
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry - SPREAD) / risk_r
                elif high[i] >= target:
                    exit_r = (target - entry - SPREAD) / risk_r
                elif bear_cross:
                    exit_r = (close[i] - entry - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry - stop - SPREAD) / risk_r
                elif low[i] <= target:
                    exit_r = (entry - target - SPREAD) / risk_r
                elif bull_cross:
                    exit_r = (entry - close[i] - SPREAD) / risk_r

            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
                just_exited = True

        if not in_pos and not just_exited:
            atr_v = atr_vals[i]
            long_ok = bull_cross and close[i] > trend[i]
            short_ok = bear_cross and close[i] < trend[i]

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
    atr_vals: np.ndarray,
    fast_rows: np.ndarray,
    slow_rows: np.ndarray,
    trend_rows: np.ndarray,
    slow_p: np.ndarray,
    trend_p: np.ndarray,
    signal_p: np.ndarray,
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
    for g in prange(n_grid):
        fast = ema_matrix[fast_rows[g], s:e]
        slow = ema_matrix[slow_rows[g], s:e]
        trend = ema_matrix[trend_rows[g], s:e]
        atr_slice = atr_vals[s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            fast,
            slow,
            trend,
            atr_slice,
            int(slow_p[g]),
            int(trend_p[g]),
            int(signal_p[g]),
            atr_mult[g],
            rr,
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
