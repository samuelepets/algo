"""Unit tests for the Ichimoku backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import SIGNAL_CLOUD, SIGNAL_FULL, SIGNAL_TK, backtest_core
from indicators import midpoint


def _bars(close: np.ndarray) -> tuple[np.ndarray, ...]:
    ts = np.arange(close.size, dtype=np.int64) * 900
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def _lines(close: np.ndarray, t: int = 9, k: int = 26, b: int = 52):
    ts, open_, high, low, close = _bars(close)
    tenkan = midpoint(high, low, t)
    kijun = midpoint(high, low, k)
    senkb = midpoint(high, low, b)
    return ts, open_, high, low, close, tenkan, kijun, senkb


def test_no_trades_on_flat_bars() -> None:
    close = np.full(400, 1.1, dtype=np.float64)
    ts, open_, high, low, close, tenkan, kijun, senkb = _lines(close)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, tenkan, kijun, senkb, 26, 52, SIGNAL_TK, 2.0
    )
    assert n_trades == 0


def test_tk_cross_trades_and_deterministic() -> None:
    t = np.arange(4000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 60.0) + 0.006 * np.sin(t / 13.0)
    ts, open_, high, low, close, tenkan, kijun, senkb = _lines(close)
    r1 = backtest_core(
        open_, high, low, close, ts, tenkan, kijun, senkb, 26, 52, SIGNAL_TK, 2.0
    )
    r2 = backtest_core(
        open_, high, low, close, ts, tenkan, kijun, senkb, 26, 52, SIGNAL_TK, 2.0
    )
    assert r1[4] > 0
    assert r1 == r2


def test_full_and_cloud_signals_run() -> None:
    t = np.arange(4000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 60.0) + 0.006 * np.sin(t / 13.0)
    ts, open_, high, low, close, tenkan, kijun, senkb = _lines(close)
    full = backtest_core(
        open_, high, low, close, ts, tenkan, kijun, senkb, 26, 52, SIGNAL_FULL, 2.0
    )
    cloud = backtest_core(
        open_, high, low, close, ts, tenkan, kijun, senkb, 26, 52, SIGNAL_CLOUD, 2.0
    )
    assert full[4] >= 0 and np.isfinite(full[0])
    assert cloud[4] >= 0 and np.isfinite(cloud[0])
