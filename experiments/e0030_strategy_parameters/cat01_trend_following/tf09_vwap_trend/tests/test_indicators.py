"""Unit tests for technical indicators (ATR, anchored VWAP bands)."""

from __future__ import annotations

import numpy as np

from indicators import SECONDS_PER_DAY, atr, vwap_bands


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_vwap_constant_price_zero_std() -> None:
    n = 50
    px = np.full(n, 1.2, dtype=np.float64)
    ts = np.arange(n, dtype=np.int64) * 300
    v, s = vwap_bands(px, px, px, np.ones(n), ts, 0)
    assert np.allclose(v, 1.2)
    assert np.allclose(s, 0.0)


def test_vwap_std_positive_when_price_varies() -> None:
    n = 60
    close = 1.1 + 0.01 * np.sin(np.arange(n) / 3.0)
    high, low = close + 0.001, close - 0.001
    ts = np.arange(n, dtype=np.int64) * 300
    v, s = vwap_bands(high, low, close, np.ones(n), ts, 0)
    assert s[-1] > 0.0
    assert not np.isnan(v[-1])


def test_vwap_daily_reset() -> None:
    ts = np.array([0, 300, SECONDS_PER_DAY, SECONDS_PER_DAY + 300], dtype=np.int64)
    close = np.array([1.0, 1.0, 2.0, 2.0], dtype=np.float64)
    v, _ = vwap_bands(close, close, close, np.ones(4), ts, 0)
    assert abs(v[2] - 2.0) < 1e-9  # day-2 first bar resets


def test_vwap_session_anchor_shifts_boundary() -> None:
    # Two bars before 07:00 and two after; with a 07:00 anchor they fall in
    # different anchor periods, so the VWAP resets at the boundary.
    anchor = 7 * 3600
    ts = np.array([6 * 3600, 6 * 3600 + 300, 7 * 3600, 7 * 3600 + 300], dtype=np.int64)
    close = np.array([1.0, 1.0, 2.0, 2.0], dtype=np.float64)
    v, _ = vwap_bands(close, close, close, np.ones(4), ts, anchor)
    assert abs(v[2] - 2.0) < 1e-9
