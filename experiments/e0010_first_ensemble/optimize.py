"""Genetic-algorithm parameter optimization for S1–S3."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import backtest
import data
import ga
import search_space
from strategies import STRATEGY_KEYS, strategy_from_key


OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"


@dataclass
class OptimizationRecord:
    strategy: str
    train_year: int
    test_year: int
    parameters: dict[str, int | float]
    train_metrics: dict[str, float]
    test_metrics: dict[str, float]
    train_fitness: float
    ga_config: dict[str, int | float]
    default_test_metrics: dict[str, float]


def _fitness_score(metrics: dict[str, float]) -> float:
    """Sharpe with mild penalties for extreme drawdown and turnover."""
    sharpe = float(metrics.get("sharpe", 0.0))
    drawdown = float(metrics.get("max_drawdown", 0.0))
    turnover = float(metrics.get("ann_turnover", 0.0))
    penalty = 0.0
    if drawdown < -0.5:
        penalty += abs(drawdown + 0.5) * 2.0
    if turnover > 100_000:
        penalty += (turnover - 100_000) / 100_000.0
    return sharpe - penalty


def _evaluate(
    strategy_key: str,
    params: dict[str, int | float],
    bars,
    cost_per_turnover: float,
) -> dict[str, float]:
    strategy = strategy_from_key(strategy_key, params)
    signal = strategy.generate_signal(bars)
    result = backtest.backtest(bars, signal, cost_per_turnover=cost_per_turnover)
    return result.metrics


def optimize_strategy(
    strategy_key: str,
    train_bars,
    test_bars,
    cost_per_turnover: float,
    ga_config: ga.GAConfig,
) -> OptimizationRecord:
    cache: dict[tuple[float, ...], float] = {}

    def fitness_fn(genome: list[float]) -> float:
        params = search_space.decode(genome, strategy_key)
        if not search_space.validate_params(strategy_key, params):
            return -1e9
        metrics = _evaluate(strategy_key, params, train_bars, cost_per_turnover)
        return _fitness_score(metrics)

    result = ga.run_ga(
        fitness_fn=fitness_fn,
        genome_length=search_space.genome_length(strategy_key),
        config=ga_config,
        cache=cache,
    )
    best_params = search_space.decode(result.best_genome, strategy_key)
    train_metrics = _evaluate(strategy_key, best_params, train_bars, cost_per_turnover)
    test_metrics = _evaluate(strategy_key, best_params, test_bars, cost_per_turnover)
    default_test_metrics = _evaluate(strategy_key, {}, test_bars, cost_per_turnover)

    return OptimizationRecord(
        strategy=strategy_key,
        train_year=int(train_bars.index[0].year),
        test_year=int(test_bars.index[0].year),
        parameters=best_params,
        train_metrics=train_metrics,
        test_metrics=test_metrics,
        train_fitness=result.best_fitness,
        ga_config={
            "population_size": ga_config.population_size,
            "generations": ga_config.generations,
            "elite_count": ga_config.elite_count,
            "tournament_size": ga_config.tournament_size,
            "mutation_rate": ga_config.mutation_rate,
            "mutation_scale": ga_config.mutation_scale,
            "seed": ga_config.seed,
        },
        default_test_metrics=default_test_metrics,
    )


def save_record(record: OptimizationRecord, outputs_dir: Path = OUTPUTS_DIR) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    path = outputs_dir / f"optimized_{record.strategy}.json"
    path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
    return path


def load_record(strategy_key: str, outputs_dir: Path = OUTPUTS_DIR) -> OptimizationRecord:
    path = outputs_dir / f"optimized_{strategy_key}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["parameters"] = search_space.normalize_params(strategy_key, payload["parameters"])
    return OptimizationRecord(**payload)


def load_all_optimized(outputs_dir: Path = OUTPUTS_DIR) -> dict[str, OptimizationRecord]:
    records: dict[str, OptimizationRecord] = {}
    for key in STRATEGY_KEYS:
        path = outputs_dir / f"optimized_{key}.json"
        if path.is_file():
            records[key] = load_record(key, outputs_dir)
    return records


def _print_record(record: OptimizationRecord) -> None:
    print(f"=== {record.strategy} ===")
    print(f"  parameters     : {record.parameters}")
    print(f"  train fitness  : {record.train_fitness:+.3f}")
    print(f"  train sharpe   : {record.train_metrics.get('sharpe', float('nan')):+.3f}")
    print(f"  test sharpe    : {record.test_metrics.get('sharpe', float('nan')):+.3f}")
    print(f"  default sharpe : {record.default_test_metrics.get('sharpe', float('nan')):+.3f}")
    uplift = record.test_metrics.get("sharpe", 0.0) - record.default_test_metrics.get("sharpe", 0.0)
    print(f"  test uplift    : {uplift:+.3f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="GA parameter optimization for S1–S3.")
    parser.add_argument("--train-year", type=int, default=2023)
    parser.add_argument("--test-year", type=int, default=2024)
    parser.add_argument("--cost-per-turnover", type=float, default=0.00002)
    parser.add_argument("--population", type=int, default=24)
    parser.add_argument("--generations", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--strategy",
        choices=sorted(STRATEGY_KEYS),
        default=None,
        help="Optimize a single strategy (default: all three).",
    )
    args = parser.parse_args()

    if args.train_year == args.test_year:
        raise SystemExit("train-year and test-year must differ")

    train_bars = data.load_bars("EURUSD", years=[args.train_year])
    test_bars = data.load_bars("EURUSD", years=[args.test_year])
    print(f"Train year: {args.train_year} ({len(train_bars):,} bars)")
    print(f"Test year : {args.test_year} ({len(test_bars):,} bars)")
    print(f"cost_per_turnover={args.cost_per_turnover}")
    print()

    ga_config = ga.GAConfig(
        population_size=args.population,
        generations=args.generations,
        seed=args.seed,
    )
    keys = [args.strategy] if args.strategy else sorted(STRATEGY_KEYS)

    for key in keys:
        print(f"Optimizing {key} ...")
        record = optimize_strategy(key, train_bars, test_bars, args.cost_per_turnover, ga_config)
        path = save_record(record)
        print(f"Saved {path}")
        _print_record(record)


if __name__ == "__main__":
    main()
