"""Unit tests for MR-05 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import SPREAD, backtest_core
from indicators import ATR_PERIOD, atr, sma, stoch_raw_k


def _run(
    high,
    low,
    close,
    k_period=5,
    d_period=3,
    slowing=3,
    oversold_thresh=20.0,
    overbought_thresh=80.0,
    atr_stop_mult=1.0,
    max_hold_bars=20,
):
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    raw_k = stoch_raw_k(high, low, close, k_period)
    smoothed_k = sma(raw_k, slowing)
    d = sma(smoothed_k, d_period)
    atr_v = atr(high, low, close, ATR_PERIOD)
    warm = k_period + slowing + d_period + 2
    return backtest_core(
        high, low, close, ts,
        smoothed_k, d, atr_v,
        oversold_thresh, overbought_thresh,
        atr_stop_mult, max_hold_bars, warm,
    )


def test_no_trades_flat() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    high = close.copy()
    low = close.copy()
    _, _, _, _, n_trades = _run(high, low, close)
    assert n_trades == 0


def test_reversion_fires_on_dip_and_recovery() -> None:
    # Build a V-shaped dip then a sharp recovery: the dip pushes %K near 0
    # (oversold), and the sharp bounce makes %K cross back above %D shortly
    # after, which is exactly the long-entry trigger.
    n = 300
    close = np.full(n, 1.1000, dtype=np.float64)
    dip_start = 150
    dip_len = 6
    rec_len = 6
    close[dip_start:dip_start + dip_len] = np.linspace(1.1000, 1.0700, dip_len)
    close[dip_start + dip_len:dip_start + dip_len + rec_len] = np.linspace(
        1.0700, 1.1050, rec_len
    )
    close[dip_start + dip_len + rec_len:] = 1.1050
    high = close + 0.0005
    low = close - 0.0005

    _, _, _, _, n_trades = _run(
        high, low, close,
        k_period=5, d_period=3, slowing=3,
        oversold_thresh=30.0, overbought_thresh=70.0,
        atr_stop_mult=1.5, max_hold_bars=50,
    )
    assert n_trades > 0


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 30.0)
    high = close + 0.0005
    low = close - 0.0005
    r1 = _run(high, low, close)
    r2 = _run(high, low, close)
    assert r1 == r2


def test_max_hold_forces_exit() -> None:
    # Hand-craft k/d/atr arrays directly so the only possible exit path is
    # the max-hold forced exit: price never moves (stop is unreachable) and
    # %K is held below the 50 midline for the whole trade. Two identical
    # entry/hold/forced-exit cycles are crafted (compute_metrics returns
    # zeroed aggregates for a single trade, so we need >= 2 to check
    # total_return).
    n = 25
    close = np.full(n, 1.1000, dtype=np.float64)
    high = np.full(n, 1.1005, dtype=np.float64)
    low = np.full(n, 1.0995, dtype=np.float64)
    ts = np.arange(n, dtype=np.int64) * 300

    k_vals = np.full(n, 30.0, dtype=np.float64)
    d_vals = np.full(n, 25.0, dtype=np.float64)
    atr_vals = np.full(n, 0.01, dtype=np.float64)

    oversold_thresh = 20.0
    overbought_thresh = 75.0

    # Crossing at entry bar 4: prior bar oversold and K<=D, this bar K>D.
    k_vals[3] = 10.0
    d_vals[3] = 15.0
    k_vals[4] = 25.0
    d_vals[4] = 20.0

    # A second, identical crossing at entry bar 14.
    k_vals[13] = 10.0
    d_vals[13] = 15.0
    k_vals[14] = 25.0
    d_vals[14] = 20.0

    max_hold_bars = 5
    atr_stop_mult = 1.0
    # warm_bars=3 -> loop starts at i = warm_bars + 1 = 4.
    sharpe, pf, mdd, total_return, n_trades = backtest_core(
        high, low, close, ts,
        k_vals, d_vals, atr_vals,
        oversold_thresh, overbought_thresh,
        atr_stop_mult, max_hold_bars, warm_bars=3,
    )

    assert n_trades == 2
    entry_price = close[4]
    exit_price = close[4 + max_hold_bars]  # forced exit at i = 9 (and i = 19)
    risk_r = atr_vals[4] * atr_stop_mult
    expected_r = (exit_price - entry_price - SPREAD) / risk_r
    assert abs(total_return - 2 * expected_r) < 1e-9


def test_short_entry_and_stop_exit() -> None:
    # Hand-craft two short entries that are each stopped out on the bar right
    # after entry (compute_metrics zeroes aggregates for a single trade, so
    # two identical cycles are crafted to check total_return).
    n = 20
    close = np.full(n, 1.1000, dtype=np.float64)
    high = np.full(n, 1.1005, dtype=np.float64)
    low = np.full(n, 1.0995, dtype=np.float64)
    ts = np.arange(n, dtype=np.int64) * 300

    k_vals = np.full(n, 40.0, dtype=np.float64)
    d_vals = np.full(n, 45.0, dtype=np.float64)
    atr_vals = np.full(n, 0.001, dtype=np.float64)

    oversold_thresh = 20.0
    overbought_thresh = 75.0

    # Short trigger at index 4: prior bar overbought and K>=D, this bar K<D.
    k_vals[3] = 90.0
    d_vals[3] = 85.0
    k_vals[4] = 60.0
    d_vals[4] = 65.0
    high[5] = 1.2000  # force the stop to be hit on the very next bar

    # A second, identical short trigger at index 10.
    k_vals[9] = 90.0
    d_vals[9] = 85.0
    k_vals[10] = 60.0
    d_vals[10] = 65.0
    high[11] = 1.2000

    sharpe, pf, mdd, total_return, n_trades = backtest_core(
        high, low, close, ts,
        k_vals, d_vals, atr_vals,
        oversold_thresh, overbought_thresh,
        atr_stop_mult=1.0, max_hold_bars=20, warm_bars=3,
    )

    assert n_trades == 2
    entry_price = close[4]
    dist = atr_vals[4] * 1.0
    stop = entry_price + dist
    expected_r = (entry_price - stop - SPREAD) / dist
    assert abs(total_return - 2 * expected_r) < 1e-9
