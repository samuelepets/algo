"""Tests for linreg_channel indicator."""

from __future__ import annotations

import numpy as np

from indicators import atr, linreg_channel


def test_atr_flat_bars():
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_linreg_constant_series():
    # Constant price -> slope=0, center=price, sigma=0
    close = np.full(50, 1.1, dtype=np.float64)
    center, sigma = linreg_channel(close, 20)
    assert not np.isnan(center[-1])
    assert abs(center[-1] - 1.1) < 1e-10
    assert sigma[-1] < 1e-10


def test_linreg_linear_trend():
    # Perfect linear trend -> sigma near 0, center near last value
    n = 100
    close = np.linspace(1.0, 2.0, n)
    center, sigma = linreg_channel(close, 30)
    assert not np.isnan(center[-1])
    assert sigma[-1] < 1e-6


def test_linreg_warmup():
    close = np.linspace(1.0, 2.0, 60)
    center, sigma = linreg_channel(close, 30)
    assert np.isnan(center[0])
    assert not np.isnan(center[29])
