"""Unit tests for the MACD + 200 EMA backtest engine."""

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


def _oscillating_bars(n: int = 2500) -> tuple[np.ndarray, ...]:
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.02 * np.sin(t / 25.0) + 0.005 * np.sin(t / 7.0)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.001
    low = close - 0.001
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_on_flat_bars() -> None:
    n = 320
    ts, open_, high, low, close = _flat_bars(n)
    fast = ema(close, 12)
    slow = ema(close, 26)
    trend = ema(close, 200)
    atr_vals = atr(high, low, close, 14)
    sharpe, pf, mdd, ret, n_trades = backtest_core(
        open_, high, low, close, ts, fast, slow, trend, atr_vals, 26, 200, 9, 1.5, 2.0
    )
    assert n_trades == 0


def test_returns_zeros_on_tiny_input() -> None:
    n = 5
    ts, open_, high, low, close = _flat_bars(n)
    fast = ema(close, 3)
    slow = ema(close, 4)
    trend = ema(close, 5)
    atr_vals = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, fast, slow, trend, atr_vals, 4, 5, 3, 1.0, 2.0
    )
    assert n_trades == 0


def test_trades_generated_and_deterministic() -> None:
    """Realistic trend filter produces trades; identical inputs are deterministic."""
    ts, open_, high, low, close = _oscillating_bars()
    fast = ema(close, 8)
    slow = ema(close, 21)
    trend = ema(close, 50)
    atr_vals = atr(high, low, close, 14)
    a = backtest_core(
        open_, high, low, close, ts, fast, slow, trend, atr_vals, 21, 50, 9, 1.5, 2.0
    )
    b = backtest_core(
        open_, high, low, close, ts, fast, slow, trend, atr_vals, 21, 50, 9, 1.5, 2.0
    )
    assert a[4] > 0
    assert a == b
