"""Tests for ROC indicator."""
from __future__ import annotations
import numpy as np
from indicators import atr, roc


def test_atr_flat():
    flat = np.ones(20, dtype=np.float64)
    assert abs(atr(flat, flat, flat, 14)[13]) < 1e-10


def test_roc_constant():
    close = np.full(20, 1.1, dtype=np.float64)
    r = roc(close, 5)
    assert not np.isnan(r[-1])
    assert abs(r[-1]) < 1e-10


def test_roc_doubling():
    # Price doubles over 10 bars: ROC(10) = 100%
    close = np.ones(20, dtype=np.float64)
    close[10:] = 2.0
    r = roc(close, 10)
    assert not np.isnan(r[-1])
    assert abs(r[-1] - 100.0) < 1e-8


def test_roc_warmup():
    close = np.linspace(1.0, 1.5, 30)
    r = roc(close, 10)
    assert np.isnan(r[0])
    assert not np.isnan(r[10])
