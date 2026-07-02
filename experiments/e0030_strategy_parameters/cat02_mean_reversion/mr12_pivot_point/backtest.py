"""Backtest engine for mr12_pivot_point.

Strategy: fade the approach to S1/R1 (or the extended S2/R2), targeting the
central pivot P (or the midpoint between the fade level and P). "Touch" is
defined as price coming within ``touch_atr_thresh × ATR(14)`` of the fade
level. Stop is a simplified fixed ATR distance from entry (see README for
why this departs from the prose spec's "beyond S2/R2 + ATR buffer").
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics
from indicators import ATR_FLOOR

SPREAD = 0.00008
MAX_TRADES = 200_000

FADE_S1_R1 = 0
FADE_S2_R2 = 1

TARGET_P = 0
TARGET_MID = 1

# No max_hold_bars dimension in the MR-12 grid. A generous fixed forced-exit
# safety net avoids indefinitely-held positions.
FORCED_EXIT_BARS = 100


@njit(cache=True)
def backtest_core(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ts: np.ndarray,
    piv_p: np.ndarray,
    piv_r1: np.ndarray,
    piv_r2: np.ndarray,
    piv_s1: np.ndarray,
    piv_s2: np.ndarray,
    atr_vals: np.ndarray,
    fade_level: int,
    touch_atr_thresh: float,
    target_mode: int,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run pivot-point reversion backtest on aligned slices."""
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
        p = piv_p[i]
        a = atr_vals[i]
        if np.isnan(p) or np.isnan(a) or a < ATR_FLOOR:
            continue

        support = piv_s1[i] if fade_level == FADE_S1_R1 else piv_s2[i]
        resistance = piv_r1[i] if fade_level == FADE_S1_R1 else piv_r2[i]

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

        touch_dist = touch_atr_thresh * a
        bull_sig = close[i] <= support + touch_dist
        bear_sig = close[i] >= resistance - touch_dist

        dist = atr_stop_mult * a
        if bull_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price - dist
            risk_r = dist
            target_price = p if target_mode == TARGET_P else (support + p) * 0.5
            is_long = True
            in_pos = True
            bars_held = 0
        elif bear_sig and dist > 1e-10:
            entry_price = close[i]
            stop = entry_price + dist
            risk_r = dist
            target_price = p if target_mode == TARGET_P else (resistance + p) * 0.5
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
    piv_p: np.ndarray,
    piv_r1: np.ndarray,
    piv_r2: np.ndarray,
    piv_s1: np.ndarray,
    piv_s2: np.ndarray,
    atr_vals: np.ndarray,
    fade_level: np.ndarray,
    touch_atr_thresh: np.ndarray,
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
    """Parallel grid search over ``[s, e)`` using precomputed pivot cache."""
    n_grid = len(fade_level)
    atr_slice = atr_vals[s:e]
    close_slice = close[s:e]
    high_slice = high[s:e]
    low_slice = low[s:e]
    ts_slice = ts[s:e]
    p_slice = piv_p[s:e]
    r1_slice = piv_r1[s:e]
    r2_slice = piv_r2[s:e]
    s1_slice = piv_s1[s:e]
    s2_slice = piv_s2[s:e]
    for g in prange(n_grid):
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            close_slice,
            high_slice,
            low_slice,
            ts_slice,
            p_slice,
            r1_slice,
            r2_slice,
            s1_slice,
            s2_slice,
            atr_slice,
            int(fade_level[g]),
            touch_atr_thresh[g],
            int(target_mode[g]),
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
