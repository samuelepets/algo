"""Sanity tests for the MR-14 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core


def _flat_series(n: int, price: float = 1.1) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    close = np.full(n, price, dtype=np.float64)
    high = close + 0.0005
    low = close - 0.0005
    ts = np.arange(n, dtype=np.int64) * 300
    return close, high, low, ts


def test_no_trades_when_k_never_crosses_threshold() -> None:
    n = 60
    close, high, low, ts = _flat_series(n)
    k_vals = np.full(n, 0.5)
    atr_vals = np.full(n, 0.001)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, k_vals, atr_vals,
        oversold_thresh=0.10, overbought_thresh=0.90, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 0


def test_long_entry_and_midline_exit() -> None:
    n = 30
    close, high, low, ts = _flat_series(n)
    k_vals = np.full(n, 0.5)
    k_vals[9] = 0.30
    k_vals[10] = 0.05  # crosses below 0.10 -> long entry
    for i in range(11, 15):
        k_vals[i] = 0.05
    k_vals[15] = 0.60  # crosses back above 0.5 -> exit
    atr_vals = np.full(n, 0.001)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, k_vals, atr_vals,
        oversold_thresh=0.10, overbought_thresh=0.90, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_short_entry_and_midline_exit() -> None:
    n = 30
    close, high, low, ts = _flat_series(n)
    k_vals = np.full(n, 0.5)
    k_vals[9] = 0.70
    k_vals[10] = 0.95  # crosses above 0.90 -> short entry
    for i in range(11, 15):
        k_vals[i] = 0.95
    k_vals[15] = 0.40  # crosses back below 0.5 -> exit
    atr_vals = np.full(n, 0.001)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, k_vals, atr_vals,
        oversold_thresh=0.10, overbought_thresh=0.90, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_stop_loss_closes_position() -> None:
    n = 30
    close = np.full(n, 1.1, dtype=np.float64)
    high = close.copy()
    low = close.copy()
    ts = np.arange(n, dtype=np.int64) * 300
    k_vals = np.full(n, 0.5)
    k_vals[9] = 0.30
    k_vals[10] = 0.05  # long entry at bar 10
    atr_vals = np.full(n, 0.001)
    low[11] = close[10] - 0.01  # crashes through the stop
    high[11] = close[10]
    close[11] = close[10] - 0.005
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, k_vals, atr_vals,
        oversold_thresh=0.10, overbought_thresh=0.90, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_forced_exit_after_max_bars() -> None:
    n = 130
    close, high, low, ts = _flat_series(n)
    k_vals = np.full(n, 0.30)
    k_vals[10] = 0.05  # crosses below 0.10 at bar 10 -> long entry, then stays low
    atr_vals = np.full(n, 0.001)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, k_vals, atr_vals,
        oversold_thresh=0.10, overbought_thresh=0.90, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1
