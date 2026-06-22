"""Unit tests for the MACD crossover backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import _macd_and_signal, backtest_core
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
    fast = ema(close, 12)
    slow = ema(close, 26)
    atr_vals = atr(high, low, close, 14)
    sharpe, pf, mdd, ret, n_trades = backtest_core(
        open_, high, low, close, ts, fast, slow, atr_vals, 26, 9, 0, 1.5, 2.0
    )
    assert n_trades == 0
    assert sharpe == 0.0
    assert mdd == 0.0


def test_returns_zeros_on_tiny_input() -> None:
    n = 5
    ts, open_, high, low, close = _flat_bars(n)
    fast = ema(close, 3)
    slow = ema(close, 4)
    atr_vals = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, fast, slow, atr_vals, 4, 3, 0, 1.0, 2.0
    )
    assert n_trades == 0


def test_macd_and_signal_constant_series() -> None:
    fast = np.full(60, 1.10, dtype=np.float64)
    slow = np.full(60, 1.08, dtype=np.float64)
    macd_line, signal_line = _macd_and_signal(fast, slow, 9)
    # Constant difference → MACD line constant, signal converges to it.
    assert abs(macd_line[-1] - 0.02) < 1e-12
    assert abs(signal_line[-1] - 0.02) < 1e-9


def _oscillating_bars(n: int = 2000) -> tuple[np.ndarray, ...]:
    """Sinusoidal close path that produces repeated MACD crossovers."""
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.02 * np.sin(t / 25.0) + 0.005 * np.sin(t / 7.0)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.001
    low = close - 0.001
    open_ = close.copy()
    return ts, open_, high, low, close


def test_trades_generated_on_oscillating_data() -> None:
    ts, open_, high, low, close = _oscillating_bars()
    fast = ema(close, 5)
    slow = ema(close, 12)
    atr_vals = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, fast, slow, atr_vals, 12, 9, 0, 1.5, 2.0
    )
    assert n_trades > 0


def test_zero_filter_runs_and_is_deterministic() -> None:
    ts, open_, high, low, close = _oscillating_bars()
    fast = ema(close, 5)
    slow = ema(close, 12)
    atr_vals = atr(high, low, close, 14)
    a = backtest_core(open_, high, low, close, ts, fast, slow, atr_vals, 12, 9, 1, 1.5, 2.0)
    b = backtest_core(open_, high, low, close, ts, fast, slow, atr_vals, 12, 9, 1, 1.5, 2.0)
    assert a[4] >= 0
    assert a == b  # deterministic for identical inputs
