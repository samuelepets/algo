"""Sanity tests for the MR-12 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import FADE_S1_R1, FADE_S2_R2, TARGET_MID, TARGET_P, backtest_core


def _levels(n: int, p: float, r1: float, r2: float, s1: float, s2: float) -> tuple:
    return (
        np.full(n, p, dtype=np.float64),
        np.full(n, r1, dtype=np.float64),
        np.full(n, r2, dtype=np.float64),
        np.full(n, s1, dtype=np.float64),
        np.full(n, s2, dtype=np.float64),
    )


def test_no_trade_when_price_far_from_levels() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    p, r1, r2, s1, s2 = _levels(n, 1.00, 1.10, 1.20, 0.90, 0.80)
    atr_vals = np.full(n, 0.001)
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, p, r1, r2, s1, s2, atr_vals,
        fade_level=FADE_S1_R1, touch_atr_thresh=0.25, target_mode=TARGET_P,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 0


def test_long_entry_on_s1_touch_targets_pivot() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    p, r1, r2, s1, s2 = _levels(n, 1.00, 1.10, 1.20, 0.90, 0.80)
    atr_vals = np.full(n, 0.01)
    # touch_atr_thresh=0.5 -> trigger zone = S1 + 0.5*ATR = 0.90 + 0.005 = 0.905
    close[10] = 0.90
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    # Rally to the central pivot target (1.00).
    high[11] = 1.01
    close[11] = 1.00
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, p, r1, r2, s1, s2, atr_vals,
        fade_level=FADE_S1_R1, touch_atr_thresh=0.5, target_mode=TARGET_P,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_fade_s2_r2_uses_extended_levels() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    p, r1, r2, s1, s2 = _levels(n, 1.00, 1.10, 1.20, 0.90, 0.80)
    atr_vals = np.full(n, 0.01)
    # Price at S1 (0.90) should NOT trigger an S2/R2 fade (S2=0.80).
    close[10] = 0.90
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, p, r1, r2, s1, s2, atr_vals,
        fade_level=FADE_S2_R2, touch_atr_thresh=0.25, target_mode=TARGET_P,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 0


def test_target_mid_is_between_fade_level_and_pivot() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    p, r1, r2, s1, s2 = _levels(n, 1.00, 1.10, 1.20, 0.90, 0.80)
    atr_vals = np.full(n, 0.01)
    close[10] = 0.90  # long entry near S1
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    # mid_SR1_P target = (0.90 + 1.00) / 2 = 0.95 -- reached, but NOT the
    # full pivot (1.00).
    high[11] = 0.951
    close[11] = 0.95
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, p, r1, r2, s1, s2, atr_vals,
        fade_level=FADE_S1_R1, touch_atr_thresh=0.5, target_mode=TARGET_MID,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_stop_checked_before_target_same_bar() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    p, r1, r2, s1, s2 = _levels(n, 1.00, 1.10, 1.20, 0.90, 0.80)
    atr_vals = np.full(n, 0.01)
    close[10] = 0.90  # long entry, stop = 0.90 - 1.0*0.01 = 0.89
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    # Bar 11: both stop and target (pivot=1.00) breached intrabar.
    low[11] = 0.88
    high[11] = 1.01
    close[11] = 0.95
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, p, r1, r2, s1, s2, atr_vals,
        fade_level=FADE_S1_R1, touch_atr_thresh=0.5, target_mode=TARGET_P,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_forced_exit_after_max_bars() -> None:
    n = 130
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    p, r1, r2, s1, s2 = _levels(n, 1.00, 1.10, 1.20, 0.90, 0.80)
    atr_vals = np.full(n, 0.01)
    close[10] = 0.90
    high[10] = close[10] + 0.0002
    low[10] = close[10] - 0.0002
    for i in range(11, n):
        close[i] = 0.92
        high[i] = 0.9202
        low[i] = 0.9198
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, p, r1, r2, s1, s2, atr_vals,
        fade_level=FADE_S1_R1, touch_atr_thresh=0.5, target_mode=TARGET_P,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 1


def test_degenerate_atr_gates_entry() -> None:
    n = 20
    close = np.full(n, 1.00, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    ts = np.arange(n, dtype=np.int64) * 300
    p, r1, r2, s1, s2 = _levels(n, 1.00, 1.10, 1.20, 0.90, 0.80)
    atr_vals = np.full(n, 1e-9)
    close[10] = 0.90
    _, _, _, _, ntrades = backtest_core(
        close, high, low, ts, p, r1, r2, s1, s2, atr_vals,
        fade_level=FADE_S1_R1, touch_atr_thresh=0.5, target_mode=TARGET_P,
        atr_stop_mult=1.0, warm_bars=0,
    )
    assert ntrades == 0
