"""Unit tests for the SuperTrend backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import atr


def _flat_bars(n: int, price: float = 1.1) -> tuple[np.ndarray, ...]:
    ts = np.arange(n, dtype=np.int64) * 300
    open_ = np.full(n, price, dtype=np.float64)
    high = np.full(n, price * 1.001, dtype=np.float64)
    low = np.full(n, price * 0.999, dtype=np.float64)
    close = np.full(n, price, dtype=np.float64)
    return ts, open_, high, low, close


def _oscillating_bars(n: int = 3000) -> tuple[np.ndarray, ...]:
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 35.0) + 0.006 * np.sin(t / 11.0)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_on_flat_bars() -> None:
    n = 200
    ts, open_, high, low, close = _flat_bars(n)
    a = atr(high, low, close, 10)
    dummy = np.zeros(n, dtype=np.int64)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, a, dummy, 0, 10, 3.0, 2.0
    )
    assert n_trades == 0


def test_returns_zeros_on_tiny_input() -> None:
    n = 6
    ts, open_, high, low, close = _flat_bars(n)
    a = atr(high, low, close, 3)
    dummy = np.zeros(n, dtype=np.int64)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, a, dummy, 0, 3, 3.0, 2.0
    )
    assert n_trades == 0


def test_trades_generated_and_deterministic() -> None:
    ts, open_, high, low, close = _oscillating_bars()
    a = atr(high, low, close, 10)
    dummy = np.zeros(close.size, dtype=np.int64)
    r1 = backtest_core(open_, high, low, close, ts, a, dummy, 0, 10, 2.0, 2.0)
    r2 = backtest_core(open_, high, low, close, ts, a, dummy, 0, 10, 2.0, 2.0)
    assert r1[4] > 0
    assert r1 == r2


def test_htf_filter_blocks_when_trend_is_neutral() -> None:
    """An htf trend array of all zeros blocks every entry when the filter is on."""
    ts, open_, high, low, close = _oscillating_bars()
    a = atr(high, low, close, 10)
    neutral = np.zeros(close.size, dtype=np.int64)  # never +1 or -1
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, a, neutral, 1, 10, 2.0, 2.0
    )
    assert n_trades == 0
