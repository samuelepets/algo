"""Unit tests for MR-17 indicators."""

from __future__ import annotations

import numpy as np
import pytest

from indicators import atr, adx, ema, build_ema_cache


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
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    result = ema(series, 5)
    assert abs(result[4] - 3.0) < 1e-12


def test_ema_recursion() -> None:
    series = np.concatenate([np.full(10, 1.0), np.full(10, 2.0)]).astype(np.float64)
    result = ema(series, 5)
    seed = result[4]
    mult = 2.0 / 6.0
    expected_next = (series[5] - seed) * mult + seed
    assert abs(result[5] - expected_next) < 1e-12


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


def test_atr_known_value() -> None:
    h = np.full(15, 1.1, dtype=np.float64)
    lo = np.full(15, 1.0, dtype=np.float64)
    c = np.full(15, 1.05, dtype=np.float64)
    result = atr(h, lo, c, 14)
    assert abs(result[13] - 0.1) < 1e-9


def test_adx_flat() -> None:
    flat = np.ones(100, dtype=np.float64)
    result = adx(flat, flat, flat, 14)
    valid = result[~np.isnan(result)]
    assert len(valid) > 0
    assert all(v == pytest.approx(0.0, abs=1e-9) for v in valid)


def test_adx_warmup_nans() -> None:
    n = 60
    h = np.linspace(1.0, 1.1, n)
    lo = np.linspace(0.9, 1.0, n)
    c = np.linspace(0.95, 1.05, n)
    result = adx(h, lo, c, 14)
    assert np.all(np.isnan(result[:26]))
    assert not np.isnan(result[26])


def test_build_ema_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 200)
    matrix, idx = build_ema_cache(close, [10, 20, 50])
    assert matrix.shape == (3, 200)
    assert set(idx.keys()) == {10, 20, 50}


def test_build_ema_cache_deduplicates() -> None:
    close = np.linspace(1.0, 1.1, 100)
    matrix, idx = build_ema_cache(close, [20, 20, 10])
    assert matrix.shape[0] == 2
    assert len(idx) == 2
