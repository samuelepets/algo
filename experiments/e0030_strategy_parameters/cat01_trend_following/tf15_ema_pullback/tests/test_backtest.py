"""Unit tests for the EMA Pullback backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import PATTERN_ANY, PATTERN_NONE, TOUCH_LOW, backtest_core
from indicators import atr, ema


def _bars(close: np.ndarray) -> tuple[np.ndarray, ...]:
    ts = np.arange(close.size, dtype=np.int64) * 60
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_flat() -> None:
    """Flat bars produce no trades because no trend is established."""
    close = np.full(200, 1.1, dtype=np.float64)
    ts, open_, high, low, close = _bars(close)
    ef = ema(close, 9)
    es = ema(close, 50)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, ef, es, a, 50, TOUCH_LOW, PATTERN_NONE, 1.5, 2.0
    )
    assert n_trades == 0


def test_long_signal_fires() -> None:
    """Synthetic uptrend with pullbacks produces trades; result is deterministic."""
    n = 3000
    t = np.arange(n, dtype=np.float64)
    # Uptrend with oscillations so pullbacks to fast EMA occur
    close = 1.10 + 0.001 * t + 0.005 * np.sin(t / 20.0)
    ts, open_, high, low, close = _bars(close)
    ef = ema(close, 9)
    es = ema(close, 50)
    a = atr(high, low, close, 14)
    r1 = backtest_core(
        open_, high, low, close, ts, ef, es, a, 50, TOUCH_LOW, PATTERN_ANY, 1.5, 2.0
    )
    r2 = backtest_core(
        open_, high, low, close, ts, ef, es, a, 50, TOUCH_LOW, PATTERN_ANY, 1.5, 2.0
    )
    assert r1[4] > 0, "Expected at least one trade on uptrending data"
    assert r1 == r2, "Backtest must be deterministic"
