"""Unit tests for technical indicators (EMA, ATR, MACD)."""

from __future__ import annotations

import numpy as np

from indicators import atr, ema, ema_of_series, macd


def test_ema_seed_is_sma() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    e = ema(close, 3)
    assert np.isnan(e[0])
    assert np.isnan(e[1])
    assert abs(e[2] - 2.0) < 1e-10


def test_ema_recurrence() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    e = ema(close, 3)
    assert abs(e[3] - 3.0) < 1e-10
    assert abs(e[4] - 4.0) < 1e-10


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    a = atr(flat, flat, flat, 14)
    assert abs(a[13]) < 1e-10


def test_ema_of_series_skips_nan_prefix() -> None:
    series = np.array([np.nan, np.nan, 1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    out = ema_of_series(series, 3)
    # First three valid values are 1,2,3 → SMA seed 2.0 at index 4.
    assert np.isnan(out[3])
    assert abs(out[4] - 2.0) < 1e-10


def test_macd_zero_when_constant() -> None:
    close = np.full(100, 1.2, dtype=np.float64)
    macd_line, signal_line, hist = macd(close, 12, 26, 9)
    # Constant price → both EMAs equal → MACD line 0 → signal 0 → hist 0.
    assert abs(macd_line[-1]) < 1e-10
    assert abs(signal_line[-1]) < 1e-10
    assert abs(hist[-1]) < 1e-10


def test_macd_positive_on_uptrend() -> None:
    close = np.linspace(1.0, 2.0, 200, dtype=np.float64)
    macd_line, signal_line, hist = macd(close, 12, 26, 9)
    # Rising series: fast EMA above slow EMA → MACD line positive.
    assert macd_line[-1] > 0.0
    assert not np.isnan(signal_line[-1])
