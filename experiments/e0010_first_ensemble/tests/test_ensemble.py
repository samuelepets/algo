"""Tests for ensemble aggregation."""

from __future__ import annotations

import numpy as np
import pandas as pd

import backtest
import data
import ensemble
from strategies import ALL_STRATEGIES


def _idx(n: int = 5) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-02", periods=n, freq="min")


def test_majority_vote_three_strategies() -> None:
    i = _idx(3)
    s1 = pd.Series([1.0, 1.0, -1.0], index=i)
    s2 = pd.Series([1.0, -1.0, -1.0], index=i)
    s3 = pd.Series([0.0, -1.0, 1.0], index=i)
    out = ensemble.majority_vote([s1, s2, s3])
    assert out.tolist() == [1.0, 0.0, 0.0]


def test_averaged_signal_clips() -> None:
    i = _idx(2)
    s1 = pd.Series([1.0, 1.0], index=i)
    s2 = pd.Series([1.0, -1.0], index=i)
    out = ensemble.averaged_signal([s1, s2])
    assert out.iloc[0] == 1.0
    assert out.iloc[1] == 0.0


def test_return_correlation_matrix() -> None:
    i = _idx(100)
    rng = np.random.default_rng(0)
    a = pd.Series(rng.normal(0, 0.001, 100), index=i)
    b = pd.Series(rng.normal(0, 0.001, 100), index=i)
    corr = ensemble.return_correlation_matrix({"a": a, "b": b})
    assert corr.loc["a", "a"] == 1.0
    assert -1.0 <= corr.loc["a", "b"] <= 1.0


def test_inverse_vol_weighted_signal_range() -> None:
    i = _idx(200)
    rng = np.random.default_rng(1)
    sig = pd.Series(rng.choice([-1.0, 0.0, 1.0], 200), index=i)
    ret = pd.Series(rng.normal(0, 0.001, 200), index=i)
    out = ensemble.inverse_vol_weighted_signal(
        [sig, sig, sig], [ret, ret, ret], window=20, min_periods=10
    )
    assert out.between(-1.0, 1.0).all()


def test_ensemble_smoke_on_eurusd() -> None:
    bars = data.load_bars("EURUSD", years=[2024]).iloc[:8000]
    sig_list = [s.generate_signal(bars) for s in ALL_STRATEGIES]
    ret_list = [
        backtest.backtest(bars, sig, cost_per_turnover=0.00002).returns for sig in sig_list
    ]
    for method in (
        ensemble.majority_vote(sig_list),
        ensemble.averaged_signal(sig_list),
        ensemble.inverse_vol_weighted_signal(sig_list, ret_list, window=100),
    ):
        result = backtest.backtest(bars, method, cost_per_turnover=0.00002)
        assert "sharpe" in result.metrics
