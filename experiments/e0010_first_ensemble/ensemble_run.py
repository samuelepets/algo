"""Run ensemble variants and compare against individual base strategies."""

from __future__ import annotations

import argparse

import backtest
import data
import ensemble
from strategies import ALL_STRATEGIES


def _print_metrics(name: str, metrics: dict[str, float]) -> None:
    print(name)
    print(f"  total_return : {metrics['total_return']:+.4f}")
    print(f"  sharpe       : {metrics['sharpe']:+.3f}")
    print(f"  max_drawdown : {metrics['max_drawdown']:+.4f}")
    print(f"  hit_rate     : {metrics['hit_rate']:.3f}")
    print(f"  ann_turnover : {metrics['ann_turnover']:.1f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest ensemble variants on EUR/USD.")
    parser.add_argument("--start-year", type=int, default=2024)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--cost-per-turnover", type=float, default=0.00002)
    parser.add_argument(
        "--inv-vol-window",
        type=int,
        default=1440,
        help="Rolling window (bars) for inverse-vol weighting.",
    )
    args = parser.parse_args()

    bars = data.load_bars("EURUSD", start_year=args.start_year, end_year=args.end_year)
    print(f"EUR/USD bars: {len(bars):,} ({args.start_year}–{args.end_year})")
    print(f"cost_per_turnover={args.cost_per_turnover}")
    print()

    signals: dict[str, object] = {}
    returns: dict[str, object] = {}
    base_metrics: dict[str, dict[str, float]] = {}

    print("=== Base strategies ===")
    for strategy in ALL_STRATEGIES:
        sig = strategy.generate_signal(bars)
        result = backtest.backtest(bars, sig, cost_per_turnover=args.cost_per_turnover)
        signals[strategy.name] = sig
        returns[strategy.name] = result.returns
        base_metrics[strategy.name] = result.metrics
        _print_metrics(strategy.name, result.metrics)

    print("=== Return-stream correlations ===")
    corr = ensemble.return_correlation_matrix(returns)
    print(corr.to_string(float_format=lambda x: f"{x:+.3f}"))
    print()

    sig_list = [signals[s.name] for s in ALL_STRATEGIES]
    ret_list = [returns[s.name] for s in ALL_STRATEGIES]

    ensembles = {
        "E_majority_vote": ensemble.majority_vote(sig_list),
        "E_averaged": ensemble.averaged_signal(sig_list),
        "E_inverse_vol": ensemble.inverse_vol_weighted_signal(
            sig_list, ret_list, window=args.inv_vol_window
        ),
    }

    print("=== Ensemble variants ===")
    ensemble_metrics: dict[str, dict[str, float]] = {}
    for name, sig in ensembles.items():
        result = backtest.backtest(bars, sig, cost_per_turnover=args.cost_per_turnover)
        ensemble_metrics[name] = result.metrics
        _print_metrics(name, result.metrics)

    print("=== Sharpe comparison ===")
    all_sharpes = {
        **{n: m["sharpe"] for n, m in base_metrics.items()},
        **{n: m["sharpe"] for n, m in ensemble_metrics.items()},
    }
    best = max(all_sharpes, key=all_sharpes.get)  # type: ignore[arg-type]
    for name, sharpe in all_sharpes.items():
        tag = "  <-- best" if name == best else ""
        print(f"  {name:22s}  sharpe={sharpe:+.3f}{tag}")


if __name__ == "__main__":
    main()
