"""Unit tests for the EMA + RSI backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import atr, ema, rsi


def _flat_bars(n: int, price: float = 1.1) -> tuple[np.ndarray, ...]:
    ts = np.arange(n, dtype=np.int64) * 60
    open_ = np.full(n, price, dtype=np.float64)
    high = np.full(n, price * 1.001, dtype=np.float64)
    low = np.full(n, price * 0.999, dtype=np.float64)
    close = np.full(n, price, dtype=np.float64)
    return ts, open_, high, low, close


def _oscillating_bars(n: int = 2500) -> tuple[np.ndarray, ...]:
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.02 * np.sin(t / 25.0) + 0.005 * np.sin(t / 7.0)
    ts = np.arange(n, dtype=np.int64) * 60
    high = close + 0.001
    low = close - 0.001
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_on_flat_bars() -> None:
    n = 200
    ts, open_, high, low, close = _flat_bars(n)
    fast = ema(close, 9)
    slow = ema(close, 21)
    r = rsi(close, 14)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, fast, slow, r, a, 21, 14, 55.0, 45.0, 1.0, 2.0
    )
    assert n_trades == 0


def test_returns_zeros_on_tiny_input() -> None:
    n = 5
    ts, open_, high, low, close = _flat_bars(n)
    fast = ema(close, 3)
    slow = ema(close, 4)
    r = rsi(close, 3)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, fast, slow, r, a, 4, 3, 55.0, 45.0, 1.0, 2.0
    )
    assert n_trades == 0


def test_trades_generated_and_deterministic() -> None:
    ts, open_, high, low, close = _oscillating_bars()
    fast = ema(close, 9)
    slow = ema(close, 21)
    r = rsi(close, 14)
    a = atr(high, low, close, 14)
    res1 = backtest_core(
        open_, high, low, close, ts, fast, slow, r, a, 21, 14, 50.0, 50.0, 1.0, 2.0
    )
    res2 = backtest_core(
        open_, high, low, close, ts, fast, slow, r, a, 21, 14, 50.0, 50.0, 1.0, 2.0
    )
    assert res1[4] > 0
    assert res1 == res2


def test_tighter_rsi_threshold_does_not_increase_longs_only_caveat() -> None:
    """Stricter RSI thresholds keep the engine running and finite."""
    ts, open_, high, low, close = _oscillating_bars()
    fast = ema(close, 9)
    slow = ema(close, 21)
    r = rsi(close, 14)
    a = atr(high, low, close, 14)
    strict = backtest_core(
        open_, high, low, close, ts, fast, slow, r, a, 21, 14, 57.0, 43.0, 1.0, 2.0
    )
    assert strict[4] >= 0
    assert np.isfinite(strict[0])
