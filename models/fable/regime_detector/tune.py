"""Walk-forward threshold tuning per §7 of MARKET_REGIME_DETECTION.md.

Protocol:
  1. Grid-search thresholds on TRAIN (2003-2015); rank by the economic
     objective (next-bar trend-following log-return per year) subject to
     stability constraints.
  2. Confirm the top TRAIN configs on VALIDATION (2016-2020); pick the final
     config among them.
  3. Run TEST (2021-2025) exactly once with the final config.

Usage: uv run python tune.py [--symbol EURUSD]
"""

import argparse
import itertools
import time
from pathlib import Path

import numpy as np
import pandas as pd

from classifier import Thresholds, confirm, raw_signals
from data import load_minute_bars, resample_bars
from features import compute_features

TRAIN = (2003, 2015)
VALIDATION = (2016, 2020)
TEST = (2021, 2025)

TIMEFRAMES = {"H1": ("1h", 24), "H4": ("4h", 6)}

GRID = {
    "adx_enter": [22.0, 25.0, 28.0, 32.0],
    "adx_gap": [5.0, 8.0],  # adx_exit = adx_enter - adx_gap
    "er_enter": [0.25, 0.30, 0.40],
    "slope_min": [0.0, 0.25, 0.50],
    "confirm_bars": [2, 3, 5],
}

# Stability constraints (§7.2): applied on TRAIN before ranking.
MAX_CHANGES_PER_DAY = 1.0
MIN_MEDIAN_DURATION_HOURS = 24.0
TREND_SHARE_BOUNDS = (0.15, 0.65)
SHORTLIST = 5


def period_metrics(
    dirs: np.ndarray, ret: np.ndarray, years: np.ndarray, period: tuple[int, int], bars_per_day: int
) -> dict:
    """Economic + stability metrics of a direction labeling within a year range."""
    mask = (years >= period[0]) & (years <= period[1])
    d = dirs[mask].astype(np.float64)
    r = ret[mask]
    r_next = np.append(r[1:], np.nan)  # label at t is traded on bar t+1
    n_years = period[1] - period[0] + 1

    trend = d != 0
    change_idx = np.flatnonzero(np.diff(d) != 0)
    run_lengths = np.diff(np.concatenate(([0], change_idx + 1, [len(d)])))

    with np.errstate(invalid="ignore"):
        mar_trend = np.nanmean(np.abs(r[trend])) if trend.any() else np.nan
        mar_range = np.nanmean(np.abs(r[~trend])) if (~trend).any() else np.nan
    return {
        "tf_ret_yr": float(np.nansum(d * r_next) / n_years),
        "trend_share": float(trend.mean()),
        "changes_day": float(len(change_idx) / (len(d) / bars_per_day)),
        "med_dur_h": float(np.median(run_lengths) * 24.0 / bars_per_day),
        "mar_ratio": float(mar_trend / mar_range),
    }


def passes_constraints(m: dict) -> bool:
    return (
        m["changes_day"] <= MAX_CHANGES_PER_DAY
        and m["med_dur_h"] >= MIN_MEDIAN_DURATION_HOURS
        and TREND_SHARE_BOUNDS[0] <= m["trend_share"] <= TREND_SHARE_BOUNDS[1]
    )


def fmt(m: dict) -> str:
    return (
        f"ret/yr {m['tf_ret_yr']:+.4f}  trend {m['trend_share']:5.1%}  "
        f"chg/day {m['changes_day']:.2f}  med_dur {m['med_dur_h']:5.0f}h  "
        f"|ret| trend/range {m['mar_ratio']:.2f}"
    )


