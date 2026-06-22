"""Unit tests for technical indicators (ATR, SMMA, shift)."""

from __future__ import annotations

import numpy as np

from indicators import atr, shifted, smma


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_smma_seed_is_sma() -> None:
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    m = smma(series, 3)
    assert np.isnan(m[1])
    assert abs(m[2] - 2.0) < 1e-10  # SMA(1,2,3)


def test_smma_converges_to_constant() -> None:
    series = np.full(50, 1.5, dtype=np.float64)
    m = smma(series, 5)
    assert abs(m[-1] - 1.5) < 1e-12


def test_shift_forward() -> None:
    line = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    out = shifted(line, 2)
    assert np.isnan(out[0]) and np.isnan(out[1])
    assert out[2] == 1.0 and out[3] == 2.0


def test_shift_zero_is_identity() -> None:
    line = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    out = shifted(line, 0)
    assert np.array_equal(out, line)
