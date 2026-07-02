"""Backtest engine for mr18_hl_channel_fade.

Strategy: fade the edges of a rolling High/Low range, confirmed by a tight
ATR/range-width ratio (range-bound filter). Long entry near the range low,
short entry near the range high; target the range center or the opposite
side; stop beyond entry by an ATR multiple.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics
from indicators import ATR_FLOOR

SPREAD = 0.00008
MAX_TRADES = 200_000

TARGET_CENTER = 0
TARGET_OPPOSITE = 1

# No max_hold_bars dimension in the MR-18 grid. A generous fixed forced-exit
# safety net avoids indefinitely-held positions; not grid-searched per spec.
FORCED_EXIT_BARS = 100


@njit(cache=True)
def backtest_core(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ts: np.ndarray,
    range_high: np.ndarray,
    range_low: np.ndarray,
    atr_vals: np.ndarray,
    entry_pct: float,
    atr_range_ratio: float,
    target_mode: int,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run High-Low channel fade backtest on aligned slices."""
    n = len(close)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry_price = 0.0
    stop = 0.0
    target_price = 0.0
    risk_r = 0.0
    bars_held = 0

    warm = warm_bars + 1

    for i in range(warm, n):
        rh = range_high[i]
        rl = range_low[i]
        a = atr_vals[i]
        if np.isnan(rh) or np.isnan(rl) or np.isnan(a) or a < ATR_FLOOR:
            continue

        width = rh - rl
        if width < 1e-10:
            continue

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif high[i] >= target_price:
                    exit_r = (target_price - entry_price - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif low[i] <= target_price:
                    exit_r = (entry_price - target_price - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        # Range-confirmation filter: only trade a genuinely tight range.
        if a / width > atr_range_ratio:
            continue

        center = (rh + rl) * 0.5
        half = width * 0.5
        long_trigger = center - entry_pct * half
        short_trigger = center + entry_pct * half

        bull_sig = close[i] <= long_trigger
        bear_sig = close[i] >= short_trigger

        dist = atr_stop_mult * a
        if bull_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price - dist
            risk_r = dist
            target_price = center if target_mode == TARGET_CENTER else rh
            is_long = True
            in_pos = True
            bars_held = 0
        elif bear_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price + dist
            risk_r = dist
            target_price = center if target_mode == TARGET_CENTER else rl
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
    range_high_matrix: np.ndarray,
    range_low_matrix: np.ndarray,
    atr_vals: np.ndarray,
    period_rows: np.ndarray,
    entry_pct: np.ndarray,
    atr_range_ratio: np.ndarray,
    target_mode: np.ndarray,
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
    """Parallel grid search over ``[s, e)`` using precomputed range cache."""
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
            range_high_matrix[row, s:e],
            range_low_matrix[row, s:e],
            atr_slice,
            entry_pct[g],
            atr_range_ratio[g],
            int(target_mode[g]),
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
