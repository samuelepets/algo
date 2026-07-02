"""Unit tests for MR-10 backtest engine.

Rather than reverse-engineering price paths that produce genuine fractal
divergences (fragile and hard to reason about), these tests feed hand-crafted
``pivot_low_vals`` / ``pivot_high_vals`` / ``rsi_vals`` arrays directly into
``backtest_core`` — the same contract ``main.py`` uses via the precomputed
indicator caches — so the entry/exit state machine is tested in isolation.
"""

from __future__ import annotations

import numpy as np

from backtest import CONFIRM_ANY_BAR, CONFIRM_BULLISH_CANDLE, backtest_core

N = 40
LOOKBACK = 2


def _base_arrays() -> dict:
    close = np.full(N, 1.0900, dtype=np.float64)
    open_ = close.copy()
    high = close + 0.0005
    low = close - 0.0005
    ts = np.arange(N, dtype=np.int64) * 300
    atr_vals = np.full(N, 0.01, dtype=np.float64)
    rsi_vals = np.full(N, np.nan, dtype=np.float64)
    pivot_low_vals = np.full(N, np.nan, dtype=np.float64)
    pivot_high_vals = np.full(N, np.nan, dtype=np.float64)
    return dict(
        open_=open_,
        high=high,
        low=low,
        close=close,
        ts=ts,
        atr_vals=atr_vals,
        rsi_vals=rsi_vals,
        pivot_low_vals=pivot_low_vals,
        pivot_high_vals=pivot_high_vals,
    )


def _run(a: dict, div_tolerance=0.0, confirmation=CONFIRM_ANY_BAR, atr_stop_mult=1.0):
    return backtest_core(
        a["open_"],
        a["high"],
        a["low"],
        a["close"],
        a["ts"],
        a["rsi_vals"],
        a["pivot_low_vals"],
        a["pivot_high_vals"],
        a["atr_vals"],
        LOOKBACK,
        div_tolerance,
        confirmation,
        atr_stop_mult,
        0,
    )


def test_no_pivots_no_trades() -> None:
    a = _base_arrays()
    _, _, _, _, n_trades = _run(a)
    assert n_trades == 0


def test_single_pivot_no_divergence_yet() -> None:
    a = _base_arrays()
    a["pivot_low_vals"][5] = 1.0850
    a["rsi_vals"][5] = 30.0
    _, _, _, _, n_trades = _run(a)
    assert n_trades == 0


def test_bullish_divergence_enters_and_hits_target() -> None:
    a = _base_arrays()
    # pivot 1 at p=5: price 1.0900, rsi 30 (weak, first low)
    a["pivot_low_vals"][5] = 1.0900
    a["rsi_vals"][5] = 30.0
    # pivot 2 at p=15: LOWER low in price (1.0850) but HIGHER rsi (45) -> bullish divergence
    a["pivot_low_vals"][15] = 1.0850
    a["rsi_vals"][15] = 45.0
    # confirmation bar i = 15 + LOOKBACK = 17
    a["close"][17] = 1.0900
    a["open_"][17] = 1.0900
    # entry_price=1.0900, cur_low=1.0850 -> pivot_dist=0.005; atr_cap=1.0*0.01=0.01 -> dist=0.005
    # stop=1.0850, target=1.0900+2*0.005=1.1000
    a["high"][20] = 1.1005  # breaches target
    a["low"][20] = 1.0895   # does not breach stop
    _, _, _, _, n_trades = _run(a, div_tolerance=0.0)
    assert n_trades == 1


def test_bullish_divergence_blocked_by_tolerance() -> None:
    a = _base_arrays()
    a["pivot_low_vals"][5] = 1.0900
    a["rsi_vals"][5] = 30.0
    a["pivot_low_vals"][15] = 1.0850
    a["rsi_vals"][15] = 28.0  # NOT higher than prior low's RSI -> no divergence
    _, _, _, _, n_trades = _run(a, div_tolerance=0.0)
    assert n_trades == 0


