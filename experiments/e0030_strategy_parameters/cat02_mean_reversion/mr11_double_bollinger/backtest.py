"""Backtest engine for mr11_double_bollinger.

Strategy: fade price beyond the outer Bollinger Band (SMA +/- outer_sigma*std),
targeting either the inner band (SMA +/- 1.0*std, on the side toward the
center) or the center SMA itself, per the ``target`` grid dimension. Optional
ADX filter restricts entries to non-trending regimes. A fixed forced-exit
safety net (``MAX_HOLD_BARS``) protects against indefinitely stuck positions
since ``max_hold_bars`` is not part of the grid search space.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
MAX_HOLD_BARS = 50  # fixed forced-exit safety net (not grid-searched)

INNER_SIGMA = 1.0

TARGET_INNER_BAND = 0
TARGET_CENTER_SMA = 1


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    sma_vals: np.ndarray,
    std_vals: np.ndarray,
    atr_vals: np.ndarray,
    adx_vals: np.ndarray,
    outer_sigma: float,
    target_type: int,
    adx_filter: int,
    atr_stop_mult: float,
    max_hold_bars: int,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run Double Bollinger Band mean-reversion backtest; returns metrics tuple."""
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
        s = sma_vals[i]
        std = std_vals[i]
        a = atr_vals[i]
        if np.isnan(s) or np.isnan(std) or std < 1e-12 or np.isnan(a):
            continue

        upper_outer = s + outer_sigma * std
        lower_outer = s - outer_sigma * std
        upper_inner = s + INNER_SIGMA * std
        lower_inner = s - INNER_SIGMA * std

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            target = s if target_type == TARGET_CENTER_SMA else (
                lower_inner if is_long else upper_inner
            )
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

        if adx_filter > 0:
            adx_val = adx_vals[i]
            if np.isnan(adx_val) or adx_val >= adx_filter:
                continue

        bull_sig = close[i] < lower_outer
        bear_sig = close[i] > upper_outer

        dist = a * atr_stop_mult
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
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    sma_matrix: np.ndarray,
    std_matrix: np.ndarray,
    atr_vals: np.ndarray,
    adx_vals: np.ndarray,
    period_rows: np.ndarray,
    outer_sigma: np.ndarray,
    target_type: np.ndarray,
    adx_filter: np.ndarray,
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
    n_grid = len(period_rows)
    atr_slice = atr_vals[s:e]
    adx_slice = adx_vals[s:e]
    for g in prange(n_grid):
        row = period_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            sma_matrix[row, s:e],
            std_matrix[row, s:e],
            atr_slice,
            adx_slice,
            outer_sigma[g],
            int(target_type[g]),
            int(adx_filter[g]),
            atr_stop_mult[g],
            int(max_hold_bars[g]),
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
