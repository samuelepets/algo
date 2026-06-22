"""Unit tests for the EMA ribbon backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import MAX_RIBBON, backtest_core
from indicators import atr, ema


def _bars(close: np.ndarray) -> tuple[np.ndarray, ...]:
    ts = np.arange(close.size, dtype=np.int64) * 300
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def _ribbon(close: np.ndarray, periods: list[int]):
    matrix = np.empty((len(periods), close.size), dtype=np.float64)
    for k, p in enumerate(periods):
        matrix[k] = ema(close, p)
    rows = np.zeros(MAX_RIBBON, dtype=np.int64)
    for k in range(len(periods)):
        rows[k] = k
    return matrix, rows


def test_no_trades_on_flat_bars() -> None:
    close = np.full(300, 1.1, dtype=np.float64)
    ts, open_, high, low, close = _bars(close)
    periods = [5, 10, 20, 40]
    matrix, rows = _ribbon(close, periods)
    a = atr(high, low, close, 14)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, matrix, rows, 4, a, 40, 1.0, 3, 2.0
    )
    assert n_trades == 0


def test_trades_and_deterministic() -> None:
    t = np.arange(4000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 70.0) + 0.005 * np.sin(t / 13.0)
    ts, open_, high, low, close = _bars(close)
    periods = [5, 10, 20, 40]
    matrix, rows = _ribbon(close, periods)
    a = atr(high, low, close, 14)
    r1 = backtest_core(open_, high, low, close, ts, matrix, rows, 4, a, 40, 0.8, 3, 2.0)
    r2 = backtest_core(open_, high, low, close, ts, matrix, rows, 4, a, 40, 0.8, 3, 2.0)
    assert r1[4] > 0
    assert r1 == r2
