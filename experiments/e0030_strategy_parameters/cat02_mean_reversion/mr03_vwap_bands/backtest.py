"""Backtest engine for mr03_vwap_bands.

Strategy: fade price when it closes beyond an N-sigma VWAP deviation band,
targeting VWAP itself (``exit_sigma=0``) or a tighter M-sigma band on the
same side, closer to VWAP (``exit_sigma>0``). Stop is placed
``atr_stop_mult * ATR(14)`` beyond the *entry band level* (not the entry
price) -- this follows the strategy doc's "price extends 0.5x ATR beyond
entry band" stop rule, which anchors the stop to the band rather than to the
fill price.
"""

from __future__ import annotations

import numpy as np
from numba import njit, prange

from algo_shared.metrics import compute_metrics

SPREAD = 0.00008
# 1-min timeframe over 23 years of EURUSD can generate very high trade counts
# for tight entry_sigma settings; measured worst case (entry_sigma=1.0,
# 1-min) reached ~577k trades, so this is sized with generous headroom
# above the mr01 default to avoid a buffer overflow in `trades`.
MAX_TRADES = 1_000_000

# Minimum stop distance (price units) required to take a trade. Unlike mr01
# (where stop distance is directly atr_stop_mult * ATR, always well away
# from zero when ATR > 0), mr03's stop is anchored to the *entry band*
# (band_level +/- atr_stop_mult * ATR) rather than to the entry price, so
# the distance from fill price to stop is a difference of two independent
# quantities that can nearly cancel out. Without a floor, near-zero
# denominators would blow up the R-multiple of an otherwise unremarkable
# trade. 1e-5 (~0.1 pip) is comfortably below any realistic ATR-based stop
# while still ruling out degenerate near-zero risk.
MIN_STOP_DIST = 1e-5

# Forced-exit safety net: VWAP-band deviations should mean-revert within a
# session; 500 bars (well beyond any single session at 1-15 min bars) bounds
# worst-case holding time without materially affecting normal trades. Not a
# grid dimension -- documented here and in README.
MAX_HOLD_BARS = 500


@njit(cache=True)
def backtest_core(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ts: np.ndarray,
    vwap_vals: np.ndarray,
    std_vals: np.ndarray,
    atr_vals: np.ndarray,
    entry_sigma: float,
    exit_sigma: float,
    atr_stop_mult: float,
    warm_bars: int,
) -> tuple[float, float, float, float, int]:
    """Run VWAP-band mean-reversion backtest on aligned slices."""
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
        v = vwap_vals[i]
        sd = std_vals[i]
        a = atr_vals[i]
        if np.isnan(v) or np.isnan(sd) or sd < 1e-12 or np.isnan(a):
            continue

        upper_entry = v + entry_sigma * sd
        lower_entry = v - entry_sigma * sd

        if in_pos:
            bars_held += 1
            exit_r = np.nan
            if is_long:
                target = v - exit_sigma * sd if exit_sigma > 0.0 else v
                if low[i] <= stop:
                    exit_r = (stop - entry_price - SPREAD) / risk_r
                elif close[i] >= target:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
                elif bars_held >= MAX_HOLD_BARS:
                    exit_r = (close[i] - entry_price - SPREAD) / risk_r
            else:
                target = v + exit_sigma * sd if exit_sigma > 0.0 else v
                if high[i] >= stop:
                    exit_r = (entry_price - stop - SPREAD) / risk_r
                elif close[i] <= target:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
                elif bars_held >= MAX_HOLD_BARS:
                    exit_r = (entry_price - close[i] - SPREAD) / risk_r
            if not np.isnan(exit_r):
                trades[n_trades] = exit_r
                n_trades += 1
                in_pos = False
            continue

        bull_sig = close[i] < lower_entry
        bear_sig = close[i] > upper_entry

        if bull_sig:
            ep = close[i]
            stop_candidate = lower_entry - atr_stop_mult * a
            dist = ep - stop_candidate
            if dist > MIN_STOP_DIST:
                entry_price = ep
                stop = stop_candidate
                risk_r = dist
                is_long = True
                in_pos = True
                bars_held = 0
        elif bear_sig:
            ep = close[i]
            stop_candidate = upper_entry + atr_stop_mult * a
            dist = stop_candidate - ep
            if dist > MIN_STOP_DIST:
                entry_price = ep
                stop = stop_candidate
                risk_r = dist
                is_long = False
                in_pos = True
                bars_held = 0

    if in_pos and risk_r > MIN_STOP_DIST:
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
    vwap_matrix: np.ndarray,
    std_matrix: np.ndarray,
    atr_vals: np.ndarray,
    mode_rows: np.ndarray,
    entry_sigma: np.ndarray,
    exit_sigma: np.ndarray,
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
    """Parallel grid search over ``[s, e)`` using precomputed VWAP caches."""
    n_grid = len(mode_rows)
    atr_slice = atr_vals[s:e]
    close_slice = close[s:e]
    high_slice = high[s:e]
    low_slice = low[s:e]
    ts_slice = ts[s:e]
    for g in prange(n_grid):
        row = mode_rows[g]
        sharpe, pf, mdd, ret, ntrades = backtest_core(
            close_slice,
            high_slice,
            low_slice,
            ts_slice,
            vwap_matrix[row, s:e],
            std_matrix[row, s:e],
            atr_slice,
            entry_sigma[g],
            exit_sigma[g],
            atr_stop_mult[g],
            int(warm_bars[g]),
        )
        out_sharpe[g] = sharpe
        out_pf[g] = pf
        out_mdd[g] = mdd
        out_ret[g] = ret
        out_ntrades[g] = ntrades
