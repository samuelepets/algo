"""Unit tests for MR-13 indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, build_mfi_cache, mfi


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


def test_mfi_warmup_nans() -> None:
    n = 30
    close = np.linspace(1.0, 1.1, n)
    high = close + 0.001
    low = close - 0.001
    volume = np.full(n, 100.0)
    result = mfi(high, low, close, volume, 14)
    assert np.all(np.isnan(result[:13]))
    assert not np.isnan(result[13])


def test_mfi_all_up_is_100() -> None:
    # Strictly increasing typical price -> all money flow is positive -> MFI = 100.
    n = 20
    close = np.linspace(1.0, 1.2, n)
    high = close + 0.0001
    low = close - 0.0001
    volume = np.full(n, 50.0)
    result = mfi(high, low, close, volume, 10)
    assert abs(result[-1] - 100.0) < 1e-9


def test_mfi_all_down_is_0() -> None:
    n = 20
    close = np.linspace(1.2, 1.0, n)
    high = close + 0.0001
    low = close - 0.0001
    volume = np.full(n, 50.0)
    result = mfi(high, low, close, volume, 10)
    assert abs(result[-1] - 0.0) < 1e-9


def test_mfi_flat_price_is_50() -> None:
    # No typical-price changes at all -> both sums are zero -> defined as 50.
    n = 20
    close = np.full(n, 1.1)
    high = close.copy()
    low = close.copy()
    volume = np.full(n, 50.0)
    result = mfi(high, low, close, volume, 10)
    assert abs(result[-1] - 50.0) < 1e-9


def test_mfi_known_alternating() -> None:
    # Alternating up/down typical price with equal volume -> pos and neg
    # money flow sums should be comparable; MFI should be strictly between
    # 0 and 100 (not pinned at an extreme).
    n = 20
    close = np.array([1.0 + 0.001 * ((-1) ** i) * (i % 2) for i in range(n)])
    close = 1.0 + 0.001 * np.sin(np.arange(n))
    high = close + 0.0001
    low = close - 0.0001
    volume = np.full(n, 50.0)
    result = mfi(high, low, close, volume, 10)
    assert 0.0 < result[-1] < 100.0


def test_mfi_higher_volume_on_up_moves_raises_mfi() -> None:
    n = 20
    close = 1.0 + 0.001 * np.sin(np.arange(n))
    high = close + 0.0001
    low = close - 0.0001
    volume_flat = np.full(n, 50.0)
    volume_skewed = np.where(np.diff(close, prepend=close[0]) > 0, 500.0, 50.0)
    mfi_flat = mfi(high, low, close, volume_flat, 10)
    mfi_skewed = mfi(high, low, close, volume_skewed, 10)
    assert mfi_skewed[-1] > mfi_flat[-1]


def test_build_mfi_cache_shape() -> None:
    n = 100
    close = np.linspace(1.0, 1.1, n)
    high = close + 0.001
    low = close - 0.001
    volume = np.full(n, 50.0)
    mfi_matrix, idx = build_mfi_cache(high, low, close, volume, [7, 10, 14, 20])
    assert mfi_matrix.shape == (4, n)
    assert set(idx.keys()) == {7, 10, 14, 20}


def test_build_mfi_cache_deduplicates() -> None:
    n = 60
    close = np.linspace(1.0, 1.1, n)
    high = close + 0.001
    low = close - 0.001
    volume = np.full(n, 50.0)
    mfi_matrix, idx = build_mfi_cache(high, low, close, volume, [14, 14, 20])
    assert mfi_matrix.shape[0] == 2
    assert len(idx) == 2


def test_mfi_short_series_all_nan() -> None:
    n = 5
    close = np.linspace(1.0, 1.01, n)
    high = close + 0.0001
    low = close - 0.0001
    volume = np.full(n, 50.0)
    result = mfi(high, low, close, volume, 14)
    assert np.all(np.isnan(result))
