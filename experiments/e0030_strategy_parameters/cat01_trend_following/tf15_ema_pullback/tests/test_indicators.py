"""Unit tests for technical indicators (ATR, EMA)."""

from __future__ import annotations

import numpy as np

from indicators import atr, ema


def test_ema_constant() -> None:
    """EMA of a constant series must equal the constant."""
    series = np.full(30, 1.5, dtype=np.float64)
    result = ema(series, 10)
    assert not np.isnan(result[-1])
    assert abs(result[-1] - 1.5) < 1e-12


def test_ema_tracks_linear() -> None:
    """EMA should be defined at the end of a linear ramp."""
    series = np.linspace(1.0, 2.0, 100)
    result = ema(series, 20)
    assert not np.isnan(result[-1])
    # EMA lags price but should converge; just verify it's in a plausible range
    assert 1.0 < result[-1] <= 2.0


def test_atr_flat() -> None:
    """ATR of flat bars (same OHLC) should be near zero."""
    flat = np.ones(20, dtype=np.float64)
    result = atr(flat, flat, flat, 14)
    assert abs(result[13]) < 1e-10
