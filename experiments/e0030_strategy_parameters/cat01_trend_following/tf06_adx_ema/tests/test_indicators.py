"""Unit tests for technical indicators (EMA, ATR, ADX/DMI)."""

from __future__ import annotations

import numpy as np

from indicators import adx_dmi, atr, ema


def test_ema_seed_is_sma() -> None:
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    e = ema(close, 3)
    assert abs(e[2] - 2.0) < 1e-10


def test_atr_flat_bars() -> None:
    flat = np.ones(20, dtype=np.float64)
    a = atr(flat, flat, flat, 14)
    assert abs(a[13]) < 1e-10


def test_adx_strong_uptrend_plus_di_dominates() -> None:
    n = 120
    close = np.linspace(1.0, 2.0, n)
    high = close + 0.001
    low = close - 0.001
    adx, plus_di, minus_di = adx_dmi(high, low, close, 14)
    # In a clean uptrend +DI should dominate -DI and ADX should be high.
    assert plus_di[-1] > minus_di[-1]
    assert adx[-1] > 25.0


def test_adx_downtrend_minus_di_dominates() -> None:
    n = 120
    close = np.linspace(2.0, 1.0, n)
    high = close + 0.001
    low = close - 0.001
    _, plus_di, minus_di = adx_dmi(high, low, close, 14)
    assert minus_di[-1] > plus_di[-1]


def test_adx_warmup_is_nan() -> None:
    n = 120
    close = np.linspace(1.0, 2.0, n)
    high = close + 0.001
    low = close - 0.001
    adx, plus_di, _ = adx_dmi(high, low, close, 14)
    assert np.isnan(plus_di[13])  # +DI valid from index period
    assert not np.isnan(plus_di[14])
    assert np.isnan(adx[2 * 14 - 2])  # ADX valid from index 2*period-1
    assert not np.isnan(adx[2 * 14 - 1])


def test_adx_bounds() -> None:
    rng = np.random.default_rng(3)
    n = 300
    close = 1.1 + np.cumsum(rng.standard_normal(n) * 0.001)
    high = close + np.abs(rng.standard_normal(n) * 0.0005)
    low = close - np.abs(rng.standard_normal(n) * 0.0005)
    adx, plus_di, minus_di = adx_dmi(high, low, close, 14)
    for arr in (adx, plus_di, minus_di):
        valid = arr[~np.isnan(arr)]
        assert np.all(valid >= 0.0) and np.all(valid <= 100.0)
