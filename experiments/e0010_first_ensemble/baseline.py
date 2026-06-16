"""Run S1–S3 baseline backtests on EUR/USD and print per-strategy metrics."""

from __future__ import annotations

import argparse
from pathlib import Path

import backtest
import data
from optimize import load_all_optimized
from strategies import ALL_STRATEGIES, STRATEGY_KEYS, strategy_from_key


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest base strategies on EUR/USD.")
    parser.add_argument("--start-year", type=int, default=2024)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument(
        "--cost-per-turnover",
        type=float,
        default=0.00002,
        help="Transaction cost per unit position change (e.g. 0.00002 ≈ 0.2 bp).",
    )
    parser.add_argument(
        "--optimized",
        action="store_true",
        help="Use GA-optimized parameters from outputs/optimized_*.json.",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory containing optimized_*.json files.",
    )
    args = parser.parse_args()

    bars = data.load_bars("EURUSD", start_year=args.start_year, end_year=args.end_year)
    print(f"EUR/USD bars: {len(bars):,} ({args.start_year}–{args.end_year})")
    print(f"cost_per_turnover={args.cost_per_turnover}")
    if args.optimized:
        print(f"mode=optimized (from {args.outputs_dir})")
    print()

    if args.optimized:
        records = load_all_optimized(args.outputs_dir)
        missing = sorted(set(STRATEGY_KEYS) - set(records))
        if missing:
            raise SystemExit(f"Missing optimized records for: {', '.join(missing)}")
        strategies = [strategy_from_key(key, records[key].parameters) for key in sorted(STRATEGY_KEYS)]
    else:
        strategies = ALL_STRATEGIES

    for strategy in strategies:
        signal = strategy.generate_signal(bars)
        result = backtest.backtest(bars, signal, cost_per_turnover=args.cost_per_turnover)
        m = result.metrics
        print(strategy.name)
        print(f"  total_return : {m['total_return']:+.4f}")
        print(f"  sharpe       : {m['sharpe']:+.3f}")
        print(f"  max_drawdown : {m['max_drawdown']:+.4f}")
        print(f"  hit_rate     : {m['hit_rate']:.3f}")
        print(f"  ann_turnover : {m['ann_turnover']:.1f}")
        print()


if __name__ == "__main__":
    main()
