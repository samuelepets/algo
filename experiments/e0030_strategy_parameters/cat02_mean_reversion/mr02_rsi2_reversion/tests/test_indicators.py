"""Unit tests for MR-02 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, sma, rsi, build_rsi_cache, build_sma_cache


def test_sma_constant() -> None:
    series = np.full(30, 2.0, dtype=np.float64)
    result = sma(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 2.0) < 1e-12


def test_sma_warmup_nans() -> None:
    result = sma(np.ones(20, dtype=np.float64), 10)
    assert np.all(np.isnan(result[:9]))
    assert not np.isnan(result[9])


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


def test_rsi_flat_series_is_50() -> None:
    # No movement at all -> 0/0 case -> defined as neutral 50.0.
    close = np.full(30, 1.1, dtype=np.float64)
    result = rsi(close, 5)
    assert not np.isnan(result[5])
    assert abs(result[5] - 50.0) < 1e-9
    assert abs(result[-1] - 50.0) < 1e-9


def test_rsi_warmup_nans() -> None:
    # Differencing consumes index 0, so first valid output is at index `period`
    # (not period - 1), one bar later than a same-period ATR/SMA seed.
    close = np.linspace(1.0, 1.2, 20)
    result = rsi(close, 5)
    assert np.all(np.isnan(result[:5]))
    assert not np.isnan(result[5])


def test_rsi_too_short_all_nan() -> None:
    # n < period + 1 => not enough bars to seed even one RSI value.
    close = np.linspace(1.0, 1.05, 5)
    result = rsi(close, 5)
    assert np.all(np.isnan(result))


def test_rsi_strictly_increasing_is_100() -> None:
    close = np.arange(1.0, 20.0, 1.0, dtype=np.float64)
    result = rsi(close, 5)
    assert abs(result[5] - 100.0) < 1e-9
    assert abs(result[-1] - 100.0) < 1e-9


def test_rsi_strictly_decreasing_is_0() -> None:
    close = np.arange(19.0, 0.0, -1.0, dtype=np.float64)
    result = rsi(close, 5)
    assert abs(result[5] - 0.0) < 1e-9
    assert abs(result[-1] - 0.0) < 1e-9


def test_rsi_hand_computed_alternating() -> None:
    # close = [1, 2, 1, 2, 1, 2, 1, 2], period=2.
    # Diffs (index i - i-1): +1,-1,+1,-1,+1,-1,+1 at indices 1..7.
    # Seed (indices 1..2): avg_gain=(1+0)/2=0.5, avg_loss=(0+1)/2=0.5 -> RSI=50.0
    # Wilder step (index 3): avg_gain=0.5-0.25+1=1.25, avg_loss=0.5-0.25+0=0.25
    #   RS=5.0 -> RSI = 100 - 100/6 = 83.3333...
    close = np.array([1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0], dtype=np.float64)
    result = rsi(close, 2)
    assert abs(result[2] - 50.0) < 1e-6
    assert abs(result[3] - 83.333333) < 1e-4


def test_rsi_period_2_shorter_warmup_than_period_5() -> None:
    close = np.linspace(1.0, 1.1, 10)
    r2 = rsi(close, 2)
    r5 = rsi(close, 5)
    assert not np.isnan(r2[2])
    assert np.isnan(r5[2])


def test_build_rsi_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 200)
    matrix, idx = build_rsi_cache(close, [2, 3, 4])
    assert matrix.shape == (3, 200)
    assert set(idx.keys()) == {2, 3, 4}


def test_build_rsi_cache_deduplicates() -> None:
    close = np.linspace(1.0, 1.1, 100)
    matrix, idx = build_rsi_cache(close, [2, 2, 3])
    assert matrix.shape[0] == 2
    assert len(idx) == 2


def test_build_sma_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 300)
    matrix, idx = build_sma_cache(close, [100, 200])
    assert matrix.shape == (2, 300)
    assert set(idx.keys()) == {100, 200}


def test_rsi_bounded_between_0_and_100() -> None:
    rng = np.random.default_rng(42)
    close = 1.1 + np.cumsum(rng.normal(0, 0.0005, 500))
    result = rsi(close, 2)
    valid = result[~np.isnan(result)]
    assert len(valid) > 0
    assert np.all(valid >= 0.0 - 1e-9)
    assert np.all(valid <= 100.0 + 1e-9)
