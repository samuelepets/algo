"""Tests for ROC backtest engine."""
from __future__ import annotations
import numpy as np
from backtest import backtest_core
from indicators import atr, roc, ROC_FILTER_NONE


def _bars(close, step_secs=60):
    ts = np.arange(close.size, dtype=np.int64) * step_secs
    high = close + 0.001
    low = close - 0.001
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_flat():
    close = np.full(300, 1.1, dtype=np.float64)
    ts, open_, high, low, close = _bars(close)
    r = roc(close, 10)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, r, r, a, 10, 0.5, ROC_FILTER_NONE, 10
    )
    assert n_trades == 0


def test_roc_trades_deterministic():
    n = 3000
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 40.0) + t * 0.00003
    ts, open_, high, low, close = _bars(close)
    r = roc(close, 10)
    a = atr(high, low, close, 14)
    r1 = backtest_core(open_, high, low, close, ts, r, r, a, 10, 0.10, ROC_FILTER_NONE, 10)
    r2 = backtest_core(open_, high, low, close, ts, r, r, a, 10, 0.10, ROC_FILTER_NONE, 10)
    assert r1 == r2
    assert np.isfinite(r1[0])
