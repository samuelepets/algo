"""Backtest engine for mr05_stochastic_reversion.

Strategy: slow-stochastic %K/%D reversion. Enter long when %K was oversold on
the prior bar and crosses back above %D on this bar; enter short when %K was
overbought on the prior bar and crosses back below %D. Exit at a fixed ATR
stop, at the 50 midline (the reversion target — the doc does not specify an
exit rule beyond the entry trigger, so midline-cross-or-max-hold is this
implementation's choice, documented in README.md), or after a max holding
period.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
MIDLINE = 50.0


@njit(cache=True)
def backtest_core(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    k_vals: np.ndarray,
    d_vals: np.ndarray,
    atr_vals: np.ndarray,
    oversold_thresh: float,
    overbought_thresh: float,
    atr_stop_mult: float,
    max_hold_bars: int,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run stochastic reversion backtest on aligned slices; returns metrics tuple."""
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
        k = k_vals[i]
        d = d_vals[i]
        k_prev = k_vals[i - 1]
        d_prev = d_vals[i - 1]
        a = atr_vals[i]

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif k >= MIDLINE:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif k <= MIDLINE:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        if np.isnan(k) or np.isnan(d) or np.isnan(k_prev) or np.isnan(d_prev) or np.isnan(a):
            continue

        dist = a * atr_stop_mult
        if dist <= 1e-10:
            continue

        long_sig = k_prev < oversold_thresh and k_prev <= d_prev and k > d
        short_sig = k_prev > overbought_thresh and k_prev >= d_prev and k < d

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
            r = (close[last] - entry_price - SPREAD) / risk_r
        else:
            r = (entry_price - close[last] - SPREAD) / risk_r
        trades[n_trades] = r
        n_trades += 1

    return compute_metrics(trades, n_trades, ts[0], ts[n - 1])


@njit(parallel=True, cache=True)
def search_range(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    k_matrix: np.ndarray,
    d_matrix: np.ndarray,
    atr_vals: np.ndarray,
    combo_rows: np.ndarray,
    oversold_thresh: np.ndarray,
    overbought_thresh: np.ndarray,
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
    n_grid = len(combo_rows)
    high_slice = high[s:e]
    low_slice = low[s:e]
    close_slice = close[s:e]
    ts_slice = ts[s:e]
    atr_slice = atr_vals[s:e]
    for g in prange(n_grid):
        row = combo_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            high_slice,
            low_slice,
            close_slice,
            ts_slice,
            k_matrix[row, s:e],
            d_matrix[row, s:e],
            atr_slice,
            oversold_thresh[g],
            overbought_thresh[g],
            atr_stop_mult[g],
            int(max_hold_bars[g]),
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
