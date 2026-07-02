"""Backtest engine for mr20_tema_distance.

Strategy: fade price when its distance from TEMA, measured in ATR units,
exceeds ``distance_thresh``. Distance > +thresh -> short (price too far above
TEMA); distance < -thresh -> long (price too far below TEMA). Exit target:
either the (dynamically updated) TEMA itself, or a static level set at entry
-- half the ATR-distance observed at entry, toward TEMA. A fixed forced-exit
safety net (``MAX_HOLD_BARS``) protects against indefinitely stuck positions
since ``max_hold_bars`` is not part of the grid search space.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
MAX_HOLD_BARS = 100  # fixed forced-exit safety net (not grid-searched)

EXIT_TEMA_TOUCH = 0
EXIT_HALF_DISTANCE = 1


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    tema_vals: np.ndarray,
    atr_vals: np.ndarray,
    distance_thresh: float,
    exit_type: int,
    atr_stop_mult: float,
    max_hold_bars: int,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run TEMA Distance Reversion backtest; returns metrics tuple."""
    n = len(close)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0

    trades = np.empty(MAX_TRADES, dtype=np.float64)
    n_trades = 0

    in_pos = False
    is_long = False
    entry_price = 0.0
    stop = 0.0
    target_static = 0.0
    risk_r = 0.0
    bars_held = 0

    warm = warm_bars + 1

    for i in range(warm, n):
        tv = tema_vals[i]
        a = atr_vals[i]
        # Wilder ATR can decay to near machine-epsilon (not exactly zero)
        # during extended flat-price stretches (weekend/holiday gaps in the
        # resampled bars). Since ``distance = (close - tema) / a`` divides by
        # ATR, a near-zero-but-nonzero reading would trivially trip the
        # entry threshold and produce an economically meaningless
        # near-zero-risk stop distance. Gate on a realistic floor (EURUSD
        # ATR is never legitimately below ~1e-6) rather than 1e-12.
        if np.isnan(tv) or np.isnan(a) or a < 1e-6:
            continue

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            target = tv if exit_type == EXIT_TEMA_TOUCH else target_static
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif close[i] >= target:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif close[i] <= target:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        dist = (close[i] - tv) / a

        bull_sig = dist < -distance_thresh
        bear_sig = dist > distance_thresh

        stop_dist = a * atr_stop_mult
        if bull_sig and stop_dist > 1e-10:
            entry_price = close[i]
            stop = entry_price - stop_dist
            risk_r = stop_dist
            is_long = True
            in_pos = True
            bars_held = 0
            half_dist_price = abs(tv - entry_price) * 0.5
            target_static = entry_price + half_dist_price
        elif bear_sig and stop_dist > 1e-10:
            entry_price = close[i]
            stop = entry_price + stop_dist
            risk_r = stop_dist
            is_long = False
            in_pos = True
            bars_held = 0
            half_dist_price = abs(tv - entry_price) * 0.5
            target_static = entry_price - half_dist_price

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
    tema_matrix: np.ndarray,
    atr_matrix: np.ndarray,
    tema_rows: np.ndarray,
    atr_rows: np.ndarray,
    distance_thresh: np.ndarray,
    exit_type: np.ndarray,
    atr_stop_mult: np.ndarray,
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
    n_grid = len(tema_rows)
    for g in prange(n_grid):
        t_row = tema_rows[g]
        a_row = atr_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            tema_matrix[t_row, s:e],
            atr_matrix[a_row, s:e],
            distance_thresh[g],
            int(exit_type[g]),
            atr_stop_mult[g],
            int(max_hold_bars[g]),
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
