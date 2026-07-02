"""Unit tests for MR-06 indicators."""

from __future__ import annotations

import numpy as np
import pytest

from indicators import atr, adx, cci, sma, typical_price, build_cci_cache


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


def test_typical_price_known_values() -> None:
    high = np.array([2.0, 4.0, 6.0], dtype=np.float64)
    low = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    close = np.array([1.5, 3.0, 4.5], dtype=np.float64)
    result = typical_price(high, low, close)
    expected = np.array([1.5, 3.0, 4.5], dtype=np.float64)
    np.testing.assert_allclose(result, expected, atol=1e-12)


def test_cci_known_value_linear_ramp() -> None:
    # Zero-range bars (high = low = close) so typical price equals close.
    # For a linear ramp with step 1 and period 3:
    #   window [1, 2, 3] at i=2: sma=2, mad=mean(|1-2|,|2-2|,|3-2|)=2/3
    #   cci[2] = (3 - 2) / (0.015 * 2/3) = 1 / 0.01 = 100.0
    close = np.arange(1.0, 11.0, dtype=np.float64)
    result = cci(close, close, close, 3)
    assert result[2] == pytest.approx(100.0, abs=1e-9)
    assert result[3] == pytest.approx(100.0, abs=1e-9)


def test_cci_warmup_nans() -> None:
    close = np.arange(1.0, 21.0, dtype=np.float64)
    result = cci(close, close, close, 5)
    assert np.all(np.isnan(result[:4]))
    assert not np.isnan(result[4])


def test_cci_constant_price_is_nan() -> None:
    # Flat typical price -> MAD == 0 -> CCI must be NaN, not a divide-by-zero
    # artifact (inf/garbage).
    close = np.full(50, 1.1, dtype=np.float64)
    result = cci(close, close, close, 14)
    valid_region = result[13:]
    assert np.all(np.isnan(valid_region))


def test_cci_symmetric_extremes() -> None:
    # A sharp downward spike should produce a strongly negative CCI; a sharp
    # upward spike should produce a strongly positive CCI.
    n = 40
    close = np.full(n, 1.1, dtype=np.float64)
    close[20] = 1.05  # sharp dip
    result_down = cci(close, close, close, 14)
    assert result_down[20] < -50.0

    close2 = np.full(n, 1.1, dtype=np.float64)
    close2[20] = 1.15  # sharp spike up
    result_up = cci(close2, close2, close2, 14)
    assert result_up[20] > 50.0


def test_cci_short_series_all_nan() -> None:
    close = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    result = cci(close, close, close, 14)
    assert np.all(np.isnan(result))


def test_build_cci_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 200)
    high = close + 0.001
    low = close - 0.001
    cci_m, idx = build_cci_cache(high, low, close, [10, 14, 20, 30])
    assert cci_m.shape == (4, 200)
    assert set(idx.keys()) == {10, 14, 20, 30}


def test_build_cci_cache_deduplicates() -> None:
    close = np.linspace(1.0, 1.1, 100)
    high = close + 0.001
    low = close - 0.001
    cci_m, idx = build_cci_cache(high, low, close, [20, 20, 10])
    assert cci_m.shape[0] == 2
    assert len(idx) == 2
