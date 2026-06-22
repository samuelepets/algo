"""Unit tests for technical indicators (EMA, ATR, SuperTrend, ADX, VWAP)."""

from __future__ import annotations

import numpy as np

from indicators import SECONDS_PER_DAY, adx_dmi, atr, ema, supertrend, vwap_daily


def test_ema_seed_is_sma() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    assert abs(ema(close, 3)[2] - 2.0) < 1e-10


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_supertrend_uptrend_bullish() -> None:
    n = 120
    close = np.linspace(1.0, 2.0, n)
    high, low = close + 0.002, close - 0.002
    a = atr(high, low, close, 10)
    _, direction = supertrend(high, low, close, a, 3.0)
    assert direction[-1] == 1


def test_adx_uptrend_plus_di_dominates() -> None:
    n = 120
    close = np.linspace(1.0, 2.0, n)
    high, low = close + 0.001, close - 0.001
    _, pdi, mdi = adx_dmi(high, low, close, 14)
    assert pdi[-1] > mdi[-1]


def test_vwap_constant_price() -> None:
    n = 50
    close = np.full(n, 1.2, dtype=np.float64)
    high = np.full(n, 1.2, dtype=np.float64)
    low = np.full(n, 1.2, dtype=np.float64)
    vol = np.ones(n, dtype=np.float64)
    ts = np.arange(n, dtype=np.int64) * 300
    v = vwap_daily(high, low, close, vol, ts)
    assert np.allclose(v, 1.2)


def test_vwap_resets_each_day() -> None:
    # Two days; day 1 price 1.0, day 2 price 2.0. After reset VWAP tracks day 2.
    ts = np.array([0, 300, SECONDS_PER_DAY, SECONDS_PER_DAY + 300], dtype=np.int64)
    close = np.array([1.0, 1.0, 2.0, 2.0], dtype=np.float64)
    v = vwap_daily(close, close, close, np.ones(4), ts)
    assert abs(v[1] - 1.0) < 1e-9
    assert abs(v[2] - 2.0) < 1e-9  # reset → first bar of day 2 equals its own price


def test_vwap_zero_volume_falls_back_to_typical() -> None:
    n = 10
    close = np.linspace(1.0, 1.1, n)
    high, low = close + 0.01, close - 0.01
    vol = np.zeros(n, dtype=np.float64)
    ts = np.arange(n, dtype=np.int64) * 300
    v = vwap_daily(high, low, close, vol, ts)
    tp = (high + low + close) / 3.0
    assert np.allclose(v, tp)
