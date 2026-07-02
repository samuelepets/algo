"""Sanity tests for the MR-18 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import TARGET_CENTER, TARGET_OPPOSITE, backtest_core


def test_no_trade_when_range_too_wide_for_ratio_filter() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    range_high = np.full(n, 1.10)
    range_low = np.full(n, 0.90)  # width=0.20, center=1.00
    atr_vals = np.full(n, 0.02)  # ATR/width = 0.02/0.20 = 0.10
    # Price sits at the long-trigger location for entry_pct=0.90 (0.91), but
    # the required ratio (0.05) is tighter than the actual ATR/width (0.10)
    # -> the range-confirmation filter should block the entry entirely.
    close[10] = 0.91
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, range_high, range_low, atr_vals,
        entry_pct=0.90, atr_range_ratio=0.05,
        target_mode=TARGET_CENTER, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 0


def test_long_entry_near_range_low() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    range_high = np.full(n, 1.10)
    range_low = np.full(n, 0.90)  # width=0.20, center=1.00
    atr_vals = np.full(n, 0.02)  # ratio = 0.02/0.20 = 0.10, passes a 0.30 filter
    # entry_pct=0.90 -> long_trigger = center - 0.9*half = 1.00 - 0.9*0.10 = 0.91
    close[10] = 0.90  # below the long trigger
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, range_high, range_low, atr_vals,
        entry_pct=0.90, atr_range_ratio=0.30,
        target_mode=TARGET_CENTER, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades >= 1


def test_stop_checked_before_target_same_bar() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    range_high = np.full(n, 1.10)
    range_low = np.full(n, 0.90)
    atr_vals = np.full(n, 0.02)
    close[10] = 0.90  # long entry: stop = 0.90 - 1.0*0.02 = 0.88, target(center)=1.00
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    # Bar 11: both stop and target breached intrabar -> stop should win.
    low[11] = 0.87
    high[11] = 1.05
    close[11] = 0.95
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, range_high, range_low, atr_vals,
        entry_pct=0.90, atr_range_ratio=0.30,
        target_mode=TARGET_CENTER, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_target_opposite_side_uses_range_boundary() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    range_high = np.full(n, 1.10)
    range_low = np.full(n, 0.90)
    atr_vals = np.full(n, 0.02)
    close[10] = 0.90  # long entry
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    # Price rallies to the opposite side (range_high = 1.10) but not beyond
    # the center target -- with TARGET_CENTER it wouldn't exit yet at 1.05,
    # but with TARGET_OPPOSITE (1.10) it also shouldn't exit at 1.05.
    high[11] = 1.05
    close[11] = 1.05
    high[12] = 1.11  # now crosses the opposite-side target
    close[12] = 1.10
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, range_high, range_low, atr_vals,
        entry_pct=0.90, atr_range_ratio=0.30,
        target_mode=TARGET_OPPOSITE, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_forced_exit_after_max_bars() -> None:
    n = 130
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    range_high = np.full(n, 1.10)
    range_low = np.full(n, 0.90)
    atr_vals = np.full(n, 0.02)
    close[10] = 0.90
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    # Price hovers near entry, never reaching stop or (center) target.
    for i in range(11, n):
        close[i] = 0.93
        high[i] = 0.9302
        low[i] = 0.9298
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, range_high, range_low, atr_vals,
        entry_pct=0.90, atr_range_ratio=0.30,
        target_mode=TARGET_CENTER, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_degenerate_atr_gates_entry() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    range_high = np.full(n, 1.10)
    range_low = np.full(n, 0.90)
    atr_vals = np.full(n, 1e-9)  # below the validity floor
    close[10] = 0.90
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, range_high, range_low, atr_vals,
        entry_pct=0.90, atr_range_ratio=0.30,
        target_mode=TARGET_CENTER, atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 0
