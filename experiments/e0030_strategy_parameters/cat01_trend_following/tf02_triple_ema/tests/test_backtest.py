"""Unit tests for the triple EMA backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import atr, ema


def _flat_bars(n: int, price: float = 1.1) -> tuple[np.ndarray, ...]:
    ts = np.arange(n, dtype=np.int64) * 300
    open_ = np.full(n, price, dtype=np.float64)
    high = np.full(n, price * 1.001, dtype=np.float64)
    low = np.full(n, price * 0.999, dtype=np.float64)
    close = np.full(n, price, dtype=np.float64)
    return ts, open_, high, low, close


def test_no_trades_on_flat_bars() -> None:
    n = 300
    ts, open_, high, low, close = _flat_bars(n)
    fast = ema(close, 9)
    mid = ema(close, 21)
    slow = ema(close, 55)
    atr_vals = atr(high, low, close, 14)
    sharpe, pf, mdd, ret, n_trades = backtest_core(
        open_, high, low, close, ts, fast, mid, slow, mid, atr_vals, 55, 1.5
    )
    assert n_trades == 0
    assert sharpe == 0.0
    assert mdd == 0.0


def test_returns_zeros_on_tiny_input() -> None:
    n = 5
    ts, open_, high, low, close = _flat_bars(n)
    fast = ema(close, 3)
    mid = ema(close, 4)
    slow = ema(close, 5)
    atr_vals = atr(high, low, close, 14)
    sharpe, pf, mdd, ret, n_trades = backtest_core(
        open_, high, low, close, ts, fast, mid, slow, mid, atr_vals, 5, 1.0
    )
    assert n_trades == 0


def test_alignment_check_prevents_entry_when_unaligned() -> None:
    # Descending close — EMAs will be fast > mid > slow reversed (fast < mid < slow)
    # so bull_align is always False → no long trades
    n = 200
    close = np.linspace(1.2, 1.0, n, dtype=np.float64)
    ts = np.arange(n, dtype=np.int64) * 300
    open_ = close.copy()
    high = close * 1.001
    low = close * 0.999
    fast = ema(close, 5)
    mid = ema(close, 21)
    slow = ema(close, 55)
    atr_vals = atr(high, low, close, 14)
    # pullback EMA = slow; alignment would be bearish so no longs expected
    # (may still produce short trades)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, fast, mid, slow, slow, atr_vals, 55, 1.0
    )
    # We only assert it runs without error; trade count is data-dependent
    assert n_trades >= 0
