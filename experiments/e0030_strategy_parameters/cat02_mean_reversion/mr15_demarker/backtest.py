"""Backtest engine for mr15_demarker.

Strategy: fade DeMarker extremes. Long when DeMarker crosses below
``oversold_thresh``; short when it crosses above ``overbought_thresh``. Exit
when DeMarker crosses back through ``exit_level`` (0.50), on a forced-exit
safety net, or on an ATR stop.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics
from indicators import ATR_FLOOR

SPREAD = 0.00008
MAX_TRADES = 200_000

# Forced-exit safety net: DeMarker crossing exit_level is not guaranteed to
# happen promptly (it can stay pinned at an extreme through a strong trend).
# 100 bars is not a grid dimension per the spec -- fixed here and documented
# in README.
FORCED_EXIT_BARS = 100


@njit(cache=True)
def backtest_core(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ts: np.ndarray,
    dem_vals: np.ndarray,
    atr_vals: np.ndarray,
    oversold_thresh: float,
    overbought_thresh: float,
    exit_level: float,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run DeMarker mean-reversion backtest on aligned slices."""
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
        d = dem_vals[i]
        d_prev = dem_vals[i - 1]
        a = atr_vals[i]
        if np.isnan(d) or np.isnan(d_prev) or np.isnan(a) or a < ATR_FLOOR:
            continue

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif d_prev < exit_level <= d:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif d_prev > exit_level >= d:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        bull_sig = d_prev >= oversold_thresh and d < oversold_thresh
        bear_sig = d_prev <= overbought_thresh and d > overbought_thresh

        dist = atr_stop_mult * a
        if bull_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price - dist
            risk_r = dist
            is_long = True
            in_pos = True
            bars_held = 0
        elif bear_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price + dist
            risk_r = dist
            is_long = False
            in_pos = True
            bars_held = 0

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
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ts: np.ndarray,
    dem_matrix: np.ndarray,
    atr_vals: np.ndarray,
    period_rows: np.ndarray,
    oversold_thresh: np.ndarray,
    overbought_thresh: np.ndarray,
    exit_level: np.ndarray,
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
    """Parallel grid search over ``[s, e)`` using precomputed DeMarker cache."""
    n_grid = len(period_rows)
    atr_slice = atr_vals[s:e]
    close_slice = close[s:e]
    high_slice = high[s:e]
    low_slice = low[s:e]
    ts_slice = ts[s:e]
    for g in prange(n_grid):
        row = period_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            close_slice,
            high_slice,
            low_slice,
            ts_slice,
            dem_matrix[row, s:e],
            atr_slice,
            oversold_thresh[g],
            overbought_thresh[g],
            exit_level[g],
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
