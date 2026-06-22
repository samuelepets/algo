"""Unit tests for the HMA backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import MODE_CROSSOVER, MODE_SLOPE, backtest_core
from indicators import atr, hma


def _bars(close: np.ndarray) -> tuple[np.ndarray, ...]:
    ts = np.arange(close.size, dtype=np.int64) * 60
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_on_flat_bars() -> None:
    close = np.full(200, 1.1, dtype=np.float64)
    ts, open_, high, low, close = _bars(close)
    hf = hma(close, 9)
    hs = hma(close, 25)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, hf, hs, a, 30, MODE_SLOPE, 2, 1.5, 2.0
    )
    assert n_trades == 0


def test_slope_mode_trades_and_deterministic() -> None:
    t = np.arange(3000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 50.0) + 0.005 * np.sin(t / 11.0)
    ts, open_, high, low, close = _bars(close)
    hf = hma(close, 9)
    hs = hma(close, 25)
    a = atr(high, low, close, 14)
    r1 = backtest_core(open_, high, low, close, ts, hf, hs, a, 30, MODE_SLOPE, 2, 1.5, 2.0)
    r2 = backtest_core(open_, high, low, close, ts, hf, hs, a, 30, MODE_SLOPE, 2, 1.5, 2.0)
    assert r1[4] > 0
    assert r1 == r2


def test_crossover_mode_runs() -> None:
    t = np.arange(3000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 50.0) + 0.005 * np.sin(t / 11.0)
    ts, open_, high, low, close = _bars(close)
    hf = hma(close, 9)
    hs = hma(close, 25)
    a = atr(high, low, close, 14)
    res = backtest_core(open_, high, low, close, ts, hf, hs, a, 30, MODE_CROSSOVER, 1, 1.5, 2.0)
    assert res[4] >= 0
    assert np.isfinite(res[0])
