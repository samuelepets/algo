"""Unit tests for the VWAP trend backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import ENTRY_ABOVE, ENTRY_BOUNCE, backtest_core
from indicators import atr, vwap_bands


def _bars(close: np.ndarray) -> tuple[np.ndarray, ...]:
    ts = np.arange(close.size, dtype=np.int64) * 300
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def _prep(close: np.ndarray):
    ts, open_, high, low, close = _bars(close)
    v, s = vwap_bands(high, low, close, np.ones(close.size), ts, 0)
    a = atr(high, low, close, 14)
    return ts, open_, high, low, close, v, s, a


def test_no_trades_on_flat_bars() -> None:
    close = np.full(200, 1.1, dtype=np.float64)
    ts, open_, high, low, close, v, s, a = _prep(close)
    # std is ~0 → engine skips every bar.
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, v, s, a, ENTRY_BOUNCE, 1.5, 1.0
    )
    assert n_trades == 0


def test_bounce_trades_and_deterministic() -> None:
    t = np.arange(4000, dtype=np.float64)
    close = 1.10 + 0.02 * np.sin(t / 40.0) + 0.006 * np.sin(t / 9.0)
    ts, open_, high, low, close, v, s, a = _prep(close)
    r1 = backtest_core(open_, high, low, close, ts, v, s, a, ENTRY_BOUNCE, 1.0, 1.0)
    r2 = backtest_core(open_, high, low, close, ts, v, s, a, ENTRY_BOUNCE, 1.0, 1.0)
    assert r1[4] > 0
    assert r1 == r2


def test_continuation_runs() -> None:
    t = np.arange(4000, dtype=np.float64)
    close = 1.10 + 0.02 * np.sin(t / 40.0) + 0.006 * np.sin(t / 9.0)
    ts, open_, high, low, close, v, s, a = _prep(close)
    res = backtest_core(open_, high, low, close, ts, v, s, a, ENTRY_ABOVE, 1.0, 1.0)
    assert res[4] >= 0
    assert np.isfinite(res[0])
