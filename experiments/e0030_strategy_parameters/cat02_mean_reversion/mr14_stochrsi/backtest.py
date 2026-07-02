"""Backtest engine for mr14_stochrsi.

Strategy: fade StochRSI extremes. Long when the smoothed %K line crosses
below ``oversold_thresh``; short when it crosses above ``overbought_thresh``.
Exit when %K crosses back through the 0.5 midline, on a forced-exit safety
net, or on an ATR stop.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics
from indicators import FORCED_EXIT_BARS

SPREAD = 0.00008
MAX_TRADES = 200_000
MIDLINE = 0.5


@njit(cache=True)
def backtest_core(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ts: np.ndarray,
    k_vals: np.ndarray,
    atr_vals: np.ndarray,
    oversold_thresh: float,
    overbought_thresh: float,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run StochRSI mean-reversion backtest on aligned slices."""
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
        k_prev = k_vals[i - 1]
        a = atr_vals[i]
        # Wilder ATR can decay to near machine-epsilon during extended
        # flat-price stretches (weekend/holiday gaps in the resampled
        # bars). StochRSI is scale-invariant, so it can still register
        # spurious extreme readings from sub-pip noise during such a
        # stretch, triggering an entry with an economically meaningless
        # near-zero-risk stop. Gate on a realistic floor (EURUSD ATR is
        # never legitimately below ~1e-6) rather than only checking NaN.
        if np.isnan(k) or np.isnan(k_prev) or np.isnan(a) or a < 1e-6:
            continue

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif k_prev < MIDLINE <= k:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif k_prev > MIDLINE >= k:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        bull_sig = k_prev >= oversold_thresh and k < oversold_thresh
        bear_sig = k_prev <= overbought_thresh and k > overbought_thresh

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
    k_matrix: np.ndarray,
    atr_vals: np.ndarray,
    combo_rows: np.ndarray,
    oversold_thresh: np.ndarray,
    overbought_thresh: np.ndarray,
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
    """Parallel grid search over ``[s, e)`` using precomputed StochRSI %K cache."""
    n_grid = len(combo_rows)
    atr_slice = atr_vals[s:e]
    close_slice = close[s:e]
    high_slice = high[s:e]
    low_slice = low[s:e]
    ts_slice = ts[s:e]
    for g in prange(n_grid):
        row = combo_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            close_slice,
            high_slice,
            low_slice,
            ts_slice,
            k_matrix[row, s:e],
            atr_slice,
            oversold_thresh[g],
            overbought_thresh[g],
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
