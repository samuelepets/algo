"""Backtest engine for mr08_keltner_channel.

Strategy: fade price outside a Keltner Channel (EMA +/- k * ATR), targeting the
EMA center line. Two entry modes: close outside the band (``close_outside``),
or an intrabar wick touching/crossing the band even if the close does not
(``wick_touch``). Stop is checked before target within the same bar. A fixed
forced-exit safety net (``MAX_HOLD_BARS``) protects against indefinitely
stuck positions since ``max_hold_bars`` is not part of the grid search space.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
MAX_TRADES = 200_000
MAX_HOLD_BARS = 100  # fixed forced-exit safety net (not grid-searched)

ENTRY_CLOSE_OUTSIDE = 0  # enter when close crosses outside the band
ENTRY_WICK_TOUCH = 1      # enter when high/low touches or crosses the band


@njit(cache=True)
def backtest_core(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ts: np.ndarray,
    ema_vals: np.ndarray,
    atr_vals: np.ndarray,
    k_mult: float,
    entry_type: int,
    atr_stop_mult: float,
    max_hold_bars: int,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run Keltner Channel mean-reversion backtest; returns metrics tuple."""
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
        e = ema_vals[i]
        a = atr_vals[i]
        if np.isnan(e) or np.isnan(a):
            continue

        upper = e + k_mult * a
        lower = e - k_mult * a

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif close[i] >= e:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif close[i] <= e:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= max_hold_bars:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        bull_sig = False
        bear_sig = False
        if entry_type == ENTRY_CLOSE_OUTSIDE:
            bull_sig = close[i] < lower
            bear_sig = close[i] > upper
        else:  # ENTRY_WICK_TOUCH
            bull_sig = low[i] <= lower
            bear_sig = high[i] >= upper

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
    ema_matrix: np.ndarray,
    atr_matrix: np.ndarray,
    ema_rows: np.ndarray,
    atr_rows: np.ndarray,
    k_mult: np.ndarray,
    entry_type: np.ndarray,
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
    n_grid = len(ema_rows)
    for g in prange(n_grid):
        ema_row = ema_rows[g]
        atr_row = atr_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            open_[s:e],
            high[s:e],
            low[s:e],
            close[s:e],
            ts[s:e],
            ema_matrix[ema_row, s:e],
            atr_matrix[atr_row, s:e],
            k_mult[g],
            int(entry_type[g]),
            atr_stop_mult[g],
            int(max_hold_bars[g]),
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
