"""Unit tests for data loading and resampling."""

from __future__ import annotations

import numpy as np

from data import BarArrays, resample


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


def test_resample_5min_two_buckets() -> None:
    bars = _make_bars(6, step_secs=60)
    out = resample(bars, 5)
    assert out.ts.size == 2
    assert out.open[0] == bars.open[0]
    assert out.close[0] == bars.close[4]
    assert out.open[1] == bars.open[5]


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
