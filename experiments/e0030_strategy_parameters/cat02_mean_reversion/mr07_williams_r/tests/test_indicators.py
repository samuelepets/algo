"""Unit tests for MR-07 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_wr_cache, williams_r


def test_williams_r_at_high() -> None:
    # Close equals the highest high over the window -> %R = 0
    high = np.array([1.0, 1.1, 1.2, 1.3, 1.4], dtype=np.float64)
    low = np.array([0.9, 1.0, 1.1, 1.2, 1.3], dtype=np.float64)
    close = np.array([0.95, 1.05, 1.15, 1.25, 1.4], dtype=np.float64)
    result = williams_r(high, low, close, 5)
    assert abs(result[4] - 0.0) < 1e-9


def test_williams_r_at_low() -> None:
    # Close equals the lowest low over the window -> %R = -100
    high = np.array([1.0, 1.1, 1.2, 1.3, 1.4], dtype=np.float64)
    low = np.array([0.9, 1.0, 1.1, 1.2, 0.9], dtype=np.float64)
    close = np.array([0.95, 1.05, 1.15, 1.25, 0.9], dtype=np.float64)
    result = williams_r(high, low, close, 5)
    assert abs(result[4] - (-100.0)) < 1e-9


def test_williams_r_known_value() -> None:
    # window: HH=1.4, LL=0.9, close=1.15 -> %R = (1.4-1.15)/(1.4-0.9)*-100 = -50
    high = np.array([1.0, 1.1, 1.2, 1.3, 1.4], dtype=np.float64)
    low = np.array([0.9, 1.0, 1.1, 1.2, 1.3], dtype=np.float64)
    close = np.array([0.95, 1.05, 1.15, 1.25, 1.15], dtype=np.float64)
    result = williams_r(high, low, close, 5)
    assert abs(result[4] - (-50.0)) < 1e-9


def test_williams_r_warmup_nans() -> None:
    n = 20
    high = np.linspace(1.0, 1.2, n)
    low = np.linspace(0.9, 1.1, n)
    close = np.linspace(0.95, 1.15, n)
    result = williams_r(high, low, close, 10)
    assert np.all(np.isnan(result[:9]))
    assert not np.isnan(result[9])


def test_williams_r_flat_range_is_nan() -> None:
    n = 20
    high = np.full(n, 1.0, dtype=np.float64)
    low = np.full(n, 1.0, dtype=np.float64)
    close = np.full(n, 1.0, dtype=np.float64)
    result = williams_r(high, low, close, 5)
    assert np.all(np.isnan(result[4:]))


def test_williams_r_bounds() -> None:
    n = 200
    rng = np.random.default_rng(42)
    close = 1.1 + np.cumsum(rng.normal(0, 0.0005, n))
    high = close + np.abs(rng.normal(0, 0.0003, n))
    low = close - np.abs(rng.normal(0, 0.0003, n))
    result = williams_r(high, low, close, 14)
    valid = result[~np.isnan(result)]
    assert np.all(valid <= 1e-9)
    assert np.all(valid >= -100.0 - 1e-9)


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


def test_build_wr_cache_shape() -> None:
    n = 200
    high = np.linspace(1.0, 1.1, n)
    low = np.linspace(0.95, 1.05, n)
    close = np.linspace(0.97, 1.07, n)
    wr_m, idx = build_wr_cache(high, low, close, [5, 10, 14, 20])
    assert wr_m.shape == (4, n)
    assert set(idx.keys()) == {5, 10, 14, 20}


def test_build_wr_cache_deduplicates() -> None:
    n = 100
    high = np.linspace(1.0, 1.1, n)
    low = np.linspace(0.95, 1.05, n)
    close = np.linspace(0.97, 1.07, n)
    wr_m, idx = build_wr_cache(high, low, close, [10, 10, 5])
    assert wr_m.shape[0] == 2
    assert len(idx) == 2
