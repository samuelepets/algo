"""Unit tests for MR-09 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_atr_cache, build_ema_cache, distance, ema


def test_ema_constant() -> None:
    series = np.full(30, 2.0, dtype=np.float64)
    result = ema(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 2.0) < 1e-12


def test_ema_warmup_nans() -> None:
    result = ema(np.ones(20, dtype=np.float64), 10)
    assert np.all(np.isnan(result[:9]))
    assert not np.isnan(result[9])


def test_ema_seed_is_sma() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    result = ema(close, 5)
    assert abs(result[4] - 3.0) < 1e-12  # SMA(1..5) = 3.0


def test_ema_known_step() -> None:
    # After the SMA seed, next value follows alpha = 2/(period+1)
    close = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 3.0], dtype=np.float64)
    result = ema(close, 5)
    alpha = 2.0 / 6.0
    expected = 1.0 + alpha * (3.0 - 1.0)
    assert abs(result[5] - expected) < 1e-12


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


def test_distance_zero_at_ema() -> None:
    close = np.array([1.0, 1.0, 1.0], dtype=np.float64)
    ema_vals = np.array([1.0, 1.0, 1.0], dtype=np.float64)
    atr_vals = np.array([0.01, 0.01, 0.01], dtype=np.float64)
    result = distance(close, ema_vals, atr_vals)
    assert np.all(np.abs(result) < 1e-12)


def test_distance_known_value() -> None:
    close = np.array([1.02], dtype=np.float64)
    ema_vals = np.array([1.00], dtype=np.float64)
    atr_vals = np.array([0.01], dtype=np.float64)
    result = distance(close, ema_vals, atr_vals)
    assert abs(result[0] - 2.0) < 1e-9  # (1.02-1.00)/0.01 = 2.0


def test_distance_nan_on_zero_atr() -> None:
    close = np.array([1.02], dtype=np.float64)
    ema_vals = np.array([1.00], dtype=np.float64)
    atr_vals = np.array([0.0], dtype=np.float64)
    result = distance(close, ema_vals, atr_vals)
    assert np.isnan(result[0])


def test_distance_negative_below_ema() -> None:
    close = np.array([0.98], dtype=np.float64)
    ema_vals = np.array([1.00], dtype=np.float64)
    atr_vals = np.array([0.01], dtype=np.float64)
    result = distance(close, ema_vals, atr_vals)
    assert abs(result[0] - (-2.0)) < 1e-9


def test_build_ema_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 300)
    ema_m, idx = build_ema_cache(close, [10, 20, 50, 100])
    assert ema_m.shape == (4, 300)
    assert set(idx.keys()) == {10, 20, 50, 100}


def test_build_atr_cache_deduplicates() -> None:
    n = 100
    high = np.linspace(1.0, 1.1, n)
    low = np.linspace(0.95, 1.05, n)
    close = np.linspace(0.97, 1.07, n)
    atr_m, idx = build_atr_cache(high, low, close, [10, 10, 14])
    assert atr_m.shape[0] == 2
    assert len(idx) == 2
