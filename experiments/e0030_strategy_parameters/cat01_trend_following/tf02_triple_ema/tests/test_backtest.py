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


def test_long_entry_and_stop_exit_with_crafted_signals() -> None:
    """Deterministic one-trade path: pullback long then stop hit next bar."""
    n = 90
    ts = np.arange(n, dtype=np.int64) * 300
    open_ = np.full(n, 1.10, dtype=np.float64)
    high = np.full(n, 1.12, dtype=np.float64)
    low = np.full(n, 1.08, dtype=np.float64)
    close = np.full(n, 1.10, dtype=np.float64)

    fast = np.full(n, 1.05, dtype=np.float64)
    mid = np.full(n, 1.03, dtype=np.float64)
    slow = np.full(n, 1.01, dtype=np.float64)
    pb = mid.copy()
    atr_vals = np.full(n, 0.01, dtype=np.float64)

    i = 60
    fast[i - 1], fast[i] = 1.09, 1.10
    mid[i - 1], mid[i] = 1.07, 1.08
    slow[i - 1], slow[i] = 1.05, 1.06
    pb[i] = mid[i]
    low[i] = 1.075
    close[i] = 1.085
    high[i] = 1.09

    # Next bar triggers the static ATR stop (entry 1.085, stop 1.075).
    low[i + 1] = 1.07
    close[i + 1] = 1.08

    sharpe, pf, mdd, ret, n_trades = backtest_core(
        open_, high, low, close, ts, fast, mid, slow, pb, atr_vals, 55, 1.0
    )
    assert n_trades == 1
    # Metrics are zeroed when n_trades < 2 (see backtest._compute_metrics).
    assert sharpe == 0.0
    assert ret == 0.0


def test_no_long_trades_without_bullish_alignment() -> None:
    n = 120
    ts = np.arange(n, dtype=np.int64) * 300
    open_ = np.full(n, 1.10, dtype=np.float64)
    high = np.full(n, 1.11, dtype=np.float64)
    low = np.full(n, 1.09, dtype=np.float64)
    close = np.full(n, 1.10, dtype=np.float64)

    fast = np.linspace(1.12, 1.00, n, dtype=np.float64)
    mid = np.linspace(1.10, 0.98, n, dtype=np.float64)
    slow = np.linspace(1.08, 0.96, n, dtype=np.float64)
    atr_vals = np.full(n, 0.01, dtype=np.float64)

    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, fast, mid, slow, mid, atr_vals, 55, 1.0
    )
    assert n_trades == 0
