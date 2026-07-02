"""Backtest engine for mr19_connors_rsi.

Strategy: fade Connors RSI (CRSI) extremes. CRSI = (RSI + UD_RSI +
ROC_percentile) / 3, combined on the fly from three independently-cached
component arrays. Long when CRSI crosses below ``oversold_thresh`` (subject
to an optional trend filter); short when it crosses above
``overbought_thresh``. Exit when CRSI crosses back through ``exit_level``
(longs) or ``100 - exit_level`` (shorts). The stop is a FIXED 1.5x ATR
multiple -- not part of the grid, since the strategy's own search space table
omits an ``atr_stop_mult`` dimension.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics
from indicators import ATR_FLOOR

SPREAD = 0.00008
MAX_TRADES = 200_000

# Fixed (not grid-searched): the MR-19 parameter table in the strategy
# research doc omits an ATR-stop dimension, unlike every other MR strategy.
FIXED_ATR_STOP_MULT = 1.5

# No max_hold_bars dimension in the MR-19 grid either. A generous fixed
# forced-exit safety net avoids indefinitely-held positions.
FORCED_EXIT_BARS = 50

NO_TREND_FILTER = -1


@njit(cache=True)
def backtest_core(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ts: np.ndarray,
    rsi_vals: np.ndarray,
    ud_rsi_vals: np.ndarray,
    roc_rank_vals: np.ndarray,
    atr_vals: np.ndarray,
    sma_vals: np.ndarray,
    has_trend_filter: bool,
    oversold_thresh: float,
    overbought_thresh: float,
    exit_level: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run Connors RSI mean-reversion backtest on aligned slices."""
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

    short_exit_level = 100.0 - exit_level
    warm = warm_bars + 1

    for i in range(warm, n):
        r = rsi_vals[i]
        u = ud_rsi_vals[i]
        p = roc_rank_vals[i]
        a = atr_vals[i]
        if np.isnan(r) or np.isnan(u) or np.isnan(p) or np.isnan(a) or a < ATR_FLOOR:
            continue
        r_prev = rsi_vals[i - 1]
        u_prev = ud_rsi_vals[i - 1]
        p_prev = roc_rank_vals[i - 1]
        if np.isnan(r_prev) or np.isnan(u_prev) or np.isnan(p_prev):
            continue

        crsi = (r + u + p) / 3.0
        crsi_prev = (r_prev + u_prev + p_prev) / 3.0

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif crsi_prev < exit_level <= crsi:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif crsi_prev > short_exit_level >= crsi:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= FORCED_EXIT_BARS:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        bull_sig = crsi_prev >= oversold_thresh and crsi < oversold_thresh
        bear_sig = crsi_prev <= overbought_thresh and crsi > overbought_thresh

        if has_trend_filter:
            s = sma_vals[i]
            if np.isnan(s):
                continue
            if bull_sig and close[i] <= s:
                bull_sig = False
            if bear_sig and close[i] >= s:
                bear_sig = False

        dist = FIXED_ATR_STOP_MULT * a
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
            rr = (close[last] - entry_price - SPREAD) / risk_r
        else:
            rr = (entry_price - close[last] - SPREAD) / risk_r
        trades[n_trades] = rr
        n_trades += 1

    return compute_metrics(trades, n_trades, ts[0], ts[n - 1])


@njit(parallel=True, cache=True)
def search_range(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ts: np.ndarray,
    rsi_matrix: np.ndarray,
    ud_rsi_matrix: np.ndarray,
    roc_rank_matrix: np.ndarray,
    sma_matrix: np.ndarray,
    atr_vals: np.ndarray,
    rsi_rows: np.ndarray,
    ud_rsi_rows: np.ndarray,
    roc_rank_rows: np.ndarray,
    sma_rows: np.ndarray,
    oversold_thresh: np.ndarray,
    overbought_thresh: np.ndarray,
    exit_level: np.ndarray,
    warm_bars: np.ndarray,
    s: int,
    e: int,
    out_sharpe: np.ndarray,
    out_pf: np.ndarray,
    out_mdd: np.ndarray,
    out_ret: np.ndarray,
    out_ntrades: np.ndarray,
) -> None:
    """Parallel grid search over ``[s, e)`` using precomputed component caches."""
    n_grid = len(rsi_rows)
    atr_slice = atr_vals[s:e]
    close_slice = close[s:e]
    high_slice = high[s:e]
    low_slice = low[s:e]
    ts_slice = ts[s:e]
    dummy_sma = np.zeros(e - s, dtype=np.float64)
    for g in prange(n_grid):
        sma_row = sma_rows[g]
        has_filter = sma_row != NO_TREND_FILTER
        sma_slice = sma_matrix[sma_row, s:e] if has_filter else dummy_sma
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            close_slice,
            high_slice,
            low_slice,
            ts_slice,
            rsi_matrix[rsi_rows[g], s:e],
            ud_rsi_matrix[ud_rsi_rows[g], s:e],
            roc_rank_matrix[roc_rank_rows[g], s:e],
            atr_slice,
            sma_slice,
            has_filter,
            oversold_thresh[g],
            overbought_thresh[g],
            exit_level[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
