"""Unit tests for technical indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, ema


def _bars_from_closes(closes: list[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    close = np.array(closes, dtype=np.float64)
    high = close * 1.001
    low = close * 0.999
    return high, low, close


def test_ema_seed_is_sma() -> None:
    closes = [1.0, 2.0, 3.0, 4.0, 5.0]
    _, _, close = _bars_from_closes(closes)
    e = ema(close, 3)
    assert np.isnan(e[0])
    assert np.isnan(e[1])
    assert abs(e[2] - 2.0) < 1e-10


def test_ema_recurrence() -> None:
    closes = [1.0, 2.0, 3.0, 4.0, 5.0]
    _, _, close = _bars_from_closes(closes)
    e = ema(close, 3)
    assert abs(e[3] - 3.0) < 1e-10
    assert abs(e[4] - 4.0) < 1e-10


def test_ema_nan_for_short_series() -> None:
    close = np.array([1.0, 2.0], dtype=np.float64)
    e = ema(close, 5)
    assert all(np.isnan(e))


def test_atr_flat_bars() -> None:
    closes = [1.0] * 20
    high = np.array(closes, dtype=np.float64)
    low = np.array(closes, dtype=np.float64)
    close = np.array(closes, dtype=np.float64)
    a = atr(high, low, close, 14)
    assert abs(a[13]) < 1e-10


def test_atr_positive_for_volatile_bars() -> None:
    rng = np.random.default_rng(42)
    n = 50
    close = 1.1 + rng.standard_normal(n) * 0.001
    high = close + rng.uniform(0.0005, 0.002, n)
    low = close - rng.uniform(0.0005, 0.002, n)
    a = atr(high, low, close, 14)
    assert a[13] > 0.0
    assert all(v > 0.0 for v in a[13:])
