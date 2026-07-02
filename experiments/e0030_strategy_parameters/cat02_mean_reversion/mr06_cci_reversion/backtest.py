"""Backtest engine for mr06_cci_reversion.

Strategy: fade extreme CCI readings (beyond ``+/- entry_threshold``), targeting
a return of CCI toward zero (``abs(CCI) <= exit_threshold``). Risk is sized off
an ATR stop rather than the CCI +/-300 adverse-extension stop suggested in the
strategy doc (ATR is a steadier, price-anchored risk unit — see README).
Optional ADX filter restricts entries to non-trending regimes. A fixed
100-bar forced-exit safety net bounds worst-case holding time (no
``max_hold_bars`` grid dimension for this strategy).
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
MAX_HOLD_SAFETY = 100  # fixed forced-exit safety net; not grid-searched


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    cci_vals: np.ndarray,
    atr_vals: np.ndarray,
    adx_vals: np.ndarray,
    entry_threshold: float,
    exit_threshold: float,
    adx_filter: int,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run CCI extreme-reversion backtest on aligned slices; returns metrics tuple."""
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
        c = cci_vals[i]

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif abs(c) <= exit_threshold:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= MAX_HOLD_SAFETY:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif abs(c) <= exit_threshold:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= MAX_HOLD_SAFETY:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        # Position sizing off ATR; skip entry if the stop distance is unusable
        # or the CCI reading is not yet available (warm-up / flat window).
        a = atr_vals[i]
        if np.isnan(a):
            continue
        dist = atr_stop_mult * a
        if np.isnan(c) or dist <= 1e-10:
            continue

        # ADX filter: skip entry if ADX >= threshold (applied before signals)
        if adx_filter > 0:
            adx_val = adx_vals[i]
            if np.isnan(adx_val) or adx_val >= adx_filter:
                continue

        long_sig = c < -entry_threshold
        short_sig = c > entry_threshold

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
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    cci_matrix: np.ndarray,
    atr_vals: np.ndarray,
    adx_vals: np.ndarray,
    period_rows: np.ndarray,
    entry_threshold: np.ndarray,
    exit_threshold: np.ndarray,
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
            cci_matrix[row, s:e],
            atr_slice,
            adx_slice,
            entry_threshold[g],
            exit_threshold[g],
            int(adx_filter[g]),
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
