"""Unit tests for MR-19 indicators."""

from __future__ import annotations

import numpy as np

from indicators import (
    atr,
    build_roc_rank_cache,
    build_rsi_cache,
    build_sma_cache,
    build_ud_rsi_cache,
    roc_percentile_rank,
    rsi,
    sma,
    streak,
)


def test_rsi_all_up_is_100() -> None:
    close = np.linspace(1.0, 1.2, 20)
    result = rsi(close, 3)
    assert abs(result[-1] - 100.0) < 1e-9


def test_rsi_all_down_is_0() -> None:
    close = np.linspace(1.2, 1.0, 20)
    result = rsi(close, 3)
    assert abs(result[-1] - 0.0) < 1e-9


def test_streak_counts_consecutive_moves() -> None:
    close = np.array([1.0, 1.1, 1.2, 1.3, 1.15, 1.05, 1.2])
    result = streak(close)
    # up, up, up -> +1, +2, +3; then down, down -> -1, -2; then up -> +1
    assert result[1] == 1.0
    assert result[2] == 2.0
    assert result[3] == 3.0
    assert result[4] == -1.0
    assert result[5] == -2.0
    assert result[6] == 1.0


def test_streak_flat_bar_resets_to_zero() -> None:
    close = np.array([1.0, 1.1, 1.1, 1.2])
    result = streak(close)
    assert result[1] == 1.0
    assert result[2] == 0.0
    assert result[3] == 1.0


def test_streak_first_bar_is_zero() -> None:
    close = np.array([1.0, 1.1])
    result = streak(close)
    assert result[0] == 0.0


def test_roc_percentile_rank_current_is_max() -> None:
    # Strictly increasing 1-bar returns (not just strictly increasing
    # price -- equal absolute price steps give DECREASING relative returns
    # as the base grows) -> the most recent ROC is the largest in any
    # trailing window -> percentile rank = 100.
    n = 30
    returns = np.linspace(0.001, 0.02, n - 1)
    close = np.empty(n)
    close[0] = 1.0
    for i in range(1, n):
        close[i] = close[i - 1] * (1.0 + returns[i - 1])
    result = roc_percentile_rank(close, 10)
    assert abs(result[-1] - 100.0) < 1e-9


def test_roc_percentile_rank_bounded() -> None:
    n = 60
    close = 1.1 + 0.01 * np.sin(np.arange(n) / 5.0)
    result = roc_percentile_rank(close, 20)
    valid = result[~np.isnan(result)]
    assert len(valid) > 0
    assert np.all(valid > 0.0) and np.all(valid <= 100.0)


def test_roc_percentile_rank_warmup_nans() -> None:
    close = np.linspace(1.0, 1.1, 30)
    result = roc_percentile_rank(close, 20)
    assert np.all(np.isnan(result[:20]))
    assert not np.isnan(result[20])


def test_sma_basic() -> None:
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = sma(series, 5)
    assert abs(result[-1] - 3.0) < 1e-12


def test_atr_flat() -> None:
    flat = np.ones(20, dtype=np.float64)
    result = atr(flat, flat, flat, 14)
    assert abs(result[13]) < 1e-10


def test_build_rsi_cache_shape() -> None:
    n = 100
    close = np.linspace(1.0, 1.1, n)
    matrix, idx = build_rsi_cache(close, [2, 3, 4])
    assert matrix.shape == (3, n)
    assert set(idx.keys()) == {2, 3, 4}


def test_build_ud_rsi_cache_shape() -> None:
    n = 100
    close = 1.1 + 0.01 * np.sin(np.arange(n) / 3.0)
    matrix, idx = build_ud_rsi_cache(close, [2, 3])
    assert matrix.shape == (2, n)
    assert set(idx.keys()) == {2, 3}


def test_build_roc_rank_cache_shape() -> None:
    n = 300
    close = 1.1 + 0.01 * np.sin(np.arange(n) / 5.0)
    matrix, idx = build_roc_rank_cache(close, [50, 100, 200])
    assert matrix.shape == (3, n)
    assert set(idx.keys()) == {50, 100, 200}


def test_build_sma_cache_shape() -> None:
    n = 300
    close = np.linspace(1.0, 1.1, n)
    matrix, idx = build_sma_cache(close, [100, 200])
    assert matrix.shape == (2, n)
    assert set(idx.keys()) == {100, 200}
