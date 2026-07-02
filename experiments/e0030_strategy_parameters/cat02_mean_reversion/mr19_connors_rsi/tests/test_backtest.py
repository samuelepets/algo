"""Sanity tests for the MR-19 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core


def _flat_series(n: int, price: float = 1.1) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    close = np.full(n, price, dtype=np.float64)
    high = close + 0.0005
    low = close - 0.0005
    ts = np.arange(n, dtype=np.int64) * 300
    return close, high, low, ts


def test_no_trades_when_crsi_never_crosses_threshold() -> None:
    n = 60
    close, high, low, ts = _flat_series(n)
    # Neutral CRSI components (average 50) -> never crosses 10/90 thresholds.
    rsi_vals = np.full(n, 50.0)
    ud_vals = np.full(n, 50.0)
    roc_vals = np.full(n, 50.0)
    atr_vals = np.full(n, 0.001)
    sma_vals = np.full(n, 1.1)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, rsi_vals, ud_vals, roc_vals, atr_vals, sma_vals,
        has_trend_filter=False, oversold_thresh=10.0, overbought_thresh=90.0,
        exit_level=50.0, warm_bars=0,
    )
    assert ntrades == 0


def test_long_entry_and_exit_on_crsi_recross() -> None:
    n = 30
    close, high, low, ts = _flat_series(n)
    rsi_vals = np.full(n, 50.0)
    ud_vals = np.full(n, 50.0)
    roc_vals = np.full(n, 50.0)
    # Average CRSI at bar 9 = 30, at bar 10 = 5 (all three components dip
    # together) -> crosses below 10 -> long entry.
    rsi_vals[9] = ud_vals[9] = roc_vals[9] = 30.0
    rsi_vals[10] = ud_vals[10] = roc_vals[10] = 5.0
    for i in range(11, 15):
        rsi_vals[i] = ud_vals[i] = roc_vals[i] = 5.0
    rsi_vals[15] = ud_vals[15] = roc_vals[15] = 60.0  # CRSI=60 crosses above 50 -> exit
    atr_vals = np.full(n, 0.001)
    sma_vals = np.full(n, 1.1)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, rsi_vals, ud_vals, roc_vals, atr_vals, sma_vals,
        has_trend_filter=False, oversold_thresh=10.0, overbought_thresh=90.0,
        exit_level=50.0, warm_bars=0,
    )
    assert ntrades == 1


def test_trend_filter_blocks_long_below_sma() -> None:
    n = 30
    close, high, low, ts = _flat_series(n, price=1.0)
    rsi_vals = np.full(n, 50.0)
    ud_vals = np.full(n, 50.0)
    roc_vals = np.full(n, 50.0)
    rsi_vals[9] = ud_vals[9] = roc_vals[9] = 30.0
    rsi_vals[10] = ud_vals[10] = roc_vals[10] = 5.0
    atr_vals = np.full(n, 0.001)
    sma_vals = np.full(n, 1.5)  # close (1.0) is well below the trend SMA
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, rsi_vals, ud_vals, roc_vals, atr_vals, sma_vals,
        has_trend_filter=True, oversold_thresh=10.0, overbought_thresh=90.0,
        exit_level=50.0, warm_bars=0,
    )
    assert ntrades == 0


def test_trend_filter_allows_long_above_sma() -> None:
    n = 30
    close, high, low, ts = _flat_series(n, price=1.5)
    rsi_vals = np.full(n, 50.0)
    ud_vals = np.full(n, 50.0)
    roc_vals = np.full(n, 50.0)
    rsi_vals[9] = ud_vals[9] = roc_vals[9] = 30.0
    rsi_vals[10] = ud_vals[10] = roc_vals[10] = 5.0
    for i in range(11, 15):
        rsi_vals[i] = ud_vals[i] = roc_vals[i] = 5.0
    rsi_vals[15] = ud_vals[15] = roc_vals[15] = 60.0
    atr_vals = np.full(n, 0.001)
    sma_vals = np.full(n, 1.0)  # close (1.5) is above the trend SMA
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, rsi_vals, ud_vals, roc_vals, atr_vals, sma_vals,
        has_trend_filter=True, oversold_thresh=10.0, overbought_thresh=90.0,
        exit_level=50.0, warm_bars=0,
    )
    assert ntrades == 1


def test_stop_loss_closes_position() -> None:
    n = 30
    close = np.full(n, 1.1, dtype=np.float64)
    high = close.copy()
    low = close.copy()
    ts = np.arange(n, dtype=np.int64) * 300
    rsi_vals = np.full(n, 50.0)
    ud_vals = np.full(n, 50.0)
    roc_vals = np.full(n, 50.0)
    rsi_vals[9] = ud_vals[9] = roc_vals[9] = 30.0
    rsi_vals[10] = ud_vals[10] = roc_vals[10] = 5.0  # long entry at bar 10
    atr_vals = np.full(n, 0.001)
    sma_vals = np.full(n, 1.1)
    low[11] = close[10] - 0.01
    high[11] = close[10]
    close[11] = close[10] - 0.005
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, rsi_vals, ud_vals, roc_vals, atr_vals, sma_vals,
        has_trend_filter=False, oversold_thresh=10.0, overbought_thresh=90.0,
        exit_level=50.0, warm_bars=0,
    )
    assert ntrades == 1


def test_forced_exit_after_max_bars() -> None:
    n = 60
    close, high, low, ts = _flat_series(n)
    rsi_vals = np.full(n, 30.0)
    ud_vals = np.full(n, 30.0)
    roc_vals = np.full(n, 30.0)
    rsi_vals[10] = ud_vals[10] = roc_vals[10] = 5.0  # long entry, then stays low
    atr_vals = np.full(n, 0.001)
    sma_vals = np.full(n, 1.1)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, rsi_vals, ud_vals, roc_vals, atr_vals, sma_vals,
        has_trend_filter=False, oversold_thresh=10.0, overbought_thresh=90.0,
        exit_level=50.0, warm_bars=0,
    )
    assert ntrades == 1


def test_degenerate_atr_gates_entry() -> None:
    n = 30
    close, high, low, ts = _flat_series(n)
    rsi_vals = np.full(n, 50.0)
    ud_vals = np.full(n, 50.0)
    roc_vals = np.full(n, 50.0)
    rsi_vals[9] = ud_vals[9] = roc_vals[9] = 30.0
    rsi_vals[10] = ud_vals[10] = roc_vals[10] = 5.0
    atr_vals = np.full(n, 1e-9)  # below the validity floor
    sma_vals = np.full(n, 1.1)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, rsi_vals, ud_vals, roc_vals, atr_vals, sma_vals,
        has_trend_filter=False, oversold_thresh=10.0, overbought_thresh=90.0,
        exit_level=50.0, warm_bars=0,
    )
    assert ntrades == 0
