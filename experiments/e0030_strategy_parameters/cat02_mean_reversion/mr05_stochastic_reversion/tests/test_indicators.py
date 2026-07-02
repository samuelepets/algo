"""Unit tests for MR-05 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_stoch_cache, sma, stoch_raw_k


def test_sma_constant() -> None:
    series = np.full(30, 2.0, dtype=np.float64)
    result = sma(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 2.0) < 1e-12


def test_sma_warmup_nans() -> None:
    result = sma(np.ones(20, dtype=np.float64), 10)
    assert np.all(np.isnan(result[:9]))
    assert not np.isnan(result[9])


def test_sma_period_one_echoes_input() -> None:
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    result = sma(series, 1)
    assert np.allclose(result, series)


def test_sma_recovers_after_leading_nan_region() -> None:
    # A series with a leading NaN warm-up (as produced by stoch_raw_k) must
    # NOT poison the whole output forever — only windows touching the NaN
    # region should be NaN; windows fully past it must be valid again.
    series = np.concatenate([np.full(4, np.nan), np.full(20, 10.0)])
    result = sma(series, 3)
    assert np.all(np.isnan(result[:5]))  # windows [0:3]..[2:5] all touch NaN region
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 10.0) < 1e-12


def test_sma_period_one_recovers_immediately() -> None:
    series = np.concatenate([np.full(4, np.nan), np.array([7.0, 8.0])])
    result = sma(series, 1)
    assert np.all(np.isnan(result[:4]))
    assert result[4] == 7.0
    assert result[5] == 8.0


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


def test_stoch_raw_k_warmup_nans() -> None:
    n = 30
    high = np.linspace(1.0, 1.3, n)
    low = high - 0.05
    close = (high + low) / 2.0
    result = stoch_raw_k(high, low, close, 5)
    assert np.all(np.isnan(result[:4]))
    assert not np.isnan(result[4])


def test_stoch_raw_k_hand_computed() -> None:
    # Window of 3 bars: lows = [1.0, 1.1, 0.9], highs = [1.2, 1.3, 1.15]
    # lowest_low = 0.9, highest_high = 1.3, range = 0.4
    high = np.array([1.2, 1.3, 1.15], dtype=np.float64)
    low = np.array([1.0, 1.1, 0.9], dtype=np.float64)
    close = np.array([1.1, 1.2, 1.1], dtype=np.float64)  # close[2] = 1.1
    result = stoch_raw_k(high, low, close, 3)
    expected = (1.1 - 0.9) / (1.3 - 0.9) * 100.0
    assert abs(result[2] - expected) < 1e-9


def test_stoch_raw_k_close_at_high_is_100() -> None:
    high = np.array([1.0, 1.1, 1.2], dtype=np.float64)
    low = np.array([0.9, 0.95, 1.0], dtype=np.float64)
    close = np.array([0.95, 1.0, 1.2], dtype=np.float64)  # close == highest_high
    result = stoch_raw_k(high, low, close, 3)
    assert abs(result[2] - 100.0) < 1e-9


def test_stoch_raw_k_close_at_low_is_0() -> None:
    high = np.array([1.0, 1.1, 1.2], dtype=np.float64)
    low = np.array([0.9, 0.95, 0.85], dtype=np.float64)
    close = np.array([0.95, 1.0, 0.85], dtype=np.float64)  # close == lowest_low
    result = stoch_raw_k(high, low, close, 3)
    assert abs(result[2] - 0.0) < 1e-9


def test_stoch_raw_k_flat_range_is_nan() -> None:
    n = 10
    high = np.full(n, 1.1, dtype=np.float64)
    low = np.full(n, 1.1, dtype=np.float64)
    close = np.full(n, 1.1, dtype=np.float64)
    result = stoch_raw_k(high, low, close, 3)
    assert np.all(np.isnan(result[2:]))


def test_build_stoch_cache_shape() -> None:
    n = 200
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.01
    close = (high + low) / 2.0
    k_m, d_m, idx = build_stoch_cache(high, low, close, [5, 9], [1, 3], [3])
    n_combos = 2 * 2 * 1
    assert k_m.shape == (n_combos, n)
    assert d_m.shape == (n_combos, n)
    assert set(idx.keys()) == {
        (5, 1, 3), (5, 3, 3), (9, 1, 3), (9, 3, 3),
    }


def test_build_stoch_cache_deduplicates() -> None:
    n = 200
    high = np.linspace(1.0, 1.1, n)
    low = high - 0.01
    close = (high + low) / 2.0
    # Duplicate (5, 1, 3) triples should collapse to a single row.
    k_m, _d_m, idx = build_stoch_cache(high, low, close, [5, 5], [1, 1], [3, 3])
    assert k_m.shape[0] == 1
    assert len(idx) == 1


def test_build_stoch_cache_values_match_manual_pipeline() -> None:
    n = 200
    high = np.linspace(1.0, 1.2, n)
    low = high - 0.02
    close = (high + low) / 2.0
    k_m, d_m, idx = build_stoch_cache(high, low, close, [5], [3], [3])
    row = idx[(5, 3, 3)]

    raw_k = stoch_raw_k(high, low, close, 5)
    smoothed_k = sma(raw_k, 3)
    d = sma(smoothed_k, 3)

    assert np.isnan(d).sum() < n  # some valid values exist
    assert np.allclose(k_m[row], smoothed_k, equal_nan=True)
    assert np.allclose(d_m[row], d, equal_nan=True)
