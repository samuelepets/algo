"""Unit tests for MR-08 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_atr_cache, build_ema_cache, ema


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
    # Seed = SMA of first 5 values = 3.0
    assert abs(result[4] - 3.0) < 1e-12


def test_ema_known_step() -> None:
    # After the seed, EMA should move toward a step change.
    series = np.concatenate([np.full(10, 1.0), np.full(10, 2.0)]).astype(np.float64)
    result = ema(series, 5)
    seed = result[4]
    mult = 2.0 / 6.0
    expected_next = (series[5] - seed) * mult + seed
    assert abs(result[5] - expected_next) < 1e-12


def test_ema_chained_leading_nans() -> None:
    # Chained EMA: feed an EMA output (with leading NaNs) back into ema().
    base = np.linspace(1.0, 1.1, 100)
    ema1 = ema(base, 10)
    ema2 = ema(ema1, 10)
    # ema1 has 9 leading NaNs; ema2 should start valid at 9 + 9 = 18
    assert np.all(np.isnan(ema2[:18]))
    assert not np.isnan(ema2[18])


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
    # Constant true range of 0.1 for 14 bars -> ATR seed = 0.1
    h = np.full(15, 1.1, dtype=np.float64)
    lo = np.full(15, 1.0, dtype=np.float64)
    c = np.full(15, 1.05, dtype=np.float64)
    result = atr(h, lo, c, 14)
    assert abs(result[13] - 0.1) < 1e-9


def test_build_ema_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 200)
    matrix, idx = build_ema_cache(close, [10, 20, 30])
    assert matrix.shape == (3, 200)
    assert set(idx.keys()) == {10, 20, 30}


def test_build_ema_cache_deduplicates() -> None:
    close = np.linspace(1.0, 1.1, 100)
    matrix, idx = build_ema_cache(close, [20, 20, 10])
    assert matrix.shape[0] == 2
    assert len(idx) == 2


def test_build_atr_cache_shape() -> None:
    high = np.linspace(1.0, 1.1, 200) + 0.01
    low = np.linspace(1.0, 1.1, 200) - 0.01
    close = np.linspace(1.0, 1.1, 200)
    matrix, idx = build_atr_cache(high, low, close, [10, 14])
    assert matrix.shape == (2, 200)
    assert set(idx.keys()) == {10, 14}
