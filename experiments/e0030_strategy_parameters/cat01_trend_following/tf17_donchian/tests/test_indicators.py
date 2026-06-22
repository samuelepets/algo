"""Tests for Donchian channel indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, donchian_upper, donchian_lower


def test_atr_flat():
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_donchian_upper_constant():
    high = np.full(20, 1.5, dtype=np.float64)
    out = donchian_upper(high, 10)
    assert not np.isnan(out[-1])
    assert abs(out[-1] - 1.5) < 1e-10


def test_donchian_lower_constant():
    low = np.full(20, 1.0, dtype=np.float64)
    out = donchian_lower(low, 10)
    assert not np.isnan(out[-1])
    assert abs(out[-1] - 1.0) < 1e-10


def test_donchian_upper_increasing():
    n = 30
    high = np.arange(n, dtype=np.float64)
    out = donchian_upper(high, 10)
    # At i=10, looks back at high[0..9] -> max = 9
    assert abs(out[10] - 9.0) < 1e-10


def test_donchian_warmup():
    high = np.ones(30, dtype=np.float64)
    out = donchian_upper(high, 15)
    assert np.isnan(out[0])
    assert not np.isnan(out[15])
