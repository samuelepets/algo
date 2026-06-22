"""Unit tests for technical indicators (ATR, WMA, HMA)."""

from __future__ import annotations

import numpy as np

from indicators import atr, hma, hma_warmup, wma


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_wma_linear_weights() -> None:
    series = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    w = wma(series, 3)
    # (1*1 + 2*2 + 3*3) / (1+2+3) = 14/6
    assert abs(w[2] - 14.0 / 6.0) < 1e-10


def test_wma_constant() -> None:
    series = np.full(10, 2.5, dtype=np.float64)
    w = wma(series, 4)
    assert abs(w[-1] - 2.5) < 1e-12


def test_hma_tracks_linear_trend() -> None:
    n = 80
    close = np.linspace(1.0, 2.0, n)
    h = hma(close, 16)
    # HMA has low lag; on a clean linear ramp it should sit very close to price.
    assert not np.isnan(h[-1])
    assert abs(h[-1] - close[-1]) < 0.02


def test_hma_warmup_is_safe_upper_bound() -> None:
    n = 120
    close = np.linspace(1.0, 2.0, n)
    h = hma(close, 16)
    w = hma_warmup(16)
    # Early bars are NaN; HMA is defined by the (conservative) warmup index.
    assert np.isnan(h[10])
    assert not np.isnan(h[w])
    assert not np.isnan(h[-1])
