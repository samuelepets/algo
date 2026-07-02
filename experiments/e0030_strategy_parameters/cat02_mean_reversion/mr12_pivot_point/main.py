"""MR-12 Pivot Point Reversion parameter search."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

# Must be set before any Numba import to direct .nbc/.nbi cache files.
os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

import numpy as np

from algo_shared.constants import MIN_TRADES, WALK_FORWARD_WINDOWS
from algo_shared.data import BarArrays, load_eurusd, resample, ts_range, year_start_ts
from algo_shared.metrics import Metrics

from backtest import FADE_S1_R1, FADE_S2_R2, TARGET_MID, TARGET_P, search_range
from indicators import ATR_PERIOD, PIVOT_DAILY, PIVOT_WEEKLY, atr, build_pivot_cache

PIVOT_PERIODS = [PIVOT_DAILY, PIVOT_WEEKLY]
FADE_LEVELS = [FADE_S1_R1, FADE_S2_R2]
TOUCH_ATR_THRESHOLDS = [0.25, 0.5, 0.75, 1.0]
TARGET_MODES = [TARGET_P, TARGET_MID]
ATR_STOP_MULTS = [0.5, 1.0, 1.5]
TIMEFRAMES = [5, 15]

_PIVOT_LABELS = {PIVOT_DAILY: "daily", PIVOT_WEEKLY: "weekly"}
_FADE_LABELS = {FADE_S1_R1: "S1/R1", FADE_S2_R2: "S2/R2"}
_TARGET_LABELS = {TARGET_P: "P", TARGET_MID: "mid_SR1_P"}


@dataclass
class Params:
    pivot_period: int
    fade_level: int
    touch_atr_thresh: float
    target_mode: int
    atr_stop_mult: float
    tf_min: int


@dataclass
class TfData:
    tf_min: int
    bars: BarArrays
    pivot_cache: dict[int, tuple[np.ndarray, ...]]
    atr_vals: np.ndarray
    grid: list[Params]
    pivot_period: np.ndarray
    fade_level: np.ndarray
    touch_atr_thresh: np.ndarray
    target_mode: np.ndarray
    atr_stop_mult: np.ndarray
    warm_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for pivot_p in PIVOT_PERIODS:
        for fade in FADE_LEVELS:
            for touch in TOUCH_ATR_THRESHOLDS:
                for target in TARGET_MODES:
                    for atr_m in ATR_STOP_MULTS:
                        grid.append(
                            Params(
                                pivot_period=pivot_p,
                                fade_level=fade,
                                touch_atr_thresh=touch,
                                target_mode=target,
                                atr_stop_mult=atr_m,
                                tf_min=tf_min,
                            )
                        )
    return grid


def _grid_arrays(grid: list[Params]) -> tuple[np.ndarray, ...]:
    n = len(grid)
    pivot_period = np.empty(n, dtype=np.int64)
    fade_level = np.empty(n, dtype=np.int64)
    touch_atr_thresh = np.empty(n, dtype=np.float64)
    target_mode = np.empty(n, dtype=np.int64)
    atr_stop_mult = np.empty(n, dtype=np.float64)
    warm_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        pivot_period[i] = p.pivot_period
        fade_level[i] = p.fade_level
        touch_atr_thresh[i] = p.touch_atr_thresh
        target_mode[i] = p.target_mode
        atr_stop_mult[i] = p.atr_stop_mult
        # Weekly pivots need roughly a week of warm-up; daily need a bit
        # more than a day's worth of bars for the first prior bucket.
        warm_bars[i] = (10080 // p.tf_min) if p.pivot_period == PIVOT_WEEKLY else (1440 // p.tf_min) + 2
    return pivot_period, fade_level, touch_atr_thresh, target_mode, atr_stop_mult, warm_bars


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    pivot_cache = build_pivot_cache(bars_tf.ts, bars_tf.high, bars_tf.low, bars_tf.close)
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    pivot_period, fade_level, touch_atr_thresh, target_mode, atr_stop_mult, warm_bars = (
        _grid_arrays(grid)
    )
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        pivot_cache=pivot_cache,
        atr_vals=atr_vals,
        grid=grid,
        pivot_period=pivot_period,
        fade_level=fade_level,
        touch_atr_thresh=touch_atr_thresh,
        target_mode=target_mode,
        atr_stop_mult=atr_stop_mult,
        warm_bars=warm_bars,
    )


def _run_search(tf: TfData, start_ts: int, end_ts: int) -> list[tuple[Params, Metrics]]:
    s, e = ts_range(tf.bars.ts, start_ts, end_ts)
    results: list[tuple[Params, Metrics]] = []

    # The two pivot periods use different underlying arrays, not a shared
    # matrix indexed by row -- split the grid by pivot_period and run each
    # slice of the grid against its own precomputed pivot arrays.
    for pivot_p in PIVOT_PERIODS:
        idx = [i for i, g in enumerate(tf.grid) if g.pivot_period == pivot_p]
        if not idx:
            continue
        idx_arr = np.array(idx, dtype=np.int64)
        n = len(idx)
        out_sharpe = np.empty(n, dtype=np.float64)
        out_pf = np.empty(n, dtype=np.float64)
        out_mdd = np.empty(n, dtype=np.float64)
        out_ret = np.empty(n, dtype=np.float64)
        out_ntrades = np.empty(n, dtype=np.int64)

        p_arr, r1_arr, r2_arr, s1_arr, s2_arr = tf.pivot_cache[pivot_p]

        search_range(
            tf.bars.close,
            tf.bars.high,
            tf.bars.low,
            tf.bars.ts,
            p_arr,
            r1_arr,
            r2_arr,
            s1_arr,
            s2_arr,
            tf.atr_vals,
            tf.fade_level[idx_arr],
            tf.touch_atr_thresh[idx_arr],
            tf.target_mode[idx_arr],
            tf.atr_stop_mult[idx_arr],
            tf.warm_bars[idx_arr],
            s,
            e,
            out_sharpe,
            out_pf,
            out_mdd,
            out_ret,
            out_ntrades,
        )

        for k, grid_i in enumerate(idx):
            results.append(
                (
                    tf.grid[grid_i],
                    Metrics(
                        sharpe=float(out_sharpe[k]),
                        profit_factor=float(out_pf[k]),
                        max_drawdown_r=float(out_mdd[k]),
                        total_return=float(out_ret[k]),
                        n_trades=int(out_ntrades[k]),
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

    warm = (10080 // params.tf_min) if params.pivot_period == PIVOT_WEEKLY else (1440 // params.tf_min) + 2
    p_arr, r1_arr, r2_arr, s1_arr, s2_arr = tf.pivot_cache[params.pivot_period]

    search_range(
        tf.bars.close,
        tf.bars.high,
        tf.bars.low,
        tf.bars.ts,
        p_arr,
        r1_arr,
        r2_arr,
        s1_arr,
        s2_arr,
        tf.atr_vals,
        np.array([params.fade_level], dtype=np.int64),
        np.array([params.touch_atr_thresh], dtype=np.float64),
        np.array([params.target_mode], dtype=np.int64),
        np.array([params.atr_stop_mult], dtype=np.float64),
        np.array([warm], dtype=np.int64),
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
            "Run from experiments/e0030_strategy_parameters/cat02_mean_reversion/"
            "mr12_pivot_point/"
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
            "pivot_period,fade_level,touch_atr_thresh,target,atr_stop_mult,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{_PIVOT_LABELS[p.pivot_period]},{_FADE_LABELS[p.fade_level]},"
                f"{p.touch_atr_thresh:.2f},{_TARGET_LABELS[p.target_mode]},"
                f"{p.atr_stop_mult:.2f},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'pivot':<7} {'fade':<6} {'touch':<6} {'target':<11} {'stop':<5} {'tf':<4}  "
        f"{'sharpe':>8}  {'pf':>7}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{_PIVOT_LABELS[p.pivot_period]:<7} {_FADE_LABELS[p.fade_level]:<6} "
            f"{p.touch_atr_thresh:<6.2f} {_TARGET_LABELS[p.target_mode]:<11} "
            f"{p.atr_stop_mult:<5.2f} {p.tf_min:<4}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>7.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_pivot_period,sel_fade_level,sel_touch_atr_thresh,sel_target,"
            "sel_atr_stop_mult,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<54}  "
            f"{'IS-Sh':>8}  {'OOS-Sh':>8}  {'OOS-PF':>7}  {'OOS-n':>7}"
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
                f"{_PIVOT_LABELS[sel_params.pivot_period]} {_FADE_LABELS[sel_params.fade_level]} "
                f"touch{sel_params.touch_atr_thresh:.2f} {_TARGET_LABELS[sel_params.target_mode]} "
                f"stop{sel_params.atr_stop_mult:.2f}x {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<54}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>7.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{_PIVOT_LABELS[sel_params.pivot_period]},{_FADE_LABELS[sel_params.fade_level]},"
                f"{sel_params.touch_atr_thresh:.2f},{_TARGET_LABELS[sel_params.target_mode]},"
                f"{sel_params.atr_stop_mult:.2f},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
