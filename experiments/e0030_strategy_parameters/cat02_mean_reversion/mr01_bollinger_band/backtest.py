"""Backtest engine for mr01_bollinger_band.

Strategy: fade the outer Bollinger Band, target the middle band (SMA).
Two entry modes — close outside the band, or first close back inside (reentry).
Optional ADX filter to restrict entries to non-trending regimes.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000

ENTRY_CLOSE_OUTSIDE = 0   # enter when close crosses outside the band
ENTRY_REENTRY = 1          # enter on first close back inside the band


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
    bb_mult: float,
    entry_type: int,
    adx_filter: int,
    atr_stop_mult: float,
    max_hold_bars: int,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run BB mean-reversion backtest on aligned slices; returns metrics tuple."""
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

        upper = s + bb_mult * std
        lower = s - bb_mult * std

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif close[i] >= s:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif close[i] <= s:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        # ADX filter: skip entry if ADX >= threshold
        if adx_filter > 0:
            adx_val = adx_vals[i]
            if np.isnan(adx_val) or adx_val >= adx_filter:
                continue

        bull_sig = False
        bear_sig = False
        if entry_type == ENTRY_CLOSE_OUTSIDE:
            bull_sig = close[i] < lower
            bear_sig = close[i] > upper
        else:  # ENTRY_REENTRY
            if not np.isnan(sma_vals[i - 1]) and not np.isnan(std_vals[i - 1]) and std_vals[i - 1] > 1e-12:
                prev_lower = sma_vals[i - 1] - bb_mult * std_vals[i - 1]
                prev_upper = sma_vals[i - 1] + bb_mult * std_vals[i - 1]
                bull_sig = close[i - 1] < prev_lower and close[i] >= lower
                bear_sig = close[i - 1] > prev_upper and close[i] <= upper

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


@njit(cache=True)
def backtest_core_with_trades(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    sma_vals: np.ndarray,
    std_vals: np.ndarray,
    atr_vals: np.ndarray,
    adx_vals: np.ndarray,
    bb_mult: float,
    entry_type: int,
    adx_filter: int,
    atr_stop_mult: float,
    max_hold_bars: int,
    warm_bars: int,
    out_entry_ts: np.ndarray,
    out_exit_ts: np.ndarray,
    out_entry_price: np.ndarray,
    out_exit_price: np.ndarray,
    out_is_long: np.ndarray,
) -> int:
    """Same signal/exit rules as ``backtest_core``, but records per-trade detail.

    Used for diagnostics/visualization (e.g. ``plot_demo.py``), not the grid
    search — kept as a separate kernel so the hot ``search_range`` path is
    untouched. ``out_*`` buffers must be pre-allocated to at least
    ``MAX_TRADES``. Returns the number of trades written.
    """
    n = len(close)
    if n < 2:
        return 0

    n_trades = 0

    in_pos = False
    is_long = False
    entry_price = 0.0
    entry_idx = 0
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

        upper = s + bb_mult * std
        lower = s - bb_mult * std

        if in_pos:
            bars_held += 1
            exit_price = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_price = stop
                elif close[i] >= s:
                    exit_price = close[i]
                elif bars_held >= max_hold_bars:
                    exit_price = close[i]
            else:
                if high[i] >= stop:
                    exit_price = stop
                elif close[i] <= s:
                    exit_price = close[i]
                elif bars_held >= max_hold_bars:
                    exit_price = close[i]
            if not np.isnan(exit_price):
                out_entry_ts[n_trades] = ts[entry_idx]
                out_exit_ts[n_trades] = ts[i]
                out_entry_price[n_trades] = entry_price
                out_exit_price[n_trades] = exit_price
                out_is_long[n_trades] = is_long
                n_trades += 1
                in_pos = False
            continue

        # ADX filter: skip entry if ADX >= threshold
        if adx_filter > 0:
            adx_val = adx_vals[i]
            if np.isnan(adx_val) or adx_val >= adx_filter:
                continue

        bull_sig = False
        bear_sig = False
        if entry_type == ENTRY_CLOSE_OUTSIDE:
            bull_sig = close[i] < lower
            bear_sig = close[i] > upper
        else:  # ENTRY_REENTRY
            if not np.isnan(sma_vals[i - 1]) and not np.isnan(std_vals[i - 1]) and std_vals[i - 1] > 1e-12:
                prev_lower = sma_vals[i - 1] - bb_mult * std_vals[i - 1]
                prev_upper = sma_vals[i - 1] + bb_mult * std_vals[i - 1]
                bull_sig = close[i - 1] < prev_lower and close[i] >= lower
                bear_sig = close[i - 1] > prev_upper and close[i] <= upper

        dist = a * atr_stop_mult
        if bull_sig and dist > 1e-10:
            entry_price = close[i]
            entry_idx = i
            stop = entry_price - dist
            risk_r = dist
            is_long = True
            in_pos = True
            bars_held = 0
        elif bear_sig and dist > 1e-10:
            entry_price = close[i]
            entry_idx = i
            stop = entry_price + dist
            risk_r = dist
            is_long = False
            in_pos = True
            bars_held = 0

    # Close open position at last bar
    if in_pos and risk_r > 1e-10:
        last = n - 1
        exit_price = close[last]
        out_entry_ts[n_trades] = ts[entry_idx]
        out_exit_ts[n_trades] = ts[last]
        out_entry_price[n_trades] = entry_price
        out_exit_price[n_trades] = exit_price
        out_is_long[n_trades] = is_long
        n_trades += 1

    return n_trades


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
    bb_mult: np.ndarray,
    entry_type: np.ndarray,
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
            bb_mult[g],
            int(entry_type[g]),
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
