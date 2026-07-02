"""Unit tests for MR-15 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_demarker_cache, demarker


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


def test_demarker_warmup_nans() -> None:
    n = 30
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.001
    result = demarker(high, low, 14)
    assert np.all(np.isnan(result[:14]))
    assert not np.isnan(result[14])


def test_demarker_all_higher_highs_is_1() -> None:
    # Strictly increasing highs, flat lows -> DeMax always positive, DeMin
    # always zero -> DeMarker = 1.
    n = 20
    high = np.linspace(1.0, 1.2, n)
    low = np.full(n, 0.9)
    result = demarker(high, low, 10)
    assert abs(result[-1] - 1.0) < 1e-9


def test_demarker_all_lower_lows_is_0() -> None:
    # Strictly decreasing lows, flat highs -> DeMin always positive, DeMax
    # always zero -> DeMarker = 0.
    n = 20
    high = np.full(n, 1.2)
    low = np.linspace(1.1, 0.9, n)
    result = demarker(high, low, 10)
    assert abs(result[-1] - 0.0) < 1e-9


def test_demarker_flat_series_is_half() -> None:
    # No High/Low change at all -> both sums zero -> defined as 0.5.
    n = 20
    high = np.full(n, 1.1)
    low = np.full(n, 0.9)
    result = demarker(high, low, 10)
    assert abs(result[-1] - 0.5) < 1e-9


def test_demarker_bounded() -> None:
    n = 60
    t = np.arange(n)
    high = 1.1 + 0.01 * np.sin(t / 5.0) + 0.0005 * t
    low = high - 0.002 - 0.0003 * np.cos(t / 3.0)
    result = demarker(high, low, 14)
    valid = result[~np.isnan(result)]
    assert len(valid) > 0
    assert np.all(valid >= 0.0) and np.all(valid <= 1.0)


def test_build_demarker_cache_shape() -> None:
    n = 100
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.001
    dem_matrix, idx = build_demarker_cache(high, low, [5, 10, 14, 20])
    assert dem_matrix.shape == (4, n)
    assert set(idx.keys()) == {5, 10, 14, 20}


def test_build_demarker_cache_deduplicates() -> None:
    n = 60
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.001
    dem_matrix, idx = build_demarker_cache(high, low, [14, 14, 20])
    assert dem_matrix.shape[0] == 2
    assert len(idx) == 2


def test_demarker_short_series_all_nan() -> None:
    n = 5
    high = np.linspace(1.0, 1.01, n)
    low = high - 0.001
    result = demarker(high, low, 14)
    assert np.all(np.isnan(result))
