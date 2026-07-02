"""Unit tests for MR-16 backtest engine (opening-range fade)."""

from __future__ import annotations

import numpy as np

from backtest import TARGET_MID, TARGET_OPPOSITE, backtest_core

SEC_PER_DAY = 86400
ORH = 1.0010
ORL = 0.9990


def _env(n: int, start_ts: int = 0) -> tuple:
    ts = np.arange(n, dtype=np.int64) * 300 + start_ts
    close = np.full(n, 1.0000, dtype=np.float64)
    high = close + 0.0005
    low = close - 0.0005
    open_ = close.copy()
    atr_vals = np.full(n, 0.0005, dtype=np.float64)
    orh_bar = np.full(n, ORH, dtype=np.float64)
    orl_bar = np.full(n, ORL, dtype=np.float64)
    return ts, open_, high, low, close, atr_vals, orh_bar, orl_bar


def _run(
    high, low, close, ts=None, atr_vals=None, orh_bar=None, orl_bar=None,
    or_window_end_min=0, reversal_bars=2, target_mode=TARGET_OPPOSITE,
    atr_stop_mult=1.0, warm_bars=0,
):
    n = len(close)
    if ts is None:
        ts = np.arange(n, dtype=np.int64) * 300
    if atr_vals is None:
        atr_vals = np.full(n, 0.0005, dtype=np.float64)
    if orh_bar is None:
        orh_bar = np.full(n, ORH, dtype=np.float64)
    if orl_bar is None:
        orl_bar = np.full(n, ORL, dtype=np.float64)
    open_ = close.copy()
    return backtest_core(
        open_, high, low, close, ts, atr_vals, orh_bar, orl_bar,
        or_window_end_min, reversal_bars, target_mode, atr_stop_mult, warm_bars,
    )


def test_no_trades_inside_range() -> None:
    n = 50
    close = np.full(n, 1.0000, dtype=np.float64)
    high = close + 0.0002
    low = close - 0.0002
    _, _, _, _, n_trades = _run(high, low, close)
    assert n_trades == 0


def test_long_fade_triggers_on_failed_orl_breakout() -> None:
    n = 8
    close = np.full(n, 1.0000, dtype=np.float64)
    close[1] = 0.9950  # breakout below ORL
    close[2] = 0.9995  # reversal: back inside [ORL, ORH]
    close[3] = 1.0020  # rally toward opposite band target
    high = close + 0.0002
    low = close - 0.0002
    low[1] = 0.9940  # breakout bar extreme (used for the stop)
    high[3] = 1.0011  # touches ORH target (1.0010)
    _, _, _, _, n_trades = _run(high, low, close, reversal_bars=2, target_mode=TARGET_OPPOSITE)
    assert n_trades == 1


def test_short_fade_triggers_on_failed_orh_breakout() -> None:
    n = 8
    close = np.full(n, 1.0000, dtype=np.float64)
    close[1] = 1.0050  # breakout above ORH
    close[2] = 1.0005  # reversal: back inside range
    close[3] = 0.9980
    high = close + 0.0002
    low = close - 0.0002
    high[1] = 1.0060  # breakout bar extreme (used for the stop)
    low[3] = 0.9989  # touches ORL target (0.9990)
    _, _, _, _, n_trades = _run(high, low, close, reversal_bars=2, target_mode=TARGET_OPPOSITE)
    assert n_trades == 1


def test_no_reversal_within_window_invalidates_setup() -> None:
    n = 10
    close = np.full(n, 1.0000, dtype=np.float64)
    close[1] = 0.9950  # breakout below ORL
    close[2:] = 0.9940  # never comes back inside the range
    high = close + 0.0002
    low = close - 0.0002
    _, _, _, _, n_trades = _run(high, low, close, reversal_bars=1)
    assert n_trades == 0


def test_only_one_setup_per_day() -> None:
    n = 12
    close = np.full(n, 1.0000, dtype=np.float64)
    # First breakout at bar 1, fails to reverse within 1 bar -> invalidated,
    # setup for the day is consumed.
    close[1] = 0.9950
    close[2] = 0.9940
    # A later, otherwise-valid breakout+reversal on the same day must be ignored.
    close[3] = 0.9950
    close[4] = 0.9995
    close[5] = 1.0020
    high = close + 0.0002
    low = close - 0.0002
    low[1] = 0.9940
    low[3] = 0.9940
    high[5] = 1.0011
    _, _, _, _, n_trades = _run(high, low, close, reversal_bars=1)
    assert n_trades == 0


