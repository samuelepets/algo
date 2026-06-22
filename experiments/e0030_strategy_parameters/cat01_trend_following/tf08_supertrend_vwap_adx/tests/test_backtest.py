"""Unit tests for the SuperTrend + VWAP + ADX backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import adx_dmi, atr, ema, vwap_daily


def _bars(close: np.ndarray) -> tuple[np.ndarray, ...]:
    ts = np.arange(close.size, dtype=np.int64) * 300
    high = close + 0.0015
    low = close - 0.0015
    open_ = close.copy()
    return ts, open_, high, low, close


def _prep(close: np.ndarray, st_atr: int = 10, adx_p: int = 14, trend: int = 21):
    ts, open_, high, low, close = _bars(close)
    a = atr(high, low, close, st_atr)
    adx, _, _ = adx_dmi(high, low, close, adx_p)
    em = ema(close, trend)
    vw = vwap_daily(high, low, close, np.ones(close.size), ts)
    return ts, open_, high, low, close, a, vw, em, adx


def test_no_trades_on_flat_bars() -> None:
    close = np.full(200, 1.1, dtype=np.float64)
    ts, open_, high, low, close, a, vw, em, adx = _prep(close)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, a, vw, em, adx, 10, 21, 14, 3.0, 25.0, 2.0
    )
    assert n_trades == 0


def test_high_adx_threshold_blocks_all() -> None:
    t = np.arange(3000, dtype=np.float64)
    close = 1.10 + 0.03 * np.sin(t / 35.0) + 0.006 * np.sin(t / 11.0)
    ts, open_, high, low, close, a, vw, em, adx = _prep(close)
    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, a, vw, em, adx, 10, 21, 14, 3.0, 100.0, 2.0
    )
    assert n_trades == 0


def test_trades_generated_and_deterministic() -> None:
    t = np.arange(4000, dtype=np.float64)
    close = 1.10 + 0.04 * np.sin(t / 60.0) + 0.008 * np.sin(t / 13.0)
    ts, open_, high, low, close, a, vw, em, adx = _prep(close)
    r1 = backtest_core(
        open_, high, low, close, ts, a, vw, em, adx, 10, 21, 14, 2.0, 15.0, 2.0
    )
    r2 = backtest_core(
        open_, high, low, close, ts, a, vw, em, adx, 10, 21, 14, 2.0, 15.0, 2.0
    )
    assert r1[4] > 0
    assert r1 == r2
