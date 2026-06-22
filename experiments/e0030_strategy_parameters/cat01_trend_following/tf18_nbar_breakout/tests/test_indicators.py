"""Tests for N-bar breakout indicators."""

from __future__ import annotations

import numpy as np

from indicators import atr, rolling_max, rolling_min, rolling_vol_avg


def test_atr_flat():
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_rolling_max_constant():
    high = np.full(20, 1.5, dtype=np.float64)
    out = rolling_max(high, 10)
    assert not np.isnan(out[-1])
    assert abs(out[-1] - 1.5) < 1e-10


def test_rolling_min_constant():
    low = np.full(20, 0.9, dtype=np.float64)
    out = rolling_min(low, 10)
    assert not np.isnan(out[-1])
    assert abs(out[-1] - 0.9) < 1e-10


def test_rolling_max_increasing():
    n = 25
    high = np.arange(n, dtype=np.float64)
    out = rolling_max(high, 10)
    # At i=10: looks at high[0..9] -> max = 9
    assert abs(out[10] - 9.0) < 1e-10


def test_rolling_vol_avg_constant():
    vol = np.full(20, 2.0, dtype=np.float64)
    out = rolling_vol_avg(vol, 10)
    assert not np.isnan(out[-1])
    assert abs(out[-1] - 2.0) < 1e-10
