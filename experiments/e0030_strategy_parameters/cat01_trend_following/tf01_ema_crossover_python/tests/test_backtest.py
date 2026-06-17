"""Unit tests for the backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import atr, ema


def _flat_bars(n: int, price: float = 1.1) -> tuple[np.ndarray, ...]:
    ts = np.arange(n, dtype=np.int64) * 300
    open_ = np.full(n, price)
    high = np.full(n, price * 1.001)
    low = np.full(n, price * 0.999)
    close = np.full(n, price)
    return ts, open_, high, low, close


def test_no_trades_on_flat_bars() -> None:
    n = 200
    ts, open_, high, low, close = _flat_bars(n)
    fast = ema(close, 9)
    slow = ema(close, 21)
    atr_vals = atr(high, low, close, 14)
    sharpe, pf, mdd, ret, n_trades = backtest_core(
        open_, high, low, close, ts, fast, slow, atr_vals, 21, 1.5, 2.0
    )
    assert n_trades == 0
    assert sharpe == 0.0
    assert pf == 0.0
    assert mdd == 0.0
    assert ret == 0.0
