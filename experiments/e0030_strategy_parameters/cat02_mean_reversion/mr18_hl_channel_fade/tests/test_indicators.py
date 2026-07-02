"""Unit tests for MR-18 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_range_cache, rolling_range


def test_atr_flat() -> None:
    flat = np.ones(20, dtype=np.float64)
    result = atr(flat, flat, flat, 14)
    assert abs(result[13]) < 1e-10


def test_rolling_range_warmup_nans() -> None:
    n = 30
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.001
    rh, rl = rolling_range(high, low, 10)
    assert np.all(np.isnan(rh[:10]))
    assert not np.isnan(rh[10])


def test_rolling_range_excludes_current_bar() -> None:
    n = 15
    high = np.full(n, 1.0)
    low = np.full(n, 0.9)
    # Bar 10 has an extreme high that should NOT appear in range_high at
    # index 10 itself (lookback excludes the current bar), but SHOULD
    # appear at index 11 (now part of the trailing window).
    high[10] = 2.0
    rh, rl = rolling_range(high, low, 5)
    assert rh[10] < 2.0
    assert rh[11] == 2.0


def test_rolling_range_known_values() -> None:
    high = np.array([1.0, 1.2, 1.1, 1.3, 1.05, 1.4])
    low = np.array([0.9, 0.95, 0.85, 1.0, 0.8, 1.1])
    rh, rl = rolling_range(high, low, 3)
    # index 3: window is bars [0,1,2] -> high=1.2, low=0.85
    assert abs(rh[3] - 1.2) < 1e-12
    assert abs(rl[3] - 0.85) < 1e-12
    # index 5: window is bars [2,3,4] -> high=1.3, low=0.8
    assert abs(rh[5] - 1.3) < 1e-12
    assert abs(rl[5] - 0.8) < 1e-12


def test_rolling_range_short_series_all_nan() -> None:
    n = 5
    high = np.linspace(1.0, 1.01, n)
    low = high - 0.001
    rh, rl = rolling_range(high, low, 10)
    assert np.all(np.isnan(rh))
    assert np.all(np.isnan(rl))


def test_build_range_cache_shape() -> None:
    n = 200
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.001
    high_m, low_m, idx = build_range_cache(high, low, [20, 30, 50, 100])
    assert high_m.shape == (4, n)
    assert low_m.shape == (4, n)
    assert set(idx.keys()) == {20, 30, 50, 100}


def test_build_range_cache_deduplicates() -> None:
    n = 150
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.001
    high_m, _, idx = build_range_cache(high, low, [20, 20, 30])
    assert high_m.shape[0] == 2
    assert len(idx) == 2
