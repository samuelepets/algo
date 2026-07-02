"""Unit tests for MR-04 indicators."""

from __future__ import annotations

import numpy as np

from indicators import (
    atr,
    build_zscore_cache,
    log_returns,
    rolling_std,
    sma,
    zscore_close_detrended,
    zscore_log_return,
)


def test_sma_constant() -> None:
    series = np.full(30, 2.0, dtype=np.float64)
    result = sma(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 2.0) < 1e-12


def test_sma_warmup_nans() -> None:
    result = sma(np.ones(20, dtype=np.float64), 10)
    assert np.all(np.isnan(result[:9]))
    assert not np.isnan(result[9])


def test_rolling_std_constant() -> None:
    series = np.full(30, 3.0, dtype=np.float64)
    result = rolling_std(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1]) < 1e-12


def test_rolling_std_known() -> None:
    # series [0, 1, 2, 3, 4]: mean=2, var=(4+1+0+1+4)/5=2, std=sqrt(2)
    series = np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    result = rolling_std(series, 5)
    assert abs(result[4] - 2.0 ** 0.5) < 1e-12


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


def test_log_returns_known() -> None:
    close = np.array([1.0, 2.0, 4.0], dtype=np.float64)
    result = log_returns(close)
    assert np.isnan(result[0])
    assert abs(result[1] - np.log(2.0)) < 1e-12
    assert abs(result[2] - np.log(2.0)) < 1e-12


def test_log_returns_warmup_nan() -> None:
    close = np.linspace(1.0, 1.1, 50)
    result = log_returns(close)
    assert np.isnan(result[0])
    assert not np.isnan(result[1])


def test_zscore_log_return_warmup_nans() -> None:
    rng = np.random.default_rng(42)
    close = 1.1 + np.cumsum(rng.normal(0.0, 0.001, 300))
    close = np.abs(close) + 1.0
    window = 20
    z = zscore_log_return(close, window)
    assert np.all(np.isnan(z[: window - 1]))
    assert not np.isnan(z[window - 1])


def test_zscore_close_detrended_warmup_nans() -> None:
    close = np.linspace(1.0, 1.2, 300)
    window = 20
    z = zscore_close_detrended(close, window)
    assert np.all(np.isnan(z[: window - 1]))
    assert not np.isnan(z[window - 1])


def test_zscore_close_detrended_spike_positive() -> None:
    # A single sharp spike above the recent flat mean should show a strongly
    # positive z-score exactly at the spike bar.
    n = 100
    close = np.full(n, 1.0, dtype=np.float64)
    close[80] = 1.05
    z = zscore_close_detrended(close, 20)
    assert z[80] > 2.0


def test_zscore_log_return_spike_positive() -> None:
    # A single sharp positive return embedded in an otherwise flat series
    # should show a strongly positive return z-score at that bar.
    n = 100
    close = np.full(n, 1.0, dtype=np.float64)
    close[80] = 1.05
    close[81:] = 1.05
    z = zscore_log_return(close, 20)
    assert z[80] > 2.0


def test_build_zscore_cache_shape() -> None:
    close = np.linspace(1.0, 1.1, 400)
    lr_matrix, cd_matrix, idx = build_zscore_cache(close, [20, 30, 60])
    assert lr_matrix.shape == (3, 400)
    assert cd_matrix.shape == (3, 400)
    assert set(idx.keys()) == {20, 30, 60}


def test_build_zscore_cache_deduplicates() -> None:
    close = np.linspace(1.0, 1.1, 300)
    lr_matrix, cd_matrix, idx = build_zscore_cache(close, [30, 30, 20])
    assert lr_matrix.shape[0] == 2
    assert cd_matrix.shape[0] == 2
    assert len(idx) == 2
