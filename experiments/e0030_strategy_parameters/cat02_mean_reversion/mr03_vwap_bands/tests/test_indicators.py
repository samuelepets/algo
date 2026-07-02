"""Unit tests for MR-03 indicators."""

from __future__ import annotations

import numpy as np

from indicators import RESET_ANCHOR_SECS, atr, build_vwap_cache, vwap_bands


def test_atr_flat() -> None:
    flat = np.ones(20, dtype=np.float64)
    result = atr(flat, flat, flat, 14)
    assert abs(result[13]) < 1e-10


def test_atr_warmup_nans() -> None:
    h = np.ones(20, dtype=np.float64) * 1.1
    lo = np.ones(20, dtype=np.float64) * 0.9
    c = np.ones(20, dtype=np.float64)
    result = atr(h, lo, c, 14)
    assert np.all(np.isnan(result[:13]))
    assert not np.isnan(result[13])


def test_vwap_first_bar_equals_typical_price() -> None:
    # Single bar: VWAP must equal the typical price of that bar, std=0.
    ts = np.array([0], dtype=np.int64)
    h = np.array([1.10], dtype=np.float64)
    lo = np.array([1.08], dtype=np.float64)
    c = np.array([1.09], dtype=np.float64)
    v = np.array([100.0], dtype=np.float64)
    vwap, std = vwap_bands(ts, h, lo, c, v, 0)
    tp = (1.10 + 1.08 + 1.09) / 3.0
    assert abs(vwap[0] - tp) < 1e-12
    assert abs(std[0]) < 1e-12


def test_vwap_known_two_bar_session() -> None:
    # Two bars in the same session (both at ts=0 and ts=100, well within
    # one 86400s daily bucket). Hand-computed VWAP and running std.
    ts = np.array([0, 100], dtype=np.int64)
    h = np.array([1.10, 1.20], dtype=np.float64)
    lo = np.array([1.08, 1.10], dtype=np.float64)
    c = np.array([1.09, 1.15], dtype=np.float64)
    vol = np.array([10.0, 30.0], dtype=np.float64)
    vwap, std = vwap_bands(ts, h, lo, c, vol, 0)

    tp0 = (1.10 + 1.08 + 1.09) / 3.0
    tp1 = (1.20 + 1.10 + 1.15) / 3.0
    expected_vwap1 = (tp0 * 10.0 + tp1 * 30.0) / 40.0
    assert abs(vwap[0] - tp0) < 1e-12
    assert abs(vwap[1] - expected_vwap1) < 1e-9

    dev0 = tp0 - tp0  # vwap[0] == tp0
    dev1 = tp1 - expected_vwap1
    mean_dev = (dev0 + dev1) / 2.0
    var = ((dev0 - mean_dev) ** 2 + (dev1 - mean_dev) ** 2) / 2.0
    assert abs(std[1] - var**0.5) < 1e-9


def test_vwap_session_reset_daily() -> None:
    # Bar just before and just after a daily boundary (86400s) must reset
    # the running accumulators.
    ts = np.array([86399, 86400], dtype=np.int64)
    h = np.array([1.10, 2.00], dtype=np.float64)
    lo = np.array([1.08, 1.90], dtype=np.float64)
    c = np.array([1.09, 1.95], dtype=np.float64)
    vol = np.array([10.0, 20.0], dtype=np.float64)
    vwap, std = vwap_bands(ts, h, lo, c, vol, 0)
    tp1 = (2.00 + 1.90 + 1.95) / 3.0
    assert abs(vwap[1] - tp1) < 1e-12  # fresh session -> vwap == own TP
    assert abs(std[1]) < 1e-12


def test_vwap_session_reset_london_offset() -> None:
    # With an 8h anchor offset, a bar at ts=8*3600 (08:00) starts a new
    # session even though ts=8*3600-1 is still in the prior session.
    offset = RESET_ANCHOR_SECS["session_london"]
    ts = np.array([8 * 3600 - 1, 8 * 3600], dtype=np.int64)
    h = np.array([1.10, 2.00], dtype=np.float64)
    lo = np.array([1.08, 1.90], dtype=np.float64)
    c = np.array([1.09, 1.95], dtype=np.float64)
    vol = np.array([10.0, 20.0], dtype=np.float64)
    vwap, std = vwap_bands(ts, h, lo, c, vol, offset)
    tp1 = (2.00 + 1.90 + 1.95) / 3.0
    assert abs(vwap[1] - tp1) < 1e-12
    assert abs(std[1]) < 1e-12


def test_vwap_zero_volume_falls_back_to_typical_price() -> None:
    ts = np.array([0, 60], dtype=np.int64)
    h = np.array([1.10, 1.12], dtype=np.float64)
    lo = np.array([1.08, 1.10], dtype=np.float64)
    c = np.array([1.09, 1.11], dtype=np.float64)
    vol = np.array([0.0, 0.0], dtype=np.float64)
    vwap, _std = vwap_bands(ts, h, lo, c, vol, 0)
    tp1 = (1.12 + 1.10 + 1.11) / 3.0
    assert abs(vwap[1] - tp1) < 1e-12


def test_build_vwap_cache_shape() -> None:
    n = 500
    ts = np.arange(n, dtype=np.int64) * 300
    h = np.linspace(1.0, 1.1, n)
    lo = h - 0.001
    c = (h + lo) / 2.0
    vol = np.full(n, 5.0)
    vwap_m, std_m, idx = build_vwap_cache(ts, h, lo, c, vol, ["daily", "session_london", "session_ny"])
    assert vwap_m.shape == (3, n)
    assert std_m.shape == (3, n)
    assert set(idx.keys()) == {"daily", "session_london", "session_ny"}


def test_build_vwap_cache_deduplicates() -> None:
    n = 200
    ts = np.arange(n, dtype=np.int64) * 300
    h = np.linspace(1.0, 1.1, n)
    lo = h - 0.001
    c = (h + lo) / 2.0
    vol = np.full(n, 5.0)
    vwap_m, _std_m, idx = build_vwap_cache(ts, h, lo, c, vol, ["daily", "daily", "session_ny"])
    assert vwap_m.shape[0] == 2
    assert len(idx) == 2


def test_std_grows_within_session_when_deviation_varies() -> None:
    # Alternating typical price around the session mean should build up a
    # positive running std across bars within the same session.
    n = 10
    ts = np.arange(n, dtype=np.int64) * 60
    c = np.array([1.10, 1.08, 1.12, 1.07, 1.13, 1.06, 1.14, 1.05, 1.15, 1.04])
    h = c + 0.001
    lo = c - 0.001
    vol = np.full(n, 10.0)
    _vwap, std = vwap_bands(ts, h, lo, c, vol, 0)
    assert std[0] == 0.0
    assert std[-1] > std[1]
