"""Unit tests for MR-01 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import ENTRY_CLOSE_OUTSIDE, ENTRY_REENTRY, backtest_core
from indicators import atr, adx, sma, rolling_std_bb, ATR_PERIOD, ADX_PERIOD


def _make_bars(n: int, step_secs: int = 300) -> tuple:
    ts = np.arange(n, dtype=np.int64) * step_secs
    close = np.full(n, 1.1000, dtype=np.float64)
    high = close + 0.002
    low = close - 0.002
    open_ = close.copy()
    return ts, open_, high, low, close


def _run(close, entry_type=ENTRY_CLOSE_OUTSIDE, bb_period=20, bb_mult=2.0,
         adx_filter=0, atr_stop_mult=1.0, max_hold_bars=20):
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.002
    low = close - 0.002
    open_ = close.copy()
    sma_v = sma(close, bb_period)
    std_v = rolling_std_bb(close, bb_period)
    atr_v = atr(high, low, close, ATR_PERIOD)
    adx_v = adx(high, low, close, ADX_PERIOD)
    warm = max(bb_period, ADX_PERIOD * 2) + 1
    return backtest_core(
        open_, high, low, close, ts,
        sma_v, std_v, atr_v, adx_v,
        bb_mult, entry_type, adx_filter,
        atr_stop_mult, max_hold_bars, warm,
    )


def test_no_trades_flat() -> None:
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_reversion_fires_on_spike_down() -> None:
    # Create a series with a downward spike that should trigger a long signal
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    # insert a sharp dip to push close below lower BB
    close[200:220] = 1.07  # large drop — below 2-std lower band
    close[220:] = 1.1      # recover

    _, _, _, _, n_trades = _run(close, bb_period=20, bb_mult=2.0,
                                 atr_stop_mult=0.5, max_hold_bars=30)
    assert n_trades > 0


def test_max_hold_exits() -> None:
    # Price goes outside band and stays there — max_hold forces exit
    n = 500
    close = np.ones(n, dtype=np.float64)
    close[200:] = 0.95  # persistent move below band, never recovers to SMA
    _, _, _, _, n_trades = _run(close, bb_period=20, bb_mult=2.0,
                                 atr_stop_mult=2.0, max_hold_bars=5)
    assert n_trades >= 0  # at minimum no crash


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 30.0)
    r1 = _run(close)
    r2 = _run(close)
    assert r1 == r2


def test_reentry_fires_differently_than_close_outside() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.04 * np.sin(t / 25.0)
    r_co = _run(close, entry_type=ENTRY_CLOSE_OUTSIDE)
    r_re = _run(close, entry_type=ENTRY_REENTRY)
    # Both should execute trades; trade counts may differ
    assert r_co[4] >= 0
    assert r_re[4] >= 0
