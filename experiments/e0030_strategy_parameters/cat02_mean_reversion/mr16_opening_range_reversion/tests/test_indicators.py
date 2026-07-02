"""Unit tests for MR-16 indicators."""

from __future__ import annotations

import numpy as np
import pytest

from indicators import (
    atr,
    build_or_daily_cache,
    build_or_matrix,
    compute_daily_or,
    expand_or_to_bars,
)

SEC_PER_DAY = 86400


def _ts_for(day: int, minute: int) -> int:
    return day * SEC_PER_DAY + minute * 60


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


def test_compute_daily_or_known_window() -> None:
    # Session window: [480, 490) i.e. 08:00-08:10 EET.
    ts = np.array(
        [
            _ts_for(0, 479),  # before window
            _ts_for(0, 480),  # in window
            _ts_for(0, 485),  # in window
            _ts_for(0, 489),  # in window (last minute of window)
            _ts_for(0, 490),  # window end is exclusive -> outside
            _ts_for(0, 500),  # outside
            _ts_for(1, 1000),  # day 1, no bar in window at all
        ],
        dtype=np.int64,
    )
    high = np.array([1.0, 1.05, 1.10, 1.02, 2.0, 3.0, 5.0], dtype=np.float64)
    low = np.array([0.9, 0.95, 0.90, 0.98, 1.9, -1.0, 4.0], dtype=np.float64)

    days, orh, orl = compute_daily_or(ts, high, low, 480, 10)

    # Only day 0 has bars inside the window -> day 1 is skipped entirely.
    assert list(days) == [0]
    assert orh[0] == pytest.approx(1.10)
    assert orl[0] == pytest.approx(0.90)


def test_compute_daily_or_no_bars_in_any_window() -> None:
    ts = np.array([_ts_for(0, 0), _ts_for(0, 700)], dtype=np.int64)
    high = np.array([1.0, 1.0], dtype=np.float64)
    low = np.array([1.0, 1.0], dtype=np.float64)
    days, orh, orl = compute_daily_or(ts, high, low, 480, 10)
    assert len(days) == 0
    assert len(orh) == 0
    assert len(orl) == 0


def test_expand_or_to_bars_matches_and_nans_missing_days() -> None:
    ts = np.array(
        [
            _ts_for(0, 479),
            _ts_for(0, 480),
            _ts_for(0, 500),
            _ts_for(1, 1000),
        ],
        dtype=np.int64,
    )
    unique_days = np.array([0], dtype=np.int64)
    orh_day = np.array([1.10], dtype=np.float64)
    orl_day = np.array([0.90], dtype=np.float64)

    orh_bar, orl_bar = expand_or_to_bars(ts, unique_days, orh_day, orl_day)

    assert orh_bar[0] == pytest.approx(1.10)
    assert orl_bar[0] == pytest.approx(0.90)
    assert orh_bar[2] == pytest.approx(1.10)  # same day 0, later bar
    assert np.isnan(orh_bar[3])  # day 1 absent -> NaN
    assert np.isnan(orl_bar[3])


def test_expand_or_to_bars_empty_days() -> None:
    ts = np.array([_ts_for(0, 0), _ts_for(0, 500)], dtype=np.int64)
    unique_days = np.empty(0, dtype=np.int64)
    orh_day = np.empty(0, dtype=np.float64)
    orl_day = np.empty(0, dtype=np.float64)
    orh_bar, orl_bar = expand_or_to_bars(ts, unique_days, orh_day, orl_day)
    assert np.all(np.isnan(orh_bar))
    assert np.all(np.isnan(orl_bar))


def test_build_or_daily_cache_shapes() -> None:
    n = 3000
    ts = np.arange(n, dtype=np.int64) * 60  # 1-min bars starting at epoch 0
    high = np.full(n, 1.1, dtype=np.float64)
    low = np.full(n, 0.9, dtype=np.float64)
    cache = build_or_daily_cache(ts, high, low)
    # 2 sessions x 4 durations = 8 combos
    assert len(cache) == 8
    assert ("london", 5) in cache
    assert ("ny", 30) in cache


def test_build_or_matrix_row_index_and_shape() -> None:
    n = 3000
    ts = np.arange(n, dtype=np.int64) * 60
    high = np.full(n, 1.1, dtype=np.float64)
    low = np.full(n, 0.9, dtype=np.float64)
    cache = build_or_daily_cache(ts, high, low)
    orh_matrix, orl_matrix, row_index = build_or_matrix(ts, cache)
    assert orh_matrix.shape == (8, n)
    assert orl_matrix.shape == (8, n)
    assert len(row_index) == 8
    # Constant high/low -> OR high == low == 1.1/0.9 wherever valid.
    row = row_index[("london", 5)]
    valid = ~np.isnan(orh_matrix[row])
    assert valid.any()
    assert np.all(orh_matrix[row][valid] == pytest.approx(1.1))
    assert np.all(orl_matrix[row][valid] == pytest.approx(0.9))


def test_or_window_respects_session_start() -> None:
    # London window starts at minute 480; a bar at minute 300 must not count.
    ts = np.array([_ts_for(0, 300), _ts_for(0, 481)], dtype=np.int64)
    high = np.array([9.0, 1.5], dtype=np.float64)
    low = np.array([9.0, 1.4], dtype=np.float64)
    days, orh, orl = compute_daily_or(ts, high, low, 480, 10)
    assert len(days) == 1
    assert orh[0] == pytest.approx(1.5)
    assert orl[0] == pytest.approx(1.4)
