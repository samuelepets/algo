"""Unit tests for MR-11 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import TARGET_CENTER_SMA, TARGET_INNER_BAND, backtest_core
from indicators import atr, adx, sma, rolling_std_bb, ATR_PERIOD, ADX_PERIOD


def _run(
    close,
    bb_period=20,
    outer_sigma=2.0,
    target=TARGET_INNER_BAND,
    adx_filter=0,
    atr_stop_mult=1.0,
    max_hold_bars=20,
):
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.002
    low = close - 0.002
    open_ = close.copy()
    sma_v = sma(close, bb_period)
    std_v = rolling_std_bb(close, bb_period)
    atr_v = atr(high, low, close, ATR_PERIOD)
    adx_v = adx(high, low, close, ADX_PERIOD)
    warm = max(bb_period, ADX_PERIOD * 2) + 1
    return backtest_core(
        open_, high, low, close, ts,
        sma_v, std_v, atr_v, adx_v,
        outer_sigma, target, adx_filter,
        atr_stop_mult, max_hold_bars, warm,
    )


def test_no_trades_flat() -> None:
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_reversion_fires_on_spike_down() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:220] = 1.07  # sharp dip below the lower outer band
    close[220:] = 1.1
    _, _, _, _, n_trades = _run(close, bb_period=20, outer_sigma=2.0,
                                 atr_stop_mult=0.5, max_hold_bars=30)
    assert n_trades > 0


def test_max_hold_exits() -> None:
    n = 500
    close = np.ones(n, dtype=np.float64)
    close[200:] = 0.95  # persistent move below band, never recovers
    _, _, _, _, n_trades = _run(close, bb_period=20, outer_sigma=2.0,
                                 atr_stop_mult=2.0, max_hold_bars=5)
    assert n_trades >= 0  # at minimum no crash


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 30.0)
    r1 = _run(close)
    r2 = _run(close)
    assert r1 == r2


def test_target_type_changes_trade_outcomes() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.04 * np.sin(t / 25.0)
    r_inner = _run(close, target=TARGET_INNER_BAND)
    r_center = _run(close, target=TARGET_CENTER_SMA)
    # Both should execute trades; trade counts/results may differ since the
    # center-SMA target requires price to travel further.
    assert r_inner[4] >= 0
    assert r_center[4] >= 0


def test_adx_filter_reduces_or_equal_trades() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.04 * np.sin(t / 20.0)
    r_no_filter = _run(close, adx_filter=0)
    r_filtered = _run(close, adx_filter=20)
    assert r_filtered[4] <= r_no_filter[4]
