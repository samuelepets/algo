"""Unit tests for the Parabolic SAR backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import MODE_EXIT_ONLY, MODE_STANDALONE, backtest_core
from indicators import ema


def _bars(close: np.ndarray) -> tuple[np.ndarray, ...]:
    ts = np.arange(close.size, dtype=np.int64) * 300
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def test_no_trades_on_too_short_input() -> None:
    close = np.full(2, 1.1, dtype=np.float64)
    ts, open_, high, low, close = _bars(close)
    ef = ema(close, 9)
    es = ema(close, 21)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, ef, es, 0.02, 0.02, 0.2, MODE_STANDALONE, 21
    )
    assert n_trades == 0


def test_standalone_trades_and_deterministic() -> None:
    t = np.arange(3000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 40.0) + 0.006 * np.sin(t / 11.0)
    ts, open_, high, low, close = _bars(close)
    ef = ema(close, 9)
    es = ema(close, 21)
    r1 = backtest_core(open_, high, low, close, ts, ef, es, 0.02, 0.02, 0.2, MODE_STANDALONE, 21)
    r2 = backtest_core(open_, high, low, close, ts, ef, es, 0.02, 0.02, 0.2, MODE_STANDALONE, 21)
    assert r1[4] > 0
    assert r1 == r2


def test_exit_only_runs() -> None:
    t = np.arange(3000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 40.0) + 0.006 * np.sin(t / 11.0)
    ts, open_, high, low, close = _bars(close)
    ef = ema(close, 9)
    es = ema(close, 21)
    res = backtest_core(open_, high, low, close, ts, ef, es, 0.02, 0.02, 0.2, MODE_EXIT_ONLY, 21)
    assert res[4] >= 0
    assert np.isfinite(res[0])
