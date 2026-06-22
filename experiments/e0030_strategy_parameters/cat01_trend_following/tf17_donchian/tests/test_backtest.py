"""Tests for Donchian backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import atr, donchian_upper, donchian_lower


def _bars(close, step_secs=300):
    ts = np.arange(close.size, dtype=np.int64) * step_secs
    high = close + 0.002
    low = close - 0.002
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_flat():
    close = np.full(200, 1.1, dtype=np.float64)
    ts, open_, high, low, close = _bars(close)
    eu = donchian_upper(high, 20); el = donchian_lower(low, 20)
    xu = donchian_upper(high, 10); xl = donchian_lower(low, 10)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(open_, high, low, close, ts, eu, el, xu, xl, a, 20, 0.0, 2.0)
    assert n_trades == 0


def test_breakout_fires_on_trend():
    n = 3000
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.05 * np.sin(t / 100.0) + t * 0.00005
    ts, open_, high, low, close = _bars(close)
    eu = donchian_upper(high, 20); el = donchian_lower(low, 20)
    xu = donchian_upper(high, 10); xl = donchian_lower(low, 10)
    a = atr(high, low, close, 14)
    r1 = backtest_core(open_, high, low, close, ts, eu, el, xu, xl, a, 20, 0.0, 2.0)
    r2 = backtest_core(open_, high, low, close, ts, eu, el, xu, xl, a, 20, 0.0, 2.0)
    assert r1[4] >= 0
    assert r1 == r2
