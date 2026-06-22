"""Unit tests for the ADX + EMA backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import adx_dmi, atr, ema


def _flat_bars(n: int, price: float = 1.1) -> tuple[np.ndarray, ...]:
    ts = np.arange(n, dtype=np.int64) * 300
    open_ = np.full(n, price, dtype=np.float64)
    high = np.full(n, price * 1.001, dtype=np.float64)
    low = np.full(n, price * 0.999, dtype=np.float64)
    close = np.full(n, price, dtype=np.float64)
    return ts, open_, high, low, close


def _oscillating_bars(n: int = 3000) -> tuple[np.ndarray, ...]:
    t = np.arange(n, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 30.0) + 0.006 * np.sin(t / 9.0)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.001
    low = close - 0.001
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_on_flat_bars() -> None:
    n = 200
    ts, open_, high, low, close = _flat_bars(n)
    trend = ema(close, 50)
    adx, pdi, mdi = adx_dmi(high, low, close, 14)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, trend, adx, pdi, mdi, a, 14, 50, 20.0, 0, 1.5, 2.0
    )
    assert n_trades == 0


def test_returns_zeros_on_tiny_input() -> None:
    n = 8
    ts, open_, high, low, close = _flat_bars(n)
    trend = ema(close, 5)
    adx, pdi, mdi = adx_dmi(high, low, close, 3)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, trend, adx, pdi, mdi, a, 3, 5, 20.0, 0, 1.0, 2.0
    )
    assert n_trades == 0


def test_high_threshold_blocks_all_trades() -> None:
    ts, open_, high, low, close = _oscillating_bars()
    trend = ema(close, 50)
    adx, pdi, mdi = adx_dmi(high, low, close, 14)
    a = atr(high, low, close, 14)
    # ADX never exceeds 100; a threshold of 100 blocks every entry.
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, trend, adx, pdi, mdi, a, 14, 50, 100.0, 0, 1.5, 2.0
    )
    assert n_trades == 0


def test_trades_generated_and_deterministic() -> None:
    ts, open_, high, low, close = _oscillating_bars()
    trend = ema(close, 20)
    adx, pdi, mdi = adx_dmi(high, low, close, 14)
    a = atr(high, low, close, 14)
    r1 = backtest_core(
        open_, high, low, close, ts, trend, adx, pdi, mdi, a, 14, 20, 15.0, 0, 1.5, 2.0
    )
    r2 = backtest_core(
        open_, high, low, close, ts, trend, adx, pdi, mdi, a, 14, 20, 15.0, 0, 1.5, 2.0
    )
    assert r1[4] > 0
    assert r1 == r2
