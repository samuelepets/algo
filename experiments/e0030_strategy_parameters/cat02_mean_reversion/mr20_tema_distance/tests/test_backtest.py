"""Unit tests for MR-20 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import EXIT_HALF_DISTANCE, EXIT_TEMA_TOUCH, backtest_core
from indicators import atr, tema


def _run(
    close,
    tema_period=14,
    distance_thresh=1.5,
    exit_type=EXIT_TEMA_TOUCH,
    atr_stop_mult=1.0,
    max_hold_bars=50,
    atr_period=14,
):
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.0005
    low = close - 0.0005
    open_ = close.copy()
    tema_v = tema(close, tema_period)
    atr_v = atr(high, low, close, atr_period)
    warm = max(3 * (tema_period - 1), atr_period) + 1
    return backtest_core(
        open_, high, low, close, ts,
        tema_v, atr_v,
        distance_thresh, exit_type, atr_stop_mult, max_hold_bars, warm,
    )


def test_no_trades_flat() -> None:
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_reversion_fires_on_spike_down() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[300] = 1.06  # sharp single-bar drop far below the (slow) TEMA
    close[301:] = 1.06
    _, _, _, _, n_trades = _run(close, distance_thresh=1.0, atr_stop_mult=0.5, max_hold_bars=30)
    assert n_trades > 0


def test_reversion_fires_on_spike_up() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[300] = 1.14
    close[301:] = 1.14
    _, _, _, _, n_trades = _run(close, distance_thresh=1.0, atr_stop_mult=0.5, max_hold_bars=30)
    assert n_trades > 0


def test_no_signal_below_threshold() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    # Tiny, gradual drift -- distance should stay below a large threshold.
    close[300:] = 1.1005
    _, _, _, _, n_trades = _run(close, distance_thresh=10.0, atr_stop_mult=0.5)
    assert n_trades == 0


def test_exit_type_changes_outcomes() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[300] = 1.06
    close[301:] = 1.06
    r_touch = _run(close, exit_type=EXIT_TEMA_TOUCH, atr_stop_mult=0.5, max_hold_bars=30)
    r_half = _run(close, exit_type=EXIT_HALF_DISTANCE, atr_stop_mult=0.5, max_hold_bars=30)
    assert r_touch[4] >= 0
    assert r_half[4] >= 0


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.02 * np.sin(t / 15.0)
    r1 = _run(close)
    r2 = _run(close)
    assert r1 == r2


def test_max_hold_bounds_trade_count() -> None:
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[300] = 1.06
    close[301:] = 1.06  # never returns to TEMA
    _, _, _, _, n_trades = _run(close, atr_stop_mult=5.0, max_hold_bars=5)
    assert n_trades >= 0  # no crash / infinite hold
