"""Unit tests for MR-01 indicators."""

from __future__ import annotations

import numpy as np
import pytest

from indicators import atr, adx, sma, rolling_std_bb, build_bb_cache


def test_sma_constant() -> None:
    series = np.full(30, 2.0, dtype=np.float64)
    result = sma(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 2.0) < 1e-12


def test_sma_warmup_nans() -> None:
    result = sma(np.ones(20, dtype=np.float64), 10)
    assert np.all(np.isnan(result[:9]))
    assert not np.isnan(result[9])


def test_rolling_std_bb_constant() -> None:
    series = np.full(30, 3.0, dtype=np.float64)
    result = rolling_std_bb(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1]) < 1e-12


def test_rolling_std_bb_known() -> None:
    # series [0, 1, 2, 3, 4]: mean=2, var=(4+1+0+1+4)/5=2, std=sqrt(2)
    series = np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    result = rolling_std_bb(series, 5)
    assert abs(result[4] - 2.0 ** 0.5) < 1e-12


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
    # First valid ADX at index 2*14-2 = 26
    assert np.all(np.isnan(result[:26]))
    assert not np.isnan(result[26])


def test_build_bb_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 200)
    sma_m, std_m, idx = build_bb_cache(close, [10, 20, 50])
    assert sma_m.shape == (3, 200)
    assert std_m.shape == (3, 200)
    assert set(idx.keys()) == {10, 20, 50}


def test_build_bb_cache_deduplicates() -> None:
    close = np.linspace(1.0, 1.1, 100)
    sma_m, std_m, idx = build_bb_cache(close, [20, 20, 10])
    assert sma_m.shape[0] == 2
    assert len(idx) == 2