def config_label(row: dict) -> str:
    return (
        f"{row['timeframe']} adx {row['adx_enter']:.0f}/{row['adx_enter'] - row['adx_gap']:.0f} "
        f"er {row['er_enter']:.2f} slope {row['slope_min']:.2f} confirm {row['confirm_bars']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="EURUSD")
    args = parser.parse_args()

    years = list(range(TRAIN[0], TEST[1] + 1))
    print(f"Loading {args.symbol} minute bars {years[0]}-{years[-1]} ...")
    t0 = time.time()
    minute = load_minute_bars(args.symbol, years)
    print(f"{len(minute):,} minute bars loaded in {time.time() - t0:.0f}s")

    rows = []
    for tf_name, (rule, bars_per_day) in TIMEFRAMES.items():
        bars = resample_bars(minute, rule)
        feats = compute_features(bars, bars_per_day=bars_per_day)
        ret = feats["ret"].to_numpy(dtype=np.float64)
        bar_years = feats.index.year.to_numpy()
        print(f"{tf_name}: {len(feats):,} bars, searching {np.prod([len(v) for v in GRID.values()])} configs ...")

        for combo in itertools.product(*GRID.values()):
            cfg = dict(zip(GRID.keys(), combo))
            th = Thresholds(
                adx_enter=cfg["adx_enter"],
                adx_exit=cfg["adx_enter"] - cfg["adx_gap"],
                er_enter=cfg["er_enter"],
                slope_min=cfg["slope_min"],
                confirm_bars=cfg["confirm_bars"],
            )
            dirs, _ = confirm(raw_signals(feats, th), th.confirm_bars)
            row = {"timeframe": tf_name, **cfg}
            for name, period in (("train", TRAIN), ("val", VALIDATION)):
                m = period_metrics(dirs, ret, bar_years, period, bars_per_day)
                row.update({f"{name}_{k}": v for k, v in m.items()})
            rows.append(row)

    results = pd.DataFrame(rows)
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    results.to_csv(out_dir / f"tuning_{args.symbol}.csv", index=False, float_format="%.6f")

    ok = results[
        results.apply(
            lambda r: passes_constraints({k[6:]: v for k, v in r.items() if k.startswith("train_")}),
            axis=1,
        )
    ]
    print(f"\n{len(ok)}/{len(results)} configs pass stability constraints on TRAIN")
    top = ok.sort_values("train_tf_ret_yr", ascending=False).head(SHORTLIST)

    print(f"\n=== Top {SHORTLIST} by TRAIN objective (selection uses TRAIN only) ===")
    for _, row in top.iterrows():
        tm = {k[6:]: v for k, v in row.items() if k.startswith("train_")}
        vm = {k[4:]: v for k, v in row.items() if k.startswith("val_")}
        print(f"{config_label(row)}\n    train: {fmt(tm)}\n    val:   {fmt(vm)}")

    # Final pick: among the TRAIN shortlist, the best VALIDATION objective that
    # also passes constraints on VALIDATION.
    viable = top[
        top.apply(
            lambda r: passes_constraints({k[4:]: v for k, v in r.items() if k.startswith("val_")}),
            axis=1,
        )
    ]
    if viable.empty:
        print("\nNo shortlisted config passes constraints on VALIDATION — do not proceed to TEST.")
        return
    final = viable.sort_values("val_tf_ret_yr", ascending=False).iloc[0]
    print(f"\n=== Final config: {config_label(final)} ===")

    rule, bars_per_day = TIMEFRAMES[final["timeframe"]]
    feats = compute_features(resample_bars(minute, rule), bars_per_day=bars_per_day)
    th = Thresholds(
        adx_enter=final["adx_enter"],
        adx_exit=final["adx_enter"] - final["adx_gap"],
        er_enter=final["er_enter"],
        slope_min=final["slope_min"],
        confirm_bars=int(final["confirm_bars"]),
    )
    dirs, _ = confirm(raw_signals(feats, th), th.confirm_bars)
    m = period_metrics(
        dirs,
        feats["ret"].to_numpy(dtype=np.float64),
        feats.index.year.to_numpy(),
        TEST,
        bars_per_day,
    )
    print(f"TEST {TEST[0]}-{TEST[1]} (single run): {fmt(m)}")


if __name__ == "__main__":
    main()
