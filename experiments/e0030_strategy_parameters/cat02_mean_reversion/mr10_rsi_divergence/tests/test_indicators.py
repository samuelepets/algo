"""Unit tests for MR-10 indicators (RSI, ATR, swing pivots)."""

from __future__ import annotations

import numpy as np

from indicators import (
    atr,
    build_pivot_cache,
    build_rsi_cache,
    pivot_highs,
    pivot_lows,
    rsi,
)


def test_rsi_monotonic_up_saturates_100() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float64)
    result = rsi(close, 3)
    assert not np.isnan(result[3])
    assert abs(result[3] - 100.0) < 1e-9
    assert abs(result[-1] - 100.0) < 1e-9


def test_rsi_warmup_nans() -> None:
    close = np.linspace(1.0, 1.1, 30)
    result = rsi(close, 7)
    assert np.all(np.isnan(result[:7]))
    assert not np.isnan(result[7])


def test_rsi_hand_computed_alternating_series() -> None:
    # close: 10,11,10,11,10,11,10,11,10 ; period=2
    close = np.array([10.0, 11.0, 10.0, 11.0, 10.0, 11.0, 10.0, 11.0, 10.0], dtype=np.float64)
    result = rsi(close, 2)
    # diff1=+1, diff2=-1 -> avg_gain=0.5, avg_loss=0.5 -> RSI=50
    assert abs(result[2] - 50.0) < 1e-9
    # diff3=+1 -> avg_gain=(0.5*1+1)/2=0.75, avg_loss=(0.5*1+0)/2=0.25 -> RS=3 -> RSI=75
    assert abs(result[3] - 75.0) < 1e-9
    # diff4=-1 -> avg_gain=(0.75*1+0)/2=0.375, avg_loss=(0.25*1+1)/2=0.625 -> RS=0.6 -> RSI=37.5
    assert abs(result[4] - 37.5) < 1e-9


def test_rsi_flat_series_is_100_by_convention() -> None:
    # Zero average loss -> RSI defined as 100 (no losing bars to divide by).
    close = np.full(20, 1.1, dtype=np.float64)
    result = rsi(close, 5)
    assert abs(result[-1] - 100.0) < 1e-9


def test_atr_flat() -> None:
    flat = np.ones(20, dtype=np.float64)
    result = atr(flat, flat, flat, 14)
    assert abs(result[13]) < 1e-10


def test_atr_warmup_nans() -> None:
    h = np.ones(20, dtype=np.float64) * 1.1
    lo = np.ones(20, dtype=np.float64) * 0.9
    c = np.ones(20, dtype=np.float64)
    result = atr(h, lo, c, 14)
    assert np.all(np.isnan(result[:13]))
    assert not np.isnan(result[13])


def test_pivot_lows_hand_computed() -> None:
    low = np.array([5.0, 4.0, 3.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    result = pivot_lows(low, 2)
    # only index 3 (value 2) is the strict minimum of the full window
    assert np.isnan(result[2])
    assert abs(result[3] - 2.0) < 1e-12
    assert np.isnan(result[4])


def test_pivot_lows_tie_break_picks_last() -> None:
    low = np.array([5.0, 3.0, 3.0, 5.0], dtype=np.float64)
    result = pivot_lows(low, 1)
    # p=1: window [5,3,3], tie with p=2 -> disqualified
    assert np.isnan(result[1])
    # p=2: window [3,3,5], no later tie within window -> pivot
    assert abs(result[2] - 3.0) < 1e-12


def test_pivot_highs_hand_computed() -> None:
    high = np.array([1.0, 2.0, 3.0, 2.0, 1.0], dtype=np.float64)
    result = pivot_highs(high, 1)
    assert np.isnan(result[1])
    assert abs(result[2] - 3.0) < 1e-12
    assert np.isnan(result[3])


def test_pivot_lows_edge_bars_unevaluated() -> None:
    low = np.linspace(1.0, 1.1, 10)
    result = pivot_lows(low, 3)
    # bars within `lookback` of either edge cannot be evaluated
    assert np.all(np.isnan(result[:3]))
    assert np.all(np.isnan(result[-3:]))


def test_build_rsi_cache_shape_and_dedup() -> None:
    close = np.linspace(1.0, 1.1, 100)
    matrix, idx = build_rsi_cache(close, [7, 10, 14, 7])
    assert matrix.shape == (3, 100)
    assert set(idx.keys()) == {7, 10, 14}


def test_build_pivot_cache_shape_and_dedup() -> None:
    n = 200
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.001
    pl_matrix, ph_matrix, idx = build_pivot_cache(high, low, [3, 5, 5, 8])
    assert pl_matrix.shape == (3, n)
    assert ph_matrix.shape == (3, n)
    assert set(idx.keys()) == {3, 5, 8}
