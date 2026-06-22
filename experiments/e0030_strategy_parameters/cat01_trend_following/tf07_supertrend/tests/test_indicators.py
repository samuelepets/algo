"""Unit tests for technical indicators (EMA, ATR, SuperTrend)."""

from __future__ import annotations

import numpy as np

from indicators import atr, ema, supertrend


def test_ema_seed_is_sma() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    e = ema(close, 3)
    assert abs(e[2] - 2.0) < 1e-10


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    a = atr(flat, flat, flat, 14)
    assert abs(a[13]) < 1e-10


def test_supertrend_uptrend_is_bullish() -> None:
    n = 120
    close = np.linspace(1.0, 2.0, n)
    high = close + 0.002
    low = close - 0.002
    a = atr(high, low, close, 10)
    st_line, direction = supertrend(high, low, close, a, 3.0)
    assert direction[-1] == 1
    # In an uptrend the SuperTrend line (lower band) sits below price.
    assert st_line[-1] < close[-1]


def test_supertrend_downtrend_is_bearish() -> None:
    n = 120
    close = np.linspace(2.0, 1.0, n)
    high = close + 0.002
    low = close - 0.002
    a = atr(high, low, close, 10)
    st_line, direction = supertrend(high, low, close, a, 3.0)
    assert direction[-1] == -1
    assert st_line[-1] > close[-1]


def test_supertrend_flips_on_reversal() -> None:
    up = np.linspace(1.0, 1.5, 80)
    down = np.linspace(1.5, 1.0, 80)
    close = np.concatenate([up, down])
    high = close + 0.002
    low = close - 0.002
    a = atr(high, low, close, 10)
    _, direction = supertrend(high, low, close, a, 2.0)
    # Direction should contain both regimes.
    assert np.any(direction == 1)
    assert np.any(direction == -1)
