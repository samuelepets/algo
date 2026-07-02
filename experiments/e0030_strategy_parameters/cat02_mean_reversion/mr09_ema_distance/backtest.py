"""Backtest engine for mr09_ema_distance.

Strategy: fade price when its ATR-normalised distance from an EMA exceeds a
threshold ("rubber band"), targeting either the (dynamically-updated) EMA
itself or half the entry distance back toward the EMA. An optional ADX filter
restricts entries to non-trending regimes. Because the strategy has no
`max_hold_bars` grid dimension, a fixed forced-exit safety net
(`FORCED_EXIT_BARS`) prevents indefinitely-held positions.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics
from indicators import ATR_FLOOR

SPREAD = 0.00008
MAX_TRADES = 200_000

# No max_hold_bars dimension in the MR-09 grid (see strategies doc). A
# generous fixed forced-exit safety net avoids indefinitely-held positions;
# 100 bars is used uniformly across all three timeframes (1/5/15-min).
FORCED_EXIT_BARS = 100

EXIT_EMA = 0            # target = EMA value, updated every bar
EXIT_HALF_DISTANCE = 1  # target = fixed price level set at entry


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    ema_vals: np.ndarray,
    atr_vals: np.ndarray,
    adx_vals: np.ndarray,
    distance_thresh: float,
    exit_target: int,
    adx_filter: int,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run EMA-distance mean-reversion backtest; returns metrics tuple."""
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
    half_target = 0.0

    warm = warm_bars + 1

    for i in range(warm, n):
        e = ema_vals[i]
        a = atr_vals[i]

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            target = e if exit_target == EXIT_EMA else half_target
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif not np.isnan(target) and close[i] >= target:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif not np.isnan(target) and close[i] <= target:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        if np.isnan(e) or np.isnan(a) or a < ATR_FLOOR:
            continue

        # ADX filter: skip entry if ADX >= threshold
        if adx_filter > 0:
            adx_val = adx_vals[i]
            if np.isnan(adx_val) or adx_val >= adx_filter:
                continue

        dist_price = close[i] - e
        dist_atr = dist_price / a
        bull_sig = dist_atr < -distance_thresh
        bear_sig = dist_atr > distance_thresh

        stop_dist = a * atr_stop_mult
        if bull_sig and stop_dist > 1e-10:
            entry_price = close[i]
            stop = entry_price - stop_dist
            risk_r = stop_dist
            is_long = True
            in_pos = True
            bars_held = 0
            half_target = entry_price - dist_price / 2.0
        elif bear_sig and stop_dist > 1e-10:
            entry_price = close[i]
            stop = entry_price + stop_dist
            risk_r = stop_dist
            is_long = False
            in_pos = True
            bars_held = 0
            half_target = entry_price - dist_price / 2.0

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
    ema_matrix: np.ndarray,
    atr_matrix: np.ndarray,
    adx_vals: np.ndarray,
    ema_rows: np.ndarray,
    atr_rows: np.ndarray,
    distance_thresh: np.ndarray,
    exit_target: np.ndarray,
    adx_filter: np.ndarray,
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
    n_grid = len(ema_rows)
    adx_slice = adx_vals[s:e]
    for g in prange(n_grid):
        erow = ema_rows[g]
        arow = atr_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            ema_matrix[erow, s:e],
            atr_matrix[arow, s:e],
            adx_slice,
            distance_thresh[g],
            int(exit_target[g]),
            int(adx_filter[g]),
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
