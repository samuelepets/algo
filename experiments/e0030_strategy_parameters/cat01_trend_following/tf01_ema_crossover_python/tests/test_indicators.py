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


def test_atr_flat_bars() -> None:
    closes = [1.0] * 20
    high = np.array(closes, dtype=np.float64)
    low = np.array(closes, dtype=np.float64)
    close = np.array(closes, dtype=np.float64)
    a = atr(high, low, close, 14)
    assert abs(a[13]) < 1e-10
