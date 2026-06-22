"""Unit tests for technical indicators (EMA, Parabolic SAR)."""

from __future__ import annotations

import numpy as np

from indicators import ema, parabolic_sar


def test_ema_seed_is_sma() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    assert abs(ema(close, 3)[2] - 2.0) < 1e-10


def test_sar_below_price_in_uptrend() -> None:
    n = 100
    close = np.linspace(1.0, 2.0, n)
    high, low = close + 0.002, close - 0.002
    sar, direction = parabolic_sar(high, low, 0.02, 0.02, 0.20)
    assert direction[-1] == 1
    assert sar[-1] < close[-1]


def test_sar_above_price_in_downtrend() -> None:
    n = 100
    close = np.linspace(2.0, 1.0, n)
    high, low = close + 0.002, close - 0.002
    sar, direction = parabolic_sar(high, low, 0.02, 0.02, 0.20)
    assert direction[-1] == -1
    assert sar[-1] > close[-1]


def test_sar_flips_on_reversal() -> None:
    up = np.linspace(1.0, 1.5, 80)
    down = np.linspace(1.5, 1.0, 80)
    close = np.concatenate([up, down])
    high, low = close + 0.002, close - 0.002
    _, direction = parabolic_sar(high, low, 0.02, 0.02, 0.20)
    assert np.any(direction == 1)
    assert np.any(direction == -1)
