"""Unit tests for technical indicators (EMA, ATR, RSI)."""

from __future__ import annotations

import numpy as np

from indicators import atr, ema, rsi


def test_ema_seed_is_sma() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    e = ema(close, 3)
    assert np.isnan(e[0])
    assert abs(e[2] - 2.0) < 1e-10


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    a = atr(flat, flat, flat, 14)
    assert abs(a[13]) < 1e-10


def test_rsi_all_gains_is_100() -> None:
    close = np.arange(1.0, 40.0, dtype=np.float64)  # strictly increasing
    r = rsi(close, 14)
    assert np.isnan(r[13])
    assert abs(r[14] - 100.0) < 1e-9
    assert abs(r[-1] - 100.0) < 1e-9


def test_rsi_all_losses_is_zero() -> None:
    close = np.arange(40.0, 1.0, -1.0, dtype=np.float64)  # strictly decreasing
    r = rsi(close, 14)
    assert abs(r[-1] - 0.0) < 1e-9


def test_rsi_midrange_for_alternating() -> None:
    rng = np.random.default_rng(7)
    close = 1.1 + np.cumsum(rng.standard_normal(200) * 0.001)
    r = rsi(close, 14)
    valid = r[~np.isnan(r)]
    assert valid.size > 0
    assert np.all(valid >= 0.0) and np.all(valid <= 100.0)
