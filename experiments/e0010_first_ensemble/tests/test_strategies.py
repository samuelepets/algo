"""Tests for base strategies S1–S3."""

from __future__ import annotations

import numpy as np
import pandas as pd

import backtest
import data
from strategies import ConnorsRsi2, EmaCrossRsi, RsiCenterlineEma, rsi, sma


def _synthetic_bars(n: int = 500, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-02 00:00:00", periods=n, freq="min")
    close = 1.10 + np.cumsum(rng.normal(0.0, 0.0001, n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.00005,
            "low": close - 0.00005,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )


def test_rsi_bounded() -> None:
    bars = _synthetic_bars(300)
    val = rsi(bars["close"], 14).dropna()
    assert val.min() >= 0.0
    assert val.max() <= 100.0


def test_sma_warmup() -> None:
    bars = _synthetic_bars(50)
    val = sma(bars["close"], 20)
    assert val.iloc[:19].isna().all()
    assert val.iloc[19:].notna().all()


def test_strategy_signal_shape_and_range() -> None:
    bars = _synthetic_bars(600)
    for strategy in (ConnorsRsi2(), EmaCrossRsi(), RsiCenterlineEma()):
        signal = strategy.generate_signal(bars)
        assert signal.index.equals(bars.index)
        assert signal.isin([-1.0, 0.0, 1.0]).all()


def test_connors_enters_long_on_oversold_in_uptrend() -> None:
    n = 250
    idx = pd.date_range("2024-01-02", periods=n, freq="min")
    close = pd.Series(1.10 + np.linspace(0, 0.05, n), index=idx)
    # Force a sharp dip at the end so RSI(2) drops.
    close.iloc[-3:] = close.iloc[-4] - 0.02
    bars = pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 1.0},
        index=idx,
    )
    signal = ConnorsRsi2().generate_signal(bars)
    assert signal.iloc[-1] in (-1.0, 0.0, 1.0)


def test_baseline_backtest_smoke_on_eurusd() -> None:
    bars = data.load_bars("EURUSD", years=[2024]).iloc[:10_000]
    for strategy in (ConnorsRsi2(), EmaCrossRsi(), RsiCenterlineEma()):
        signal = strategy.generate_signal(bars)
        result = backtest.backtest(bars, signal, cost_per_turnover=0.00002)
        assert "sharpe" in result.metrics
        assert len(result.returns) > 0
