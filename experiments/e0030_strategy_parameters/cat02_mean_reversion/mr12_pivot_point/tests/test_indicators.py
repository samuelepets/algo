"""Unit tests for MR-12 indicators."""

from __future__ import annotations

import numpy as np

from indicators import DAY_SECS, atr, build_pivot_cache, pivot_levels


def test_atr_flat() -> None:
    flat = np.ones(20, dtype=np.float64)
    result = atr(flat, flat, flat, 14)
    assert abs(result[13]) < 1e-10


def test_pivot_levels_first_bucket_is_nan() -> None:
    # Two days of 4 bars each, 6h apart (well within one calendar day).
    ts = np.array([0, 21600, 43200, 64800, 86400, 108000, 129600, 151200], dtype=np.int64)
    high = np.array([1.05, 1.06, 1.04, 1.03, 1.10, 1.11, 1.09, 1.08])
    low = np.array([1.00, 1.01, 0.99, 0.98, 1.05, 1.06, 1.04, 1.03])
    close = np.array([1.02, 1.03, 1.01, 1.00, 1.07, 1.08, 1.06, 1.05])
    p, r1, r2, s1, s2 = pivot_levels(ts, high, low, close, DAY_SECS)
    assert np.all(np.isnan(p[:4]))


def test_pivot_levels_known_values() -> None:
    # Day 1: H=1.06, L=0.98, C=1.00 (last close of day 1).
    # Day 2 bars should all use day 1's H/L/C for their pivot levels.
    ts = np.array([0, 21600, 43200, 64800, 86400, 108000], dtype=np.int64)
    high = np.array([1.05, 1.06, 1.04, 1.03, 1.10, 1.11])
    low = np.array([1.00, 1.01, 0.99, 0.98, 1.05, 1.06])
    close = np.array([1.02, 1.03, 1.01, 1.00, 1.07, 1.08])
    p, r1, r2, s1, s2 = pivot_levels(ts, high, low, close, DAY_SECS)

    expected_p = (1.06 + 0.98 + 1.00) / 3.0
    expected_r1 = 2.0 * expected_p - 0.98
    expected_r2 = expected_p + (1.06 - 0.98)
    expected_s1 = 2.0 * expected_p - 1.06
    expected_s2 = expected_p - (1.06 - 0.98)

    for i in (4, 5):
        assert abs(p[i] - expected_p) < 1e-12
        assert abs(r1[i] - expected_r1) < 1e-12
        assert abs(r2[i] - expected_r2) < 1e-12
        assert abs(s1[i] - expected_s1) < 1e-12
        assert abs(s2[i] - expected_s2) < 1e-12


def test_pivot_levels_updates_across_three_days() -> None:
    n = 12
    ts = np.arange(n, dtype=np.int64) * (DAY_SECS // 4)  # 4 bars/day, 3 days
    high = np.full(n, 1.05)
    low = np.full(n, 0.95)
    close = np.full(n, 1.00)
    # Make day 2's range distinctly different from day 1's.
    high[4:8] = 1.20
    low[4:8] = 0.80
    p, r1, r2, s1, s2 = pivot_levels(ts, high, low, close, DAY_SECS)
    # Day 3 (indices 8-11) should reflect day 2's wider range -> wider R2-S2.
    assert (r2[8] - s2[8]) > (r2[4] - s2[4])


def test_build_pivot_cache_has_both_periods() -> None:
    n = 20
    ts = np.arange(n, dtype=np.int64) * 3600
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.01
    close = high - 0.005
    cache = build_pivot_cache(ts, high, low, close)
    assert set(cache.keys()) == {0, 1}
    for arrays in cache.values():
        assert len(arrays) == 5
        for arr in arrays:
            assert arr.shape[0] == n
