"""Unit tests for algo_shared.data."""

from __future__ import annotations

import numpy as np
import pytest

from algo_shared.data import BarArrays, resample, ts_range, year_start_ts


def _make_bars(n: int, step_secs: int = 60) -> BarArrays:
    ts = np.arange(n, dtype=np.int64) * step_secs
    price = 1.0 + np.arange(n, dtype=np.float64) * 0.01
    return BarArrays(
        ts=ts,
        open=price,
        high=price + 0.01,
        low=price - 0.01,
        close=price + 0.005,
        volume=np.ones(n, dtype=np.float64),
    )


def test_year_start_ts_2003() -> None:
    ts = year_start_ts(2003)
    assert ts == 1041379200  # 2003-01-01 00:00:00 UTC


def test_year_start_ts_monotonic() -> None:
    ts_seq = [year_start_ts(y) for y in range(2003, 2026)]
    assert all(a < b for a, b in zip(ts_seq, ts_seq[1:]))


def test_ts_range_basic() -> None:
    ts = np.array([0, 60, 120, 180, 240], dtype=np.int64)
    s, e = ts_range(ts, 60, 180)
    assert s == 1
    assert e == 3


def test_ts_range_full() -> None:
    ts = np.array([0, 60, 120], dtype=np.int64)
    s, e = ts_range(ts, 0, 999)
    assert s == 0
    assert e == 3


def test_bar_arrays_frozen() -> None:
    bars = _make_bars(10)
    with pytest.raises((AttributeError, TypeError)):
        bars.ts = np.zeros(10, dtype=np.int64)  # type: ignore[misc]


def test_resample_5min_two_buckets() -> None:
    bars = _make_bars(6, step_secs=60)
    out = resample(bars, 5)
    assert out.ts.size == 2
    assert out.open[0] == bars.open[0]
    assert out.close[0] == bars.close[4]
    assert out.open[1] == bars.open[5]


def test_resample_aggregates_high_low() -> None:
    bars = _make_bars(5, step_secs=60)
    out = resample(bars, 5)
    assert out.ts.size == 1
    assert out.high[0] == pytest.approx(bars.high.max())
    assert out.low[0] == pytest.approx(bars.low.min())


def test_resample_volume_sum() -> None:
    bars = _make_bars(5, step_secs=60)
    out = resample(bars, 5)
    assert out.volume[0] == pytest.approx(bars.volume.sum())


def test_resample_empty() -> None:
    empty = BarArrays(
        ts=np.empty(0, dtype=np.int64),
        open=np.empty(0),
        high=np.empty(0),
        low=np.empty(0),
        close=np.empty(0),
        volume=np.empty(0),
    )
    out = resample(empty, 5)
    assert out.ts.size == 0
