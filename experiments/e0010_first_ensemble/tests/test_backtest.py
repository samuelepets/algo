"""Tests for the e0010 vectorized backtest harness."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import backtest
import data


def _bars(opens: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-02 00:00:00", periods=len(opens), freq="min")
    return pd.DataFrame(
        {
            "open": opens,
            "high": opens,
            "low": opens,
            "close": opens,
            "volume": 1.0,
        },
        index=idx,
    )


def test_backtest_no_lookahead_first_bar_flat() -> None:
    bars = _bars([1.0, 1.01, 1.02, 1.03])
    signal = pd.Series(1.0, index=bars.index)
    result = backtest.backtest(bars, signal, periods_per_year=2.0)
    assert result.position.iloc[0] == 0.0
    assert result.position.iloc[1] == 1.0


def test_backtest_return_math_long_only() -> None:
    # Open path: 1.00 -> 1.10 -> 1.21 (two +10% open-to-open legs)
    bars = _bars([1.0, 1.1, 1.21])
    signal = pd.Series(1.0, index=bars.index)
    result = backtest.backtest(bars, signal, periods_per_year=2.0)
    # Bar 0: flat. Bar 1: long, ret = 1.21/1.1 - 1 = 0.1
    assert len(result.returns) == 2
    assert result.returns.iloc[1] == pytest.approx(0.1)
    assert result.equity.iloc[-1] == pytest.approx(1.1)


def test_backtest_costs_reduce_returns() -> None:
    bars = _bars([1.0, 1.1, 1.21])
    signal = pd.Series(1.0, index=bars.index)
    free = backtest.backtest(bars, signal, cost_per_turnover=0.0, periods_per_year=2.0)
    costly = backtest.backtest(bars, signal, cost_per_turnover=0.01, periods_per_year=2.0)
    # Enter long on bar 1: turnover 0 -> 1 costs 1 * 0.01
    assert costly.returns.iloc[1] == pytest.approx(free.returns.iloc[1] - 0.01)


def test_compute_metrics_keys() -> None:
  idx = pd.date_range("2024-01-02", periods=100, freq="min")
  returns = pd.Series(np.random.default_rng(0).normal(0.0001, 0.001, 100), index=idx)
  position = pd.Series(1.0, index=idx)
  turnover = position.diff().abs().fillna(1.0)
  metrics = backtest.compute_metrics(returns, position, turnover, periods_per_year=525_600.0)
  for key in ("total_return", "ann_return", "sharpe", "max_drawdown", "hit_rate", "ann_turnover"):
    assert key in metrics


def test_backtest_on_real_eurusd_sample() -> None:
  bars = data.load_bars("EURUSD", years=[2024]).iloc[:5000]
  signal = pd.Series(0.0, index=bars.index)
  signal.iloc[100:] = 1.0  # go long after warmup
  result = backtest.backtest(bars, signal)
  assert len(result.returns) == len(bars) - 1
  assert result.equity.iloc[-1] > 0
  assert "sharpe" in result.metrics
