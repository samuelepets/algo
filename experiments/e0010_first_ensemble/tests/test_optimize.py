"""Tests for GA optimization (search space, engine, persistence)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import ga
import optimize
import search_space
from strategies import strategy_from_key


def test_decode_respects_int_and_float_genes() -> None:
    genome = [0.0, 0.5, 1.0, 0.25, 0.75]
    params = search_space.decode(genome, "S1_connors_rsi2")
    assert params["sma_regime"] == 50
    assert params["sma_exit"] == 16
    assert params["rsi_period"] == 10
    assert params["rsi_oversold"] == pytest.approx(7.25)
    assert params["rsi_overbought"] == pytest.approx(92.75)


def test_validate_params_s2_requires_fast_lt_slow() -> None:
    valid = {"fast_period": 5, "slow_period": 20, "rsi_period": 14, "rsi_overbought": 70.0, "rsi_oversold": 30.0}
    invalid = {"fast_period": 25, "slow_period": 20, "rsi_period": 14, "rsi_overbought": 70.0, "rsi_oversold": 30.0}
    assert search_space.validate_params("S2_ema_cross_rsi", valid)
    assert not search_space.validate_params("S2_ema_cross_rsi", invalid)


def test_ga_finds_better_than_random_on_sphere() -> None:
    target = np.array([0.2, 0.7, 0.4])

    def fitness(genome: list[float]) -> float:
        return -float(np.linalg.norm(np.array(genome) - target))

    result = ga.run_ga(
        fitness_fn=fitness,
        genome_length=3,
        config=ga.GAConfig(population_size=30, generations=20, seed=1),
    )
    assert result.best_fitness > -0.5


def _tiny_bars(n: int = 800) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    idx = pd.date_range("2023-01-02", periods=n, freq="min")
    close = 1.10 + np.cumsum(rng.normal(0.0, 0.0001, n))
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 1.0},
        index=idx,
    )


def test_optimize_strategy_roundtrip(tmp_path: Path) -> None:
    train = _tiny_bars(600)
    test = _tiny_bars(400)
    config = ga.GAConfig(population_size=6, generations=3, seed=0)
    record = optimize.optimize_strategy(
        "S3_rsi_centerline_ema",
        train,
        test,
        cost_per_turnover=0.0,
        ga_config=config,
    )
    path = optimize.save_record(record, tmp_path)
    loaded = optimize.load_record("S3_rsi_centerline_ema", tmp_path)
    assert loaded.strategy == record.strategy
    assert loaded.parameters == record.parameters
    assert path.name == "optimized_S3_rsi_centerline_ema.json"
    strategy = strategy_from_key(loaded.strategy, loaded.parameters)
    assert strategy.generate_signal(test).isin([-1.0, 0.0, 1.0]).all()


def test_save_record_json_is_readable(tmp_path: Path) -> None:
    record = optimize.OptimizationRecord(
        strategy="S1_connors_rsi2",
        train_year=2023,
        test_year=2024,
        parameters={"sma_regime": 100, "sma_exit": 5, "rsi_period": 2, "rsi_oversold": 10.0, "rsi_overbought": 90.0},
        train_metrics={"sharpe": 1.0},
        test_metrics={"sharpe": 0.5},
        train_fitness=1.0,
        ga_config={"population_size": 4},
        default_test_metrics={"sharpe": -1.0},
    )
    path = optimize.save_record(record, tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["strategy"] == "S1_connors_rsi2"
    assert payload["parameters"]["sma_regime"] == 100
