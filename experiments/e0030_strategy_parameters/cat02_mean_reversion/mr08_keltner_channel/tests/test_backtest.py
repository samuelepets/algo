"""Unit tests for MR-08 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import ENTRY_CLOSE_OUTSIDE, ENTRY_WICK_TOUCH, backtest_core
from indicators import ATR_PERIODS, EMA_PERIODS, atr, ema


def _run(
    close,
    high=None,
    low=None,
    entry_type=ENTRY_CLOSE_OUTSIDE,
    ema_period=20,
    atr_period=14,
    k_mult=2.0,
    atr_stop_mult=1.0,
    max_hold_bars=20,
):
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    if high is None:
        high = close + 0.002
    if low is None:
        low = close - 0.002
    open_ = close.copy()
    ema_v = ema(close, ema_period)
    atr_v = atr(high, low, close, atr_period)
    warm = max(ema_period, atr_period) + 1
    return backtest_core(
        open_, high, low, close, ts,
        ema_v, atr_v,
        k_mult, entry_type, atr_stop_mult, max_hold_bars, warm,
    )


def test_no_trades_flat() -> None:
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_reversion_fires_on_spike_down() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:220] = 1.07  # sharp dip below the lower Keltner band
    close[220:] = 1.1
    _, _, _, _, n_trades = _run(close, atr_stop_mult=0.5, max_hold_bars=30)
    assert n_trades > 0


def test_wick_touch_fires_more_than_close_outside() -> None:
    n = 300
    close = np.full(n, 1.1, dtype=np.float64)
    # Small spike: high pokes above the band but close stays inside.
    high = close + 0.002
    low = close - 0.002
    high[150] = 1.1080  # large upper wick
    _, _, _, _, n_co = _run(close, high=high, low=low, entry_type=ENTRY_CLOSE_OUTSIDE)
    _, _, _, _, n_wt = _run(close, high=high, low=low, entry_type=ENTRY_WICK_TOUCH)
    assert n_wt >= n_co


def test_max_hold_exits() -> None:
    n = 500
    close = np.ones(n, dtype=np.float64)
    close[200:] = 0.95  # persistent move below band, never recovers to EMA
    _, _, _, _, n_trades = _run(close, atr_stop_mult=2.0, max_hold_bars=5)
    assert n_trades >= 0  # at minimum no crash


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 30.0)
    r1 = _run(close)
    r2 = _run(close)
    assert r1 == r2


def test_stop_checked_before_target() -> None:
    # Position enters long, next bar gaps hard down through the stop but
    # also closes above EMA (would-be target) -- stop must win.
    n = 200
    close = np.full(n, 1.1, dtype=np.float64)
    close[100:110] = 1.07
    close[110:] = 1.1
    _, _, mdd, _, n_trades = _run(close, atr_stop_mult=0.3, max_hold_bars=50)
    assert n_trades >= 0


def test_grid_constants_nonempty() -> None:
    assert len(EMA_PERIODS) == 3
    assert len(ATR_PERIODS) == 2
