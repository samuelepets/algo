"""Unit tests for MR-14 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_k_cache, rsi, sma, stoch_rsi


def test_rsi_all_up_is_100() -> None:
    close = np.linspace(1.0, 1.2, 30)
    result = rsi(close, 14)
    assert abs(result[-1] - 100.0) < 1e-9


def test_rsi_all_down_is_0() -> None:
    close = np.linspace(1.2, 1.0, 30)
    result = rsi(close, 14)
    assert abs(result[-1] - 0.0) < 1e-9


def test_rsi_flat_is_100_by_convention() -> None:
    # No losses at all (avg_loss == 0) -> RSI defined as 100 (matches
    # standard RSI conventions and every other RSI implementation in this repo).
    close = np.full(30, 1.1)
    result = rsi(close, 14)
    assert abs(result[-1] - 100.0) < 1e-9


def test_rsi_warmup_nans() -> None:
    close = np.linspace(1.0, 1.1, 30)
    result = rsi(close, 14)
    assert np.all(np.isnan(result[:14]))
    assert not np.isnan(result[14])


def test_stoch_rsi_range() -> None:
    n = 60
    close = 1.1 + 0.01 * np.sin(np.arange(n) / 5.0)
    rsi_vals = rsi(close, 14)
    result = stoch_rsi(rsi_vals, 14)
    valid = result[~np.isnan(result)]
    assert len(valid) > 0
    assert np.all(valid >= 0.0) and np.all(valid <= 1.0)


def test_stoch_rsi_at_local_max_is_1() -> None:
    # Construct an RSI series that hits a new high at the last index -> StochRSI = 1.
    rsi_vals = np.array([50.0, 55.0, 45.0, 60.0, 70.0])
    result = stoch_rsi(rsi_vals, 3)
    assert abs(result[-1] - 1.0) < 1e-9


def test_stoch_rsi_at_local_min_is_0() -> None:
    rsi_vals = np.array([50.0, 55.0, 45.0, 30.0, 20.0])
    result = stoch_rsi(rsi_vals, 3)
    assert abs(result[-1] - 0.0) < 1e-9


def test_stoch_rsi_flat_rsi_is_half() -> None:
    rsi_vals = np.full(10, 50.0)
    result = stoch_rsi(rsi_vals, 5)
    assert abs(result[-1] - 0.5) < 1e-9


def test_sma_basic() -> None:
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = sma(series, 5)
    assert abs(result[-1] - 3.0) < 1e-12


def test_sma_propagates_nan_gaps() -> None:
    series = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
    result = sma(series, 3)
    # window [1] (nan,3,4) contains a NaN -> should stay NaN
    assert np.isnan(result[3])


def test_atr_flat() -> None:
    flat = np.ones(20, dtype=np.float64)
    result = atr(flat, flat, flat, 14)
    assert abs(result[13]) < 1e-10


def test_build_k_cache_shape() -> None:
    n = 200
    close = 1.1 + 0.01 * np.sin(np.arange(n) / 10.0)
    k_matrix, idx = build_k_cache(close, [10, 14], [10, 14], [3, 5])
    assert k_matrix.shape == (8, n)
    assert len(idx) == 8


def test_build_k_cache_values_bounded() -> None:
    n = 200
    close = 1.1 + 0.01 * np.sin(np.arange(n) / 10.0)
    k_matrix, _ = build_k_cache(close, [14], [14], [3])
    valid = k_matrix[0][~np.isnan(k_matrix[0])]
    assert len(valid) > 0
    assert np.all(valid >= 0.0) and np.all(valid <= 1.0)


def test_build_k_cache_deduplicates_rsi() -> None:
    n = 100
    close = np.linspace(1.0, 1.1, n)
    _, idx = build_k_cache(close, [14, 14], [10], [3])
    assert len(idx) == 1
