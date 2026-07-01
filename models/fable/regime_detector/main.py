"""Label a year of EUR/USD with market regimes and print sanity metrics.

Usage: uv run python main.py [--symbol EURUSD] [--year 2025] [--warmup-years 1]
"""

import argparse
from pathlib import Path

from classifier import Thresholds, classify
from data import load_minute_bars, resample_h1
from evaluate import summarize
from features import compute_features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument(
        "--warmup-years",
        type=int,
        default=1,
        help="prior years loaded only to warm up rolling indicators",
    )
    args = parser.parse_args()

    years = list(range(args.year - args.warmup_years, args.year + 1))
    print(f"Loading {args.symbol} minute bars for {years} ...")
    minute = load_minute_bars(args.symbol, years)
    bars = resample_h1(minute)
    print(f"{len(minute):,} minute bars -> {len(bars):,} H1 bars")

    bars = compute_features(bars)
    regimes = classify(bars, Thresholds())

    # Report only on the target year; earlier years are indicator warmup.
    mask = bars.index.year == args.year
    bars_y, regimes_y = bars[mask], regimes[mask]

    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"regimes_{args.symbol}_{args.year}.csv"
    regimes_y.join(bars_y[["close", "adx", "er", "slope_norm", "atr_pct"]]).to_csv(
        out_path, index_label="time_open", float_format="%.6f"
    )
    print(f"Wrote {len(regimes_y):,} labeled bars to {out_path}\n")

    print(f"=== {args.symbol} {args.year} regime summary ===")
    print(summarize(bars_y, regimes_y))


if __name__ == "__main__":
    main()
