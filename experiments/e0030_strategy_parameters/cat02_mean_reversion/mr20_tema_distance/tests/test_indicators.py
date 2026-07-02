"""Unit tests for MR-20 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_atr_cache, build_tema_cache, ema, tema


def test_ema_constant() -> None:
    series = np.full(30, 2.0, dtype=np.float64)
    result = ema(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 2.0) < 1e-12


def test_ema_warmup_nans() -> None:
    result = ema(np.ones(20, dtype=np.float64), 10)
    assert np.all(np.isnan(result[:9]))
    assert not np.isnan(result[9])


def test_ema_chained_leading_nans() -> None:
    base = np.linspace(1.0, 1.1, 100)
    ema1 = ema(base, 10)
    ema2 = ema(ema1, 10)
    # ema1 has 9 leading NaNs; ema2 should start valid at 9 + 9 = 18
    assert np.all(np.isnan(ema2[:18]))
    assert not np.isnan(ema2[18])


def test_tema_constant_equals_price() -> None:
    # On a constant series, all three EMAs converge to the constant, so
    # TEMA = 3c - 3c + c = c.
    series = np.full(200, 1.25, dtype=np.float64)
    result = tema(series, 9)
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 1.25) < 1e-9


def test_tema_warmup_nans() -> None:
    # TEMA becomes valid once EMA3 (chained thrice) is valid:
    # first valid index = 3 * (period - 1).
    period = 10
    n = 200
    series = np.linspace(1.0, 1.2, n)
    result = tema(series, period)
    first_valid = 3 * (period - 1)
    assert np.all(np.isnan(result[:first_valid]))
    assert not np.isnan(result[first_valid])


def test_tema_formula_matches_manual_computation() -> None:
    series = np.linspace(1.0, 1.3, 150) + 0.001 * np.sin(np.arange(150))
    period = 14
    ema1 = ema(series, period)
    ema2 = ema(ema1, period)
    ema3 = ema(ema2, period)
    expected = 3.0 * ema1 - 3.0 * ema2 + ema3
    result = tema(series, period)
    valid = ~np.isnan(expected)
    assert np.allclose(result[valid], expected[valid], equal_nan=True)


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


def test_build_tema_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 300)
    matrix, idx = build_tema_cache(close, [9, 14, 21, 30])
    assert matrix.shape == (4, 300)
    assert set(idx.keys()) == {9, 14, 21, 30}


def test_build_atr_cache_shape() -> None:
    high = np.linspace(1.0, 1.1, 200) + 0.01
    low = np.linspace(1.0, 1.1, 200) - 0.01
    close = np.linspace(1.0, 1.1, 200)
    matrix, idx = build_atr_cache(high, low, close, [10, 14])
    assert matrix.shape == (2, 200)
    assert set(idx.keys()) == {10, 14}
