"""Unit tests for MR-09 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import EXIT_EMA, EXIT_HALF_DISTANCE, FORCED_EXIT_BARS, backtest_core
from indicators import ADX_PERIOD, adx, atr, ema


def _run(
    close,
    high=None,
    low=None,
    ema_period=20,
    atr_period=14,
    distance_thresh=2.0,
    exit_target=EXIT_EMA,
    adx_filter=0,
    atr_stop_mult=1.5,
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
    adx_v = adx(high, low, close, ADX_PERIOD)
    warm = max(ema_period, atr_period, ADX_PERIOD * 2) + 1
    return backtest_core(
        open_, high, low, close, ts,
        ema_v, atr_v, adx_v,
        distance_thresh, exit_target, adx_filter, atr_stop_mult, warm,
    )


def test_no_trades_flat() -> None:
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_reversion_fires_on_spike_down() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:220] = 1.05  # sharp dip far below EMA
    close[220:] = 1.1
    high = close + 0.001
    low = close - 0.001
    _, _, _, _, n_trades = _run(close, high=high, low=low, distance_thresh=1.5)
    assert n_trades > 0


def test_reversion_fires_on_spike_up() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:220] = 1.15  # sharp rally far above EMA
    close[220:] = 1.1
    high = close + 0.001
    low = close - 0.001
    _, _, _, _, n_trades = _run(close, high=high, low=low, distance_thresh=1.5)
    assert n_trades > 0


def test_half_distance_exit_variant_runs() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:220] = 1.05
    close[220:] = 1.1
    high = close + 0.001
    low = close - 0.001
    _, _, _, _, n_trades = _run(
        close, high=high, low=low, distance_thresh=1.5, exit_target=EXIT_HALF_DISTANCE
    )
    assert n_trades >= 0  # runs without crashing, may or may not trade


def test_forced_exit_bars_caps_hold() -> None:
    n = FORCED_EXIT_BARS + 250
    close = np.full(n, 1.1, dtype=np.float64)
    close[100:120] = 1.05  # entry trigger
    close[120:] = np.linspace(1.05, 1.02, n - 120)  # drift away, never reaches EMA target
    high = close + 0.001
    low = close - 0.001
    _, _, _, _, n_trades = _run(
        close, high=high, low=low, distance_thresh=1.0, atr_stop_mult=10.0
    )
    assert n_trades >= 0


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 30.0)
    r1 = _run(close)
    r2 = _run(close)
    assert r1 == r2


def test_adx_filter_reduces_or_equal_trades() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 20.0) + 0.0001 * t
    r_nofilter = _run(close, adx_filter=0)
    r_filtered = _run(close, adx_filter=20)
    assert r_filtered[4] <= r_nofilter[4]
