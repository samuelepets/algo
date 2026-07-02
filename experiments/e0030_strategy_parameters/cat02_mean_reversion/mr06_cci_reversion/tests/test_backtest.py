"""Unit tests for MR-06 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import atr, adx, cci, ADX_PERIOD, ATR_PERIOD


def _run(
    close,
    high=None,
    low=None,
    cci_period=14,
    entry_threshold=100,
    exit_threshold=50,
    adx_filter=0,
    atr_stop_mult=2.0,
):
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    if high is None:
        high = close + 0.002
    if low is None:
        low = close - 0.002
    open_ = close.copy()
    cci_v = cci(high, low, close, cci_period)
    atr_v = atr(high, low, close, ATR_PERIOD)
    adx_v = adx(high, low, close, ADX_PERIOD)
    warm = max(cci_period, ADX_PERIOD * 2) + 2
    return backtest_core(
        open_, high, low, close, ts,
        cci_v, atr_v, adx_v,
        float(entry_threshold), float(exit_threshold), adx_filter,
        atr_stop_mult, warm,
    )


def test_no_trades_flat() -> None:
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_reversion_fires_on_spike_down() -> None:
    # Flat price, then a sharp multi-bar dip that pushes CCI well below
    # -entry_threshold, followed by a recovery back toward the prior level
    # (CCI reverts toward zero, or the forced-exit safety net closes it).
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[200:230] = 1.07  # sharp multi-bar dip
    close[230:] = 1.1      # recovery back to prior level

    _, _, _, _, n_trades = _run(
        close, cci_period=14, entry_threshold=100, exit_threshold=50, atr_stop_mult=2.0
    )
    assert n_trades > 0


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 30.0)
    r1 = _run(close)
    r2 = _run(close)
    assert r1 == r2


def test_adx_filter_reduces_trades_in_strong_trend() -> None:
    # A strongly-trending series (persistent one-directional drift) keeps ADX
    # elevated. A small, faster oscillation superimposed on the drift still
    # produces occasional CCI extremes. A tight ADX filter should suppress
    # entries (fewer or zero trades) relative to no filter at all.
    n = 700
    t = np.arange(n, dtype=np.float64)
    trend = 0.00035 * t
    osc = 0.012 * np.sin(t / 8.0)
    close = 1.1 + trend + osc
    high = close + 0.0005
    low = close - 0.0005

    _, _, _, _, n_no_filter = _run(
        close, high=high, low=low, entry_threshold=100, exit_threshold=50,
        adx_filter=0, atr_stop_mult=1.5,
    )
    _, _, _, _, n_tight_filter = _run(
        close, high=high, low=low, entry_threshold=100, exit_threshold=50,
        adx_filter=15, atr_stop_mult=1.5,
    )
    assert n_no_filter > 0
    assert n_tight_filter <= n_no_filter


def test_high_entry_threshold_reduces_trades() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 15.0)
    _, _, _, _, n_loose = _run(close, entry_threshold=100, exit_threshold=50)
    _, _, _, _, n_strict = _run(close, entry_threshold=200, exit_threshold=50)
    assert n_strict <= n_loose
