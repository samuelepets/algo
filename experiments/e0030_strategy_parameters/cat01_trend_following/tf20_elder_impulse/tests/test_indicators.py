"""Tests for Elder Impulse indicators."""

from __future__ import annotations

import numpy as np

from indicators import (
    COLOR_GREEN,
    COLOR_NEUTRAL,
    atr,
    elder_impulse_colors,
    ema,
    macd_histogram,
)


def test_atr_flat():
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_ema_constant():
    series = np.full(20, 1.1, dtype=np.float64)
    out = ema(series, 10)
    assert not np.isnan(out[-1])
    assert abs(out[-1] - 1.1) < 1e-10


def test_macd_histogram_warmup():
    close = np.linspace(1.0, 1.5, 100)
    h = macd_histogram(close, 12, 26, 9)
    assert np.isnan(h[0])
    assert not np.isnan(h[-1])


def test_elder_impulse_all_rising():
    n = 60
    # Steadily rising price: EMA rising + histogram rising → all Green after warmup
    close = np.linspace(1.0, 2.0, n)
    e_vals = ema(close, 10)
    h_vals = macd_histogram(close, 8, 21, 7)
    colors = elder_impulse_colors(e_vals, h_vals)
    # After warmup, most bars should be Green
    valid_colors = colors[40:]
    assert COLOR_GREEN in valid_colors


def test_elder_impulse_neutral_on_nan():
    n = 10
    e_vals = np.full(n, np.nan, dtype=np.float64)
    h_vals = np.full(n, np.nan, dtype=np.float64)
    colors = elder_impulse_colors(e_vals, h_vals)
    assert all(colors[i] == COLOR_NEUTRAL for i in range(n))
