"""Tests for N-bar breakout backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import atr, rolling_max, rolling_min, rolling_vol_avg, CONFIRM_CLOSE


def _bars(close, step_secs=300):
    ts = np.arange(close.size, dtype=np.int64) * step_secs
    high = close + 0.002
    low = close - 0.002
    open_ = close.copy()
    vol = np.ones(close.size, dtype=np.float64) * 10.0
    return ts, open_, high, low, close, vol


def test_no_trades_flat():
    close = np.full(200, 1.1, dtype=np.float64)
    ts, open_, high, low, close, vol = _bars(close)
    bh = rolling_max(high, 20); bl = rolling_min(low, 20)
    va = rolling_vol_avg(vol, 20); a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, vol, bh, bl, va, a, 20, CONFIRM_CLOSE, False, 1.5, 2.0
    )
    assert n_trades == 0


def test_breakout_deterministic():
    n = 3000
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.05 * np.sin(t / 80.0) + t * 0.00004
    ts, open_, high, low, close, vol = _bars(close)
    bh = rolling_max(high, 20); bl = rolling_min(low, 20)
    va = rolling_vol_avg(vol, 20); a = atr(high, low, close, 14)
    r1 = backtest_core(open_, high, low, close, ts, vol, bh, bl, va, a, 20, CONFIRM_CLOSE, False, 1.5, 2.0)
    r2 = backtest_core(open_, high, low, close, ts, vol, bh, bl, va, a, 20, CONFIRM_CLOSE, False, 1.5, 2.0)
    assert r1 == r2
    assert np.isfinite(r1[0])
