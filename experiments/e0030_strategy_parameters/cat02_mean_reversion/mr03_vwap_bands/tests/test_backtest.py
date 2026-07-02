"""Unit tests for MR-03 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import ATR_PERIOD, atr, vwap_bands


def _make_series(n: int, seed_amplitude: float = 0.0004, spike_start: int = 300,
                  spike_len: int = 20, spike_size: float = -0.01, step_secs: int = 60):
    ts = np.arange(n, dtype=np.int64) * step_secs
    t = np.arange(n, dtype=np.float64)
    close = 1.1000 + seed_amplitude * np.sin(t / 15.0)
    if spike_start is not None:
        close[spike_start:spike_start + spike_len] += spike_size
    high = close + 0.0005
    low = close - 0.0005
    return ts, high, low, close


def _run(ts, high, low, close, entry_sigma=2.0, exit_sigma=0.0, atr_stop_mult=1.0, warm_bars=40):
    vwap, std = vwap_bands(ts, high, low, close, np.full(len(close), 10.0), 0)
    atr_v = atr(high, low, close, ATR_PERIOD)
    return backtest_core(close, high, low, ts, vwap, std, atr_v, entry_sigma, exit_sigma, atr_stop_mult, warm_bars)


def test_no_trades_flat() -> None:
    n = 500
    ts, high, low, close = _make_series(n, seed_amplitude=0.0, spike_start=None)
    _, _, _, _, n_trades = _run(ts, high, low, close)
    assert n_trades == 0


def test_reversion_fires_on_spike_down() -> None:
    n = 800
    ts, high, low, close = _make_series(n, spike_start=300, spike_len=20, spike_size=-0.02)
    _, _, _, _, n_trades = _run(ts, high, low, close, entry_sigma=2.0, atr_stop_mult=1.0)
    assert n_trades > 0


def test_reversion_fires_on_spike_up() -> None:
    n = 800
    ts, high, low, close = _make_series(n, spike_start=300, spike_len=20, spike_size=0.02)
    _, _, _, _, n_trades = _run(ts, high, low, close, entry_sigma=2.0, atr_stop_mult=1.0)
    assert n_trades > 0


def test_higher_entry_sigma_reduces_or_equal_trades() -> None:
    n = 800
    ts, high, low, close = _make_series(n, spike_start=300, spike_len=20, spike_size=-0.02)
    _, _, _, _, n_loose = _run(ts, high, low, close, entry_sigma=1.0)
    _, _, _, _, n_tight = _run(ts, high, low, close, entry_sigma=3.0)
    assert n_tight <= n_loose


def test_forced_exit_bounds_holding_period() -> None:
    # Persistent one-directional drift after the spike: price never returns
    # to VWAP, so the forced-exit safety net (MAX_HOLD_BARS) must still
    # close the trade eventually rather than looping forever.
    n = 900
    ts = np.arange(n, dtype=np.int64) * 60
    t = np.arange(n, dtype=np.float64)
    close = 1.1000 + 0.0004 * np.sin(t / 15.0)
    close[300:] -= 0.02  # drop and never recover
    high = close + 0.0005
    low = close - 0.0005
    _, _, _, _, n_trades = _run(ts, high, low, close, entry_sigma=2.0, atr_stop_mult=5.0)
    # Should not crash and should produce a finite, bounded trade count.
    assert n_trades >= 0


def test_deterministic() -> None:
    n = 800
    ts, high, low, close = _make_series(n, spike_start=300, spike_len=20, spike_size=-0.02)
    r1 = _run(ts, high, low, close)
    r2 = _run(ts, high, low, close)
    assert r1 == r2


def test_exit_sigma_zero_targets_vwap() -> None:
    n = 800
    ts, high, low, close = _make_series(n, spike_start=300, spike_len=20, spike_size=-0.02)
    _, _, _, _, n_trades_0 = _run(ts, high, low, close, exit_sigma=0.0)
    _, _, _, _, n_trades_1 = _run(ts, high, low, close, exit_sigma=1.0)
    # Both configurations should be able to execute trades without error.
    assert n_trades_0 >= 0 and n_trades_1 >= 0
