"""Tests for Elder Impulse backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import ENTRY_FIRST, EXIT_NEUTRAL, atr, elder_impulse_colors, ema, macd_histogram


def _bars(close, step_secs=300):
    ts = np.arange(close.size, dtype=np.int64) * step_secs
    high = close + 0.002
    low = close - 0.002
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_flat():
    close = np.full(300, 1.1, dtype=np.float64)
    ts, open_, high, low, close = _bars(close)
    e_vals = ema(close, 13)
    h_vals = macd_histogram(close, 12, 26, 9)
    colors = elder_impulse_colors(e_vals, h_vals)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, colors, a, 35, ENTRY_FIRST, EXIT_NEUTRAL, 1.5
    )
    assert n_trades == 0


def test_impulse_deterministic():
    n = 3000
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.04 * np.sin(t / 70.0) + 0.008 * np.sin(t / 17.0)
    ts, open_, high, low, close = _bars(close)
    e_vals = ema(close, 13)
    h_vals = macd_histogram(close, 12, 26, 9)
    colors = elder_impulse_colors(e_vals, h_vals)
    a = atr(high, low, close, 14)
    r1 = backtest_core(open_, high, low, close, ts, colors, a, 35, ENTRY_FIRST, EXIT_NEUTRAL, 1.5)
    r2 = backtest_core(open_, high, low, close, ts, colors, a, 35, ENTRY_FIRST, EXIT_NEUTRAL, 1.5)
    assert r1 == r2
    assert np.isfinite(r1[0])
