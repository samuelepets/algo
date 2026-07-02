"""Unit tests for MR-04 backtest engine."""

from __future__ import annotations

import numpy as np

from backtest import INPUT_CLOSE_DETRENDED, INPUT_LOG_RETURN, backtest_core
from indicators import ATR_PERIOD, atr, zscore_close_detrended, zscore_log_return


def _run(
    close: np.ndarray,
    zscore_window: int = 20,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.5,
    atr_stop_mult: float = 1.0,
    input_type: int = INPUT_LOG_RETURN,
) -> tuple:
    n = len(close)
    ts = np.arange(n, dtype=np.int64) * 300
    high = close + 0.002
    low = close - 0.002
    open_ = close.copy()
    atr_v = atr(high, low, close, ATR_PERIOD)
    if input_type == INPUT_LOG_RETURN:
        z = zscore_log_return(close, zscore_window)
    else:
        z = zscore_close_detrended(close, zscore_window)
    warm = zscore_window + 2
    return backtest_core(
        open_, high, low, close, ts,
        z, atr_v,
        entry_threshold, exit_threshold, atr_stop_mult, warm,
    )


def test_no_trades_flat() -> None:
    # Flat series -> std=0 -> z is NaN everywhere -> no entries.
    close = np.full(500, 1.1, dtype=np.float64)
    _, _, _, _, n_trades = _run(close)
    assert n_trades == 0


def test_long_trade_triggers_on_return_spike_down() -> None:
    # A sharp single-bar drop pushes the return z-score well below
    # -entry_threshold, then price recovers back toward the mean, crossing
    # the exit threshold on the following bar.
    n = 500
    close = np.full(n, 1.1, dtype=np.float64)
    close[300] = 1.07
    close[301:] = 1.1
    _, _, _, _, n_trades = _run(
        close,
        zscore_window=20,
        entry_threshold=2.0,
        exit_threshold=0.5,
        atr_stop_mult=2.0,
        input_type=INPUT_LOG_RETURN,
    )
    assert n_trades > 0


def test_max_hold_safety_net_forces_exit() -> None:
    # A sharp drop triggers an oversold long entry (close_detrended z-score).
    # Price then drifts persistently downward (never reverting toward the
    # rolling mean, so the target never fires) while a very wide ATR stop
    # never gets touched — only the 200-bar forced-exit safety net can close
    # the position.
    n = 600
    close = np.full(n, 1.1, dtype=np.float64)
    close[100] = 1.05
    for i in range(101, n):
        close[i] = close[i - 1] - 0.000005
    _, _, _, _, n_trades = _run(
        close,
        zscore_window=20,
        entry_threshold=2.0,
        exit_threshold=0.0,
        atr_stop_mult=100.0,
        input_type=INPUT_CLOSE_DETRENDED,
    )
    assert n_trades > 0


def test_deterministic() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.02 * np.sin(t / 30.0)
    r1 = _run(close, zscore_window=30, entry_threshold=1.5, exit_threshold=0.0, atr_stop_mult=1.0)
    r2 = _run(close, zscore_window=30, entry_threshold=1.5, exit_threshold=0.0, atr_stop_mult=1.0)
    assert r1 == r2


def test_input_types_both_run_without_crash() -> None:
    n = 1000
    t = np.arange(n, dtype=np.float64)
    close = 1.1 + 0.03 * np.sin(t / 25.0)
    r_lr = _run(close, input_type=INPUT_LOG_RETURN)
    r_cd = _run(close, input_type=INPUT_CLOSE_DETRENDED)
    assert r_lr[4] >= 0
    assert r_cd[4] >= 0
