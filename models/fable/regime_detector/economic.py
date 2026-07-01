"""§7.3 economic validation: does the regime filter add value to toy strategies?

For each toy strategy (EMA-crossover trend follower on H1, Bollinger-fade mean
reverter on H1) compare four variants:

  always   - strategy always enabled
  matched  - enabled only in its compatible direction regime
  opposite - enabled only in the incompatible regime (negative control)
  vol_off  - enabled except during VOL_HIGH (volatility circuit breaker)

Regimes come from the walk-forward-tuned H4 detector; each H4 label becomes
usable for H1 bars only from its `time_close` onward (no leakage).

Usage: uv run python economic.py [--symbol EURUSD]
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from classifier import Thresholds, classify
from data import load_minute_bars, resample_bars
from features import compute_features
from strategies import bollinger_fade_positions, ema_crossover_positions, strategy_returns

# Final config selected by tune.py (train 2003-2015, confirmed on 2016-2020).
FINAL_TH = Thresholds(adx_enter=28.0, adx_exit=23.0, er_enter=0.40, slope_min=0.0, confirm_bars=5)
PERIODS = {"train 2003-2015": (2003, 2015), "val 2016-2020": (2016, 2020), "test 2021-2025": (2021, 2025)}


def h4_regimes_on_h1(minute: pd.DataFrame, h1_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Label H1 bars with the latest H4 regime available at each bar's open."""
    h4 = compute_features(resample_bars(minute, "4h"), bars_per_day=6)
    regimes = classify(h4, FINAL_TH)
    regimes = regimes.sort_values("time_close")
    aligned = pd.merge_asof(
        pd.DataFrame(index=h1_index).reset_index(names="time"),
        regimes[["time_close", "direction", "volatility"]],
        left_on="time",
        right_on="time_close",
        direction="backward",
        allow_exact_matches=True,
    ).set_index("time")
    return aligned[["direction", "volatility"]]


def period_stats(strat_ret: pd.Series, pos: pd.Series, period: tuple[int, int]) -> dict:
    mask = (strat_ret.index.year >= period[0]) & (strat_ret.index.year <= period[1])
    r = strat_ret[mask].dropna()
    n_years = period[1] - period[0] + 1
    bars_per_year = len(r) / n_years
    equity = r.cumsum()
    drawdown = equity - equity.cummax()
    sharpe = r.mean() / r.std() * np.sqrt(bars_per_year) if r.std() > 0 else 0.0
    return {
        "ret_yr": float(r.sum() / n_years),
        "sharpe": float(sharpe),
        "max_dd": float(drawdown.min()),
        "in_mkt": float((pos.shift(1)[mask].abs() > 0).mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="EURUSD")
    args = parser.parse_args()

    years = list(range(2003, 2026))
    print(f"Loading {args.symbol} minute bars {years[0]}-{years[-1]} ...")
    minute = load_minute_bars(args.symbol, years)
    h1 = resample_bars(minute, "1h")
    regimes = h4_regimes_on_h1(minute, h1.index)

    in_trend = regimes["direction"].isin(["TREND_UP", "TREND_DOWN"])
    in_range = regimes["direction"] == "RANGE"
    vol_ok = regimes["volatility"] != "VOL_HIGH"

    strategies = {
        "EMA crossover (trend)": {
            "raw": ema_crossover_positions(h1["close"]),
            "matched": in_trend,
            "opposite": in_range,
        },
        "Bollinger fade (mean-rev)": {
            "raw": bollinger_fade_positions(h1["close"]),
            "matched": in_range,
            "opposite": in_trend,
        },
    }

    rows = []
    for strat_name, spec in strategies.items():
        raw = spec["raw"]
        variants = {
            "always": raw,
            "matched": raw * spec["matched"].astype(float),
            "opposite": raw * spec["opposite"].astype(float),
            "vol_off": raw * vol_ok.astype(float),
        }
        for var_name, pos in variants.items():
            strat_ret = strategy_returns(h1["close"], pos)
            for period_name, period in PERIODS.items():
                stats = period_stats(strat_ret, pos, period)
                rows.append(
                    {"strategy": strat_name, "variant": var_name, "period": period_name, **stats}
                )

    results = pd.DataFrame(rows)
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    results.to_csv(out_dir / f"economic_{args.symbol}.csv", index=False, float_format="%.6f")

    for strat_name in strategies:
        print(f"\n=== {strat_name} ===")
        sub = results[results["strategy"] == strat_name]
        print(f"{'variant':<10} {'period':<16} {'ret/yr':>8} {'sharpe':>7} {'maxDD':>8} {'in mkt':>7}")
        for _, r in sub.iterrows():
            print(
                f"{r['variant']:<10} {r['period']:<16} {r['ret_yr']:+8.4f} {r['sharpe']:7.2f} "
                f"{r['max_dd']:+8.4f} {r['in_mkt']:6.1%}"
            )


if __name__ == "__main__":
    main()
