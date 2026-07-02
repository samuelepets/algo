"""Unit tests for MR-02 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import backtest_core
from indicators import ATR_PERIOD, atr, rsi, sma


def _run(
    close: np.ndarray,
    rsi_period: int = 2,
    long_threshold: float = 10.0,
    short_threshold: float = 90.0,
    exit_rsi_long: float = 50.0,
    exit_rsi_short: float = 50.0,
    trend_ema: int = 0,
    max_hold_bars: int = 20,
) -> tuple:
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.002
    low = close - 0.002
    open_ = close.copy()
    rsi_v = rsi(close, rsi_period)
    atr_v = atr(high, low, close, ATR_PERIOD)
    trend_v = sma(close, trend_ema) if trend_ema > 0 else np.zeros(n, dtype=np.float64)
    warm = max(rsi_period, trend_ema, ATR_PERIOD) + 2
    return backtest_core(
        open_, high, low, close, ts,
        rsi_v, trend_v, atr_v,
        long_threshold, short_threshold, exit_rsi_long, exit_rsi_short,
        trend_ema, max_hold_bars, warm,
    )


def test_no_trades_flat() -> None:
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_reversion_fires_on_dip_and_recovers() -> None:
    # Long flat lead-in (RSI stabilises at 50, avg_gain == avg_loss == 0),
    # then a single down-tick drives RSI(2) straight to 0 (avg_gain stays 0,
    # avg_loss jumps positive) -> triggers a long entry below long_threshold.
    # A subsequent recovery run pushes RSI back above exit_rsi_long, closing
    # the trade via the RSI-exit branch (not the stop).
    lead = np.full(200, 1.1000, dtype=np.float64)
    dip = np.array([1.0990], dtype=np.float64)
    recovery = np.linspace(1.0995, 1.1150, 30)
    tail = np.full(50, 1.1150, dtype=np.float64)
    close = np.concatenate([lead, dip, recovery, tail])

    _, _, _, _, n_trades = _run(close, long_threshold=10.0, exit_rsi_long=50.0)
    assert n_trades > 0


def test_max_hold_forces_exit() -> None:
    # Same dip trigger, but price then stays perfectly flat at the dipped
    # level: RSI(2) stays pinned at 0 (never crosses exit_rsi_long) and the
    # stop (entry - 1.5*ATR ~ entry - 0.006) is never touched (price doesn't
    # move). The only possible exit is the max-hold forced exit.
    lead = np.full(200, 1.1000, dtype=np.float64)
    dip = np.array([1.0990], dtype=np.float64)
    tail = np.full(100, 1.0990, dtype=np.float64)
    close = np.concatenate([lead, dip, tail])

    _, _, _, _, n_trades = _run(
        close, long_threshold=10.0, exit_rsi_long=50.0, max_hold_bars=5
    )
    assert n_trades > 0


def test_short_side_fires_symmetrically() -> None:
    lead = np.full(200, 1.1000, dtype=np.float64)
    spike = np.array([1.1010], dtype=np.float64)
    recovery = np.linspace(1.1005, 1.0850, 30)
    tail = np.full(50, 1.0850, dtype=np.float64)
    close = np.concatenate([lead, spike, recovery, tail])

    _, _, _, _, n_trades = _run(close, short_threshold=90.0, exit_rsi_short=50.0)
    assert n_trades > 0


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.02 * np.sin(t / 15.0)
    r1 = _run(close)
    r2 = _run(close)
    assert r1 == r2


def test_trend_filter_blocks_counter_trend_longs() -> None:
    # Strong downtrend: close well below SMA(100) throughout, so with the
    # trend filter enabled, longs (which require close > trend SMA) should
    # never fire even if RSI dips low.
    n = 400
    close = np.linspace(1.20, 1.00, n)
    # Add a couple of oversold ticks near the end to try to trigger a long.
    close[-5:] = close[-6] - np.array([0.002, 0.001, 0.003, 0.001, 0.002])

    _, _, _, _, n_trades_filtered = _run(close, trend_ema=100, long_threshold=15.0)
    assert n_trades_filtered == 0


def test_more_combinations_produce_at_least_as_many_trades_without_filter() -> None:
    n = 400
    close = np.linspace(1.20, 1.00, n)
    close[-5:] = close[-6] - np.array([0.002, 0.001, 0.003, 0.001, 0.002])

    _, _, _, _, n_trades_no_filter = _run(close, trend_ema=0, long_threshold=15.0)
    _, _, _, _, n_trades_filtered = _run(close, trend_ema=100, long_threshold=15.0)
    assert n_trades_no_filter >= n_trades_filtered
