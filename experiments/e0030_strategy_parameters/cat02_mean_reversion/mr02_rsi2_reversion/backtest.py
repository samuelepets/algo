"""Backtest engine for mr02_rsi2_reversion.

Strategy: RSI(2)-style ultra-short mean reversion. Enter long when RSI drops
below ``long_threshold`` (extreme oversold), enter short when RSI rises above
``short_threshold`` (extreme overbought). An optional SMA trend filter
restricts longs to above the SMA and shorts to below it. Exit on a fixed
1.5x ATR stop, on RSI crossing back through an exit threshold, or after a
maximum holding period — whichever comes first (stop has priority).
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
ATR_STOP_MULT = 1.5  # fixed per spec, not a grid dimension


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    rsi_vals: np.ndarray,
    trend_sma_vals: np.ndarray,
    atr_vals: np.ndarray,
    long_threshold: float,
    short_threshold: float,
    exit_rsi_long: float,
    exit_rsi_short: float,
    trend_ema: int,
    max_hold_bars: int,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run RSI(2) reversion backtest on aligned slices; returns metrics tuple."""
    n = len(close)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry_price = 0.0
    stop = 0.0
    risk_r = 0.0
    bars_held = 0

    warm = warm_bars + 1

    for i in range(warm, n):
        r = rsi_vals[i]
        a = atr_vals[i]
        if np.isnan(r) or np.isnan(a):
            continue

        tsma = 0.0
        if trend_ema > 0:
            tsma = trend_sma_vals[i]
            if np.isnan(tsma):
                continue

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif r >= exit_rsi_long:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif r <= exit_rsi_short:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        dist = ATR_STOP_MULT * a
        if dist <= 1e-10:
            continue

        long_sig = (trend_ema == 0 or close[i] > tsma) and r < long_threshold
        short_sig = (trend_ema == 0 or close[i] < tsma) and r > short_threshold

        if long_sig:
            entry_price = close[i]
            stop = entry_price - dist
            risk_r = dist
            is_long = True
            in_pos = True
            bars_held = 0
        elif short_sig:
            entry_price = close[i]
            stop = entry_price + dist
            risk_r = dist
            is_long = False
            in_pos = True
            bars_held = 0

    # Close open position at last bar
    if in_pos and risk_r > 1e-10:
        last = n - 1
        if is_long:
            r_final = (close[last] - entry_price - SPREAD) / risk_r
        else:
            r_final = (entry_price - close[last] - SPREAD) / risk_r
        trades[n_trades] = r_final
        n_trades += 1

    return compute_metrics(trades, n_trades, ts[0], ts[n - 1])


@njit(parallel=True, cache=True)
def search_range(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    rsi_matrix: np.ndarray,
    trend_sma_matrix: np.ndarray,
    atr_vals: np.ndarray,
    rsi_row: np.ndarray,
    trend_row: np.ndarray,
    long_threshold: np.ndarray,
    short_threshold: np.ndarray,
    exit_rsi_long: np.ndarray,
    exit_rsi_short: np.ndarray,
    trend_ema: np.ndarray,
    max_hold_bars: np.ndarray,
    warm_bars: np.ndarray,
    s: int,
    e: int,
    out_sharpe: np.ndarray,
    out_pf: np.ndarray,
    out_mdd: np.ndarray,
    out_ret: np.ndarray,
    out_ntrades: np.ndarray,
) -> None:
    """Parallel grid search over ``[s, e)`` using precomputed indicators."""
    n_grid = len(rsi_row)
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        r_row = rsi_row[g]
        t_row = trend_row[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            rsi_matrix[r_row, s:e],
            trend_sma_matrix[t_row, s:e],
            atr_slice,
            long_threshold[g],
            short_threshold[g],
            exit_rsi_long[g],
            exit_rsi_short[g],
            int(trend_ema[g]),
            int(max_hold_bars[g]),
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
