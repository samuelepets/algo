"""Unit tests for indicators and ribbon period construction."""

from __future__ import annotations

import numpy as np

from indicators import atr, ema
from main import ribbon_periods


def test_ema_seed_is_sma() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    assert abs(ema(close, 3)[2] - 2.0) < 1e-10


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_ribbon_periods_strictly_increasing() -> None:
    for start in (3, 5, 8):
        for ratio in (1.5, 1.618, 2.0):
            for count in (4, 5, 6):
                periods = ribbon_periods(start, ratio, count)
                assert len(periods) == count
                assert all(periods[i] < periods[i + 1] for i in range(count - 1))


def test_ribbon_periods_geometric_growth() -> None:
    periods = ribbon_periods(5, 2.0, 4)
    assert periods == [5, 10, 20, 40]
