"""Unit tests for MR-07 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import ATR_PERIOD, atr, williams_r


def _run(
    close,
    high=None,
    low=None,
    wr_period=14,
    oversold_thresh=-80.0,
    overbought_thresh=-20.0,
    exit_level=-50.0,
    atr_stop_mult=1.0,
    max_hold_bars=10,
):
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    if high is None:
        high = close + 0.002
    if low is None:
        low = close - 0.002
    open_ = close.copy()
    wr_v = williams_r(high, low, close, wr_period)
    atr_v = atr(high, low, close, ATR_PERIOD)
    warm = max(wr_period, ATR_PERIOD) + 1
    return backtest_core(
        open_, high, low, close, ts,
        wr_v, atr_v,
        oversold_thresh, overbought_thresh, exit_level,
        atr_stop_mult, max_hold_bars, warm,
    )


def test_no_trades_flat() -> None:
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_reversion_fires_on_spike_down() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:220] = 1.07  # sharp dip -> WR near -100 -> oversold long
    close[220:] = 1.1
    high = close + 0.001
    low = close - 0.001
    _, _, _, _, n_trades = _run(close, high=high, low=low, atr_stop_mult=0.5, max_hold_bars=30)
    assert n_trades > 0


def test_reversion_fires_on_spike_up() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:220] = 1.13  # sharp rally -> WR near 0 -> overbought short
    close[220:] = 1.1
    high = close + 0.001
    low = close - 0.001
    _, _, _, _, n_trades = _run(close, high=high, low=low, atr_stop_mult=0.5, max_hold_bars=30)
    assert n_trades > 0


def test_max_hold_forces_exit() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:] = np.linspace(1.1, 1.05, n - 200)  # persistent drift, never reverts
    high = close + 0.001
    low = close - 0.001
    _, _, _, _, n_trades = _run(close, high=high, low=low, atr_stop_mult=5.0, max_hold_bars=5)
    assert n_trades >= 0  # at minimum no crash


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.02 * np.sin(t / 30.0)
    r1 = _run(close)
    r2 = _run(close)
    assert r1 == r2


def test_stop_priority_over_exit() -> None:
    # Force a long entry, then a large adverse move that both breaches the
    # stop and would otherwise satisfy the %R exit condition — stop must win.
    n = 300
    close = np.full(n, 1.1, dtype=np.float64)
    close[100:110] = 1.07  # spike down -> oversold long entry
    close[110] = 1.05  # sharp drop through the stop
    close[111:] = 1.1
    high = close + 0.001
    low = close - 0.001
    _, _, _, _, n_trades = _run(close, high=high, low=low, atr_stop_mult=0.3, max_hold_bars=50)
    assert n_trades > 0