def test_bearish_divergence_enters_short() -> None:
    a = _base_arrays()
    a["pivot_high_vals"][5] = 1.0900
    a["rsi_vals"][5] = 70.0
    # higher high in price, lower rsi -> bearish divergence
    a["pivot_high_vals"][15] = 1.0950
    a["rsi_vals"][15] = 55.0
    a["close"][17] = 1.0900
    a["open_"][17] = 1.0900
    # entry=1.0900, cur_high=1.0950 -> pivot_dist=0.005, atr_cap=0.01 -> dist=0.005
    # stop=1.0950, target=1.0900-0.01=1.0800
    a["low"][20] = 1.0795
    a["high"][20] = 1.0905
    _, _, _, _, n_trades = _run(a, div_tolerance=0.0)
    assert n_trades == 1


def test_stop_loss_exit() -> None:
    a = _base_arrays()
    a["pivot_low_vals"][5] = 1.0900
    a["rsi_vals"][5] = 30.0
    a["pivot_low_vals"][15] = 1.0850
    a["rsi_vals"][15] = 45.0
    a["close"][17] = 1.0900
    a["open_"][17] = 1.0900
    # stop at 1.0850 -> breach it instead of target
    a["low"][20] = 1.0845
    a["high"][20] = 1.0905
    _, _, _, _, n_trades = _run(a, div_tolerance=0.0)
    assert n_trades == 1


def test_bullish_candle_confirmation_blocks_bearish_candle() -> None:
    a = _base_arrays()
    a["pivot_low_vals"][5] = 1.0900
    a["rsi_vals"][5] = 30.0
    a["pivot_low_vals"][15] = 1.0850
    a["rsi_vals"][15] = 45.0
    # confirmation bar closes BELOW open -> bearish candle, long entry must be skipped
    a["open_"][17] = 1.0905
    a["close"][17] = 1.0900
    _, _, _, _, n_trades = _run(a, div_tolerance=0.0, confirmation=CONFIRM_BULLISH_CANDLE)
    assert n_trades == 0


def test_bullish_candle_confirmation_allows_bullish_candle() -> None:
    a = _base_arrays()
    a["pivot_low_vals"][5] = 1.0900
    a["rsi_vals"][5] = 30.0
    a["pivot_low_vals"][15] = 1.0850
    a["rsi_vals"][15] = 45.0
    a["open_"][17] = 1.0895
    a["close"][17] = 1.0900  # close > open -> bullish candle, allowed
    a["high"][20] = 1.1005
    a["low"][20] = 1.0895
    _, _, _, _, n_trades = _run(a, div_tolerance=0.0, confirmation=CONFIRM_BULLISH_CANDLE)
    assert n_trades == 1


def test_deterministic() -> None:
    a = _base_arrays()
    a["pivot_low_vals"][5] = 1.0900
    a["rsi_vals"][5] = 30.0
    a["pivot_low_vals"][15] = 1.0850
    a["rsi_vals"][15] = 45.0
    a["close"][17] = 1.0900
    a["open_"][17] = 1.0900
    a["high"][20] = 1.1005
    a["low"][20] = 1.0895
    r1 = _run(a, div_tolerance=0.0)
    r2 = _run(a, div_tolerance=0.0)
    assert r1 == r2


def test_forced_exit_after_max_hold() -> None:
    # FORCED_EXIT_BARS=50, entry at bar 17 -> needs bars up to ~67 to observe the
    # forced exit itself (rather than the end-of-data close fallback).
    n = 90
    close = np.full(n, 1.0900, dtype=np.float64)
    open_ = close.copy()
    high = close + 0.0002  # never reaches target (1.1000)
    low = close - 0.0002   # never reaches stop (1.0850)
    ts = np.arange(n, dtype=np.int64) * 300
    atr_vals = np.full(n, 0.01, dtype=np.float64)
    rsi_vals = np.full(n, np.nan, dtype=np.float64)
    pivot_low_vals = np.full(n, np.nan, dtype=np.float64)
    pivot_high_vals = np.full(n, np.nan, dtype=np.float64)
    pivot_low_vals[5] = 1.0900
    rsi_vals[5] = 30.0
    pivot_low_vals[15] = 1.0850
    rsi_vals[15] = 45.0

    _, _, _, _, n_trades = backtest_core(
        open_, high, low, close, ts, rsi_vals, pivot_low_vals, pivot_high_vals,
        atr_vals, LOOKBACK, 0.0, CONFIRM_ANY_BAR, 1.0, 0,
    )
    assert n_trades == 1
