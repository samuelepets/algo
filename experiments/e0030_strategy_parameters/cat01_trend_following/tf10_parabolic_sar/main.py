"""TF-10 Parabolic SAR Trend-Following parameter search."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backtest import (
    EXIT_FAST_EMA,
    EXIT_SLOW_EMA,
    MODE_EXIT_ONLY,
    MODE_STANDALONE,
    search_range,
)
from data import BarArrays, load_eurusd, resample, ts_range, year_start_ts
from indicators import ema

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

AF_STARTS = [0.01, 0.02, 0.03, 0.05]
AF_STEPS = [0.01, 0.02, 0.03]
AF_MAXES = [0.10, 0.15, 0.20, 0.30]
MODES = [("standalone", MODE_STANDALONE), ("exit_only", MODE_EXIT_ONLY)]
TIMEFRAMES = [5, 15]
MIN_TRADES = 50

WALK_FORWARD_WINDOWS: list[tuple[int, int, int, int]] = [
    (2003, 2014, 2015, 2018),
    (2003, 2016, 2017, 2020),
    (2003, 2018, 2019, 2022),
    (2003, 2020, 2021, 2025),
]


@dataclass
class Params:
    af_start: float
    af_step: float
    af_max: float
    mode_label: str
    mode: int
    tf_min: int


@dataclass
class Metrics:
    sharpe: float
    profit_factor: float
    max_drawdown_r: float
    total_return: float
    n_trades: int


@dataclass
class TfData:
    tf_min: int
    bars: BarArrays
    ema_fast: np.ndarray
    ema_slow: np.ndarray
    grid: list[Params]
    af_start: np.ndarray
    af_step: np.ndarray
    af_max: np.ndarray
    mode: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for af_s in AF_STARTS:
        for af_step in AF_STEPS:
            for af_m in AF_MAXES:
                for mode_label, mode in MODES:
                    grid.append(
                        Params(
                            af_start=af_s,
                            af_step=af_step,
                            af_max=af_m,
                            mode_label=mode_label,
                            mode=mode,
                            tf_min=tf_min,
                        )
                    )
    return grid


def _grid_arrays(grid: list[Params]) -> tuple[np.ndarray, ...]:
    n = len(grid)
    af_start = np.empty(n, dtype=np.float64)
    af_step = np.empty(n, dtype=np.float64)
    af_max = np.empty(n, dtype=np.float64)
    mode = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        af_start[i] = p.af_start
        af_step[i] = p.af_step
        af_max[i] = p.af_max
        mode[i] = p.mode
    return af_start, af_step, af_max, mode


def _top_params_entry(p: Params, m: Metrics) -> dict[str, float | int | str]:
    return {
        "af_max": p.af_max,
        "af_start": p.af_start,
        "af_step": p.af_step,
        "max_drawdown_r": m.max_drawdown_r,
        "mode": p.mode_label,
        "n_trades": m.n_trades,
        "profit_factor": m.profit_factor,
        "sharpe": m.sharpe,
        "tf_min": p.tf_min,
        "total_return": m.total_return,
    }


def _format_top_params_json(rows: list[dict[str, float | int | str]]) -> str:
    return json.dumps(rows, indent=2, sort_keys=True)


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    ema_fast = ema(bars_tf.close, EXIT_FAST_EMA)
    ema_slow = ema(bars_tf.close, EXIT_SLOW_EMA)
    grid = build_grid(tf_min)
    af_start, af_step, af_max, mode = _grid_arrays(grid)
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        grid=grid,
        af_start=af_start,
        af_step=af_step,
        af_max=af_max,
        mode=mode,
    )


def _run_search(tf: TfData, start_ts: int, end_ts: int) -> list[tuple[Params, Metrics]]:
    s, e = ts_range(tf.bars.ts, start_ts, end_ts)
    n = len(tf.grid)
    out_sharpe = np.empty(n, dtype=np.float64)
    out_pf = np.empty(n, dtype=np.float64)
    out_mdd = np.empty(n, dtype=np.float64)
    out_ret = np.empty(n, dtype=np.float64)
    out_ntrades = np.empty(n, dtype=np.int64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.ema_fast,
        tf.ema_slow,
        tf.af_start,
        tf.af_step,
        tf.af_max,
        tf.mode,
        EXIT_SLOW_EMA,
        s,
        e,
        out_sharpe,
        out_pf,
        out_mdd,
        out_ret,
        out_ntrades,
    )

    results: list[tuple[Params, Metrics]] = []
    for i, params in enumerate(tf.grid):
        results.append(
            (
                params,
                Metrics(
                    sharpe=float(out_sharpe[i]),
                    profit_factor=float(out_pf[i]),
                    max_drawdown_r=float(out_mdd[i]),
                    total_return=float(out_ret[i]),
                    n_trades=int(out_ntrades[i]),
                ),
            )
        )
    return results


def _eval_single(tf: TfData, params: Params, start_ts: int, end_ts: int) -> Metrics:
    s, e = ts_range(tf.bars.ts, start_ts, end_ts)
    out_sharpe = np.empty(1, dtype=np.float64)
    out_pf = np.empty(1, dtype=np.float64)
    out_mdd = np.empty(1, dtype=np.float64)
    out_ret = np.empty(1, dtype=np.float64)
    out_ntrades = np.empty(1, dtype=np.int64)

    af_start = np.array([params.af_start], dtype=np.float64)
    af_step = np.array([params.af_step], dtype=np.float64)
    af_max = np.array([params.af_max], dtype=np.float64)
    mode = np.array([params.mode], dtype=np.int64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.ema_fast,
        tf.ema_slow,
        af_start,
        af_step,
        af_max,
        mode,
        EXIT_SLOW_EMA,
        s,
        e,
        out_sharpe,
        out_pf,
        out_mdd,
        out_ret,
        out_ntrades,
    )
    return Metrics(
        sharpe=float(out_sharpe[0]),
        profit_factor=float(out_pf[0]),
        max_drawdown_r=float(out_mdd[0]),
        total_return=float(out_ret[0]),
        n_trades=int(out_ntrades[0]),
    )


def main() -> None:
    data_dir = Path("../../../../data/bars/EURUSD")
    if not data_dir.exists():
        raise SystemExit(
            f"ERROR: Data directory not found at {data_dir.resolve()}\n"
            "Run from experiments/e0030_strategy_parameters/cat01_trend_following/"
            "tf10_parabolic_sar/"
        )

    outputs = Path("outputs")
    outputs.mkdir(exist_ok=True)

    t0 = time.perf_counter()
    print("Loading EURUSD 1-min bars...")
    bars_1min = load_eurusd(data_dir)
    load_secs = time.perf_counter() - t0
    years = bars_1min.ts.size / (252.0 * 1440.0)
    print(f"  {bars_1min.ts.size:,} bars  ({years:.2f} years)  [{load_secs:.1f}s]")
    if bars_1min.ts.size < 1_000_000:
        raise SystemExit(f"Expected >= 1 M bars; got {bars_1min.ts.size}")

    tf_data: list[TfData] = []
    for tf_min in TIMEFRAMES:
        print(f"\nTimeframe: {tf_min}-min")
        t1 = time.perf_counter()
        tf = _prepare_tf(bars_1min, tf_min)
        print(
            f"  {tf.bars.ts.size:,} bars  "
            f"grid={len(tf.grid):,}  [{time.perf_counter() - t1:.2f}s]"
        )
        tf_data.append(tf)

    all_results: list[tuple[Params, Metrics]] = []
    for tf in tf_data:
        print(
            f"\nTimeframe {tf.tf_min}-min: searching {len(tf.grid):,} combinations "
            "(numba parallel)..."
        )
        t2 = time.perf_counter()
        results = _run_search(tf, -(2**62), 2**62)
        print(f"  Done [{time.perf_counter() - t2:.2f}s]")
        all_results.extend(results)

    print("\nWriting outputs/results.csv...")
    results_path = outputs / "results.csv"
    with results_path.open("w", encoding="utf-8") as fh:
        fh.write(
            "af_start,af_step,af_max,mode,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.af_start:.2f},{p.af_step:.2f},{p.af_max:.2f},{p.mode_label},"
                f"{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'af_s':<6} {'af_st':<6} {'af_mx':<6} {'mode':<11} {'tf':<5}  "
        f"{'sharpe':>8}  {'pf':>8}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    top10 = []
    for p, m in valid[:10]:
        print(
            f"{p.af_start:<6.2f} {p.af_step:<6.2f} {p.af_max:<6.2f} {p.mode_label:<11} "
            f"{p.tf_min:<5}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>8.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )
        top10.append(_top_params_entry(p, m))

    top_path = outputs / "top_params.json"
    top_path.write_text(_format_top_params_json(top10), encoding="utf-8")
    print(f"\nSaved {top_path}")

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_af_start,sel_af_step,sel_af_max,sel_mode,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<30}  "
            f"{'IS-Sh':>8}  {'OOS-Sh':>8}  {'OOS-PF':>8}  {'OOS-n':>7}"
        )
        for idx, (is_s, is_e, oos_s, oos_e) in enumerate(WALK_FORWARD_WINDOWS):
            is_start = year_start_ts(is_s)
            is_end = year_start_ts(is_e + 1)
            oos_start = year_start_ts(oos_s)
            oos_end = year_start_ts(oos_e + 1)

            is_results: list[tuple[Params, Metrics]] = []
            for tf in tf_data:
                is_results.extend(_run_search(tf, is_start, is_end))

            is_results.sort(key=lambda x: x[1].sharpe, reverse=True)
            selected = next(
                ((p, m) for p, m in is_results if m.n_trades >= MIN_TRADES), None
            )
            if selected is None:
                print(f"  Window {idx + 1}: no valid IS combination — skipping.")
                continue

            sel_params, is_m = selected
            tf = next(t for t in tf_data if t.tf_min == sel_params.tf_min)
            oos_m = _eval_single(tf, sel_params, oos_start, oos_end)

            selected_label = (
                f"af{sel_params.af_start:.2f}/{sel_params.af_step:.2f}/"
                f"{sel_params.af_max:.2f} {sel_params.mode_label} {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<30}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>8.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.af_start:.2f},{sel_params.af_step:.2f},"
                f"{sel_params.af_max:.2f},{sel_params.mode_label},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
