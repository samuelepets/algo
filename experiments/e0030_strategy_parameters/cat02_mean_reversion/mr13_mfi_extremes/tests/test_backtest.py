"""Sanity tests for the MR-13 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core


def _flat_series(n: int, price: float = 1.1) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    close = np.full(n, price, dtype=np.float64)
    high = close + 0.0005
    low = close - 0.0005
    ts = np.arange(n, dtype=np.int64) * 60
    return close, high, low, ts


def test_no_trades_when_mfi_never_crosses_threshold() -> None:
    n = 60
    close, high, low, ts = _flat_series(n)
    mfi_vals = np.full(n, 50.0)
    atr_vals = np.full(n, 0.001)
    sharpe, pf, mdd, ret, ntrades = backtest_core(
        close, high, low, ts, mfi_vals, atr_vals,
        oversold_thresh=20.0, overbought_thresh=80.0, exit_level=50.0,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 0
    assert sharpe == 0.0


def test_long_entry_and_exit_on_mfi_recross() -> None:
    n = 30
    close, high, low, ts = _flat_series(n)
    # MFI dips below 20 at bar 10 (entry), then crosses back above 50 at bar 15 (exit).
    mfi_vals = np.full(n, 50.0)
    mfi_vals[9] = 30.0
    mfi_vals[10] = 10.0
    for i in range(11, 15):
        mfi_vals[i] = 10.0
    mfi_vals[15] = 60.0
    atr_vals = np.full(n, 0.001)
    sharpe, pf, mdd, ret, ntrades = backtest_core(
        close, high, low, ts, mfi_vals, atr_vals,
        oversold_thresh=20.0, overbought_thresh=80.0, exit_level=50.0,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_stop_loss_triggers_before_target() -> None:
    n = 30
    close = np.full(n, 1.1, dtype=np.float64)
    high = close.copy()
    low = close.copy()
    ts = np.arange(n, dtype=np.int64) * 60
    mfi_vals = np.full(n, 50.0)
    mfi_vals[9] = 30.0
    mfi_vals[10] = 10.0  # long entry at bar 10
    atr_vals = np.full(n, 0.001)
    # Price crashes through the stop on the next bar.
    low[11] = close[10] - 0.01
    high[11] = close[10]
    close[11] = close[10] - 0.005
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, mfi_vals, atr_vals,
        oversold_thresh=20.0, overbought_thresh=80.0, exit_level=50.0,
        atr_stop_mult=1.0, warm_bars=0,
    )
    # compute_metrics zeroes all aggregate stats below 2 trades; only the
    # trade count is meaningful here.
    assert ntrades == 1


def test_forced_exit_after_max_bars() -> None:
    n = 130
    close, high, low, ts = _flat_series(n)
    mfi_vals = np.full(n, 30.0)  # stays oversold-adjacent, never crosses back to 50
    mfi_vals[9] = 30.0
    mfi_vals[10] = 10.0
    atr_vals = np.full(n, 0.001)
    sharpe, pf, mdd, ret, ntrades = backtest_core(
        close, high, low, ts, mfi_vals, atr_vals,
        oversold_thresh=20.0, overbought_thresh=80.0, exit_level=50.0,
        atr_stop_mult=1.0, warm_bars=0,
    )
    # Position must be forced closed well before the end of a 130-bar series.
    assert ntrades == 1