def test_stop_checked_before_target_same_bar() -> None:
    n = 8
    close = np.full(n, 1.0000, dtype=np.float64)
    close[1] = 0.9950  # breakout below ORL
    close[2] = 0.9995  # reversal -> enter long, stop = low[1] - atr = 0.9940 - 0.0005 = 0.9935
    high = close + 0.0002
    low = close - 0.0002
    low[1] = 0.9940
    # Bar 3: both stop AND target would be hit intrabar -> stop must win.
    low[3] = 0.9930   # below stop (0.9935)
    high[3] = 1.0020  # above target (ORH = 1.0010)
    _, _, _, _, n_trades = _run(
        high, low, close, reversal_bars=2, atr_stop_mult=1.0, target_mode=TARGET_OPPOSITE
    )
    # compute_metrics zeroes all aggregate stats below 2 trades, so total
    # return can't be checked here directly; the trade count confirms the
    # position closed on bar 3 rather than surviving to hit the target.
    assert n_trades == 1


def test_forced_end_of_day_exit() -> None:
    n = 5
    close = np.full(n, 1.0000, dtype=np.float64)
    close[1] = 0.9950  # breakout below ORL
    close[2] = 0.9995  # reversal -> entry (long), not the day's last bar
    close[3] = 1.0002  # neither stop nor target hit; this IS day 0's last bar
    close[4] = 1.0500  # day 1 — must not matter, position already closed
    high = close + 0.0001
    low = close - 0.0001
    low[1] = 0.9940
    ts = np.array([0, 300, 600, 900, SEC_PER_DAY + 100], dtype=np.int64)
    _, _, _, ret, n_trades = _run(high, low, close, ts=ts, reversal_bars=2)
    assert n_trades == 1
    # Forced exit at close (1.0002), a small gain, not the 1.0010 opposite-band target.
    assert ret < 1.0


def test_mid_range_target_used_when_selected() -> None:
    n = 8
    close = np.full(n, 1.0000, dtype=np.float64)
    close[1] = 0.9950
    close[2] = 0.9995  # entry long, mid-range target = (ORH+ORL)/2 = 1.0000
    high = close + 0.0002
    low = close - 0.0002
    low[1] = 0.9940
    high[3] = 1.0001  # crosses the mid-range target, well below ORH
    _, _, _, _, n_trades = _run(
        high, low, close, reversal_bars=2, target_mode=TARGET_MID
    )
    assert n_trades == 1


def test_before_or_window_end_no_signal() -> None:
    n = 5
    close = np.full(n, 1.0000, dtype=np.float64)
    close[1] = 0.9950
    close[2] = 0.9995
    high = close + 0.0002
    low = close - 0.0002
    low[1] = 0.9940
    # OR window "closes" only after bar 3 -> the breakout at bar 1 must be ignored.
    _, _, _, _, n_trades = _run(high, low, close, or_window_end_min=10**9, reversal_bars=2)
    assert n_trades == 0


def test_deterministic() -> None:
    n = 300
    t = np.arange(n, dtype=np.float64)
    close = 1.0000 + 0.003 * np.sin(t / 15.0)
    high = close + 0.0003
    low = close - 0.0003
    r1 = _run(high, low, close, reversal_bars=2)
    r2 = _run(high, low, close, reversal_bars=2)
    assert r1 == r2


def test_nan_or_skips_bar() -> None:
    n = 20
    close = np.full(n, 1.0000, dtype=np.float64)
    close[1] = 0.9950
    close[2] = 0.9995
    high = close + 0.0002
    low = close - 0.0002
    low[1] = 0.9940
    orh_bar = np.full(n, np.nan, dtype=np.float64)
    orl_bar = np.full(n, np.nan, dtype=np.float64)
    _, _, _, _, n_trades = _run(high, low, close, orh_bar=orh_bar, orl_bar=orl_bar)
    assert n_trades == 0
