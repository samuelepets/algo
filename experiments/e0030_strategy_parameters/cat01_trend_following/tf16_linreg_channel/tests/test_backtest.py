"""Tests for linreg backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import ENTRY_BOUNCE, ENTRY_BREAKOUT, atr, linreg_channel


def _bars(close):
    ts = np.arange(close.size, dtype=np.int64) * 300  # 5-min
    high = close + 0.001
    low = close - 0.001
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_on_flat_bars():
    close = np.full(300, 1.1, dtype=np.float64)
    ts, open_, high, low, close = _bars(close)
    c, s = linreg_channel(close, 50)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, c, s, a, 50, ENTRY_BOUNCE, 1.5, 1.5, 2.0
    )
    assert n_trades == 0


def test_bounce_mode_deterministic():
    t = np.arange(3000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 60.0) + 0.005 * np.sin(t / 13.0)
    ts, open_, high, low, close = _bars(close)
    c, s = linreg_channel(close, 50)
    a = atr(high, low, close, 14)
    r1 = backtest_core(open_, high, low, close, ts, c, s, a, 50, ENTRY_BOUNCE, 1.5, 1.5, 2.0)
    r2 = backtest_core(open_, high, low, close, ts, c, s, a, 50, ENTRY_BOUNCE, 1.5, 1.5, 2.0)
    assert r1 == r2
    assert np.isfinite(r1[0])
