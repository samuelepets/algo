"""Unit tests for the Ichimoku midpoint indicator."""

from __future__ import annotations

import numpy as np

from indicators import midpoint


def test_midpoint_warmup_nan() -> None:
    high = np.arange(1.0, 11.0)
    low = high - 0.5
    mid = midpoint(high, low, 5)
    assert np.isnan(mid[3])
    assert not np.isnan(mid[4])


def test_midpoint_value() -> None:
    high = np.array([1.0, 3.0, 2.0, 5.0, 4.0], dtype=np.float64)
    low = np.array([0.5, 1.0, 1.5, 2.0, 3.0], dtype=np.float64)
    mid = midpoint(high, low, 5)
    # max high = 5, min low = 0.5 → midpoint 2.75
    assert abs(mid[4] - 2.75) < 1e-10


def test_midpoint_constant() -> None:
    px = np.full(20, 1.2, dtype=np.float64)
    mid = midpoint(px, px, 9)
    assert abs(mid[-1] - 1.2) < 1e-12
