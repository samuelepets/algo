"""Unit tests for the Williams Alligator backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import atr, shifted, smma


def _bars(close: np.ndarray) -> tuple[np.ndarray, ...]:
    ts = np.arange(close.size, dtype=np.int64) * 300
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def _lines(close: np.ndarray):
    ts, open_, high, low, close = _bars(close)
    median = (high + low) / 2.0
    jaw = shifted(smma(median, 13), 8)
    teeth = shifted(smma(median, 8), 5)
    lips = shifted(smma(median, 5), 3)
    a = atr(high, low, close, 14)
    return ts, open_, high, low, close, jaw, teeth, lips, a


def test_no_trades_on_flat_bars() -> None:
    close = np.full(200, 1.1, dtype=np.float64)
    ts, open_, high, low, close, jaw, teeth, lips, a = _lines(close)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, jaw, teeth, lips, a, 21, 1.5, 2.0
    )
    assert n_trades == 0


def test_trades_and_deterministic() -> None:
    t = np.arange(3000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 45.0) + 0.006 * np.sin(t / 11.0)
    ts, open_, high, low, close, jaw, teeth, lips, a = _lines(close)
    r1 = backtest_core(open_, high, low, close, ts, jaw, teeth, lips, a, 21, 1.5, 2.0)
    r2 = backtest_core(open_, high, low, close, ts, jaw, teeth, lips, a, 21, 1.5, 2.0)
    assert r1[4] > 0
    assert r1 == r2
