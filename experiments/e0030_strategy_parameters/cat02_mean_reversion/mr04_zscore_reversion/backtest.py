"""Backtest engine for mr04_zscore_reversion.

Strategy: fade statistical extremes of a rolling z-score (of either
log-returns or detrended close price). Entry when |z| exceeds an entry
threshold; exit when z reverts back inside an exit threshold, or on an
ATR-based stop, or on a fixed-bar forced-exit safety net (no max-hold grid
dimension for this strategy).
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000

# Fixed (not grid-searched) safety net bounding worst-case holding time.
MAX_HOLD_SAFETY = 200

INPUT_LOG_RETURN = 0        # z-score of log-returns
INPUT_CLOSE_DETRENDED = 1   # z-score of close price vs its rolling mean


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    z_vals: np.ndarray,
    atr_vals: np.ndarray,
    entry_threshold: float,
    exit_threshold: float,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run z-score mean-reversion backtest on aligned slices; returns metrics tuple."""
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
        zv = z_vals[i]
        a = atr_vals[i]

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif not np.isnan(zv) and zv >= -exit_threshold:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= MAX_HOLD_SAFETY:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif not np.isnan(zv) and zv <= exit_threshold:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= MAX_HOLD_SAFETY:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        if np.isnan(zv) or np.isnan(a):
            continue

        long_sig = zv < -entry_threshold
        short_sig = zv > entry_threshold

        dist = atr_stop_mult * a
        if long_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price - dist
            risk_r = dist
            is_long = True
            in_pos = True
            bars_held = 0
        elif short_sig and dist > 1e-10:
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
            r = (close[last] - entry_price - SPREAD) / risk_r
        else:
            r = (entry_price - close[last] - SPREAD) / risk_r
        trades[n_trades] = r
        n_trades += 1

    return compute_metrics(trades, n_trades, ts[0], ts[n - 1])


@njit(parallel=True, cache=True)
def search_range(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    log_return_matrix: np.ndarray,
    close_detrended_matrix: np.ndarray,
    atr_vals: np.ndarray,
    window_rows: np.ndarray,
    input_type: np.ndarray,
    entry_threshold: np.ndarray,
    exit_threshold: np.ndarray,
    atr_stop_mult: np.ndarray,
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
    n_grid = len(window_rows)
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        row = window_rows[g]
        if input_type[g] == INPUT_LOG_RETURN:
            z_slice = log_return_matrix[row, s:e]
        else:
            z_slice = close_detrended_matrix[row, s:e]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            z_slice,
            atr_slice,
            entry_threshold[g],
            exit_threshold[g],
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
