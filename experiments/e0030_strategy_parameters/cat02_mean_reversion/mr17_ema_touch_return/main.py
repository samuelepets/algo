"""MR-17 EMA Touch Return parameter search."""

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

from backtest import EXIT_EMA_TOUCH, EXIT_HALF_DISTANCE, MAX_HOLD_BARS, search_range
from indicators import ADX_PERIOD, ATR_PERIOD, EMA_PERIODS, atr, adx, build_ema_cache

DISTANCE_THRESH_ATR = [0.5, 1.0, 1.5, 2.0]
ADX_MAXES = [15, 20, 25]
ATR_STOP_MULTS = [0.5, 1.0, 1.5]
EXIT_TYPES = [EXIT_EMA_TOUCH, EXIT_HALF_DISTANCE]
TIMEFRAMES = [5, 15]

_EXIT_LABELS = {EXIT_EMA_TOUCH: "ema_touch", EXIT_HALF_DISTANCE: "half_distance"}


@dataclass
class Params:
    ema_period: int
    distance_thresh_atr: float
    adx_max: int
    atr_stop_mult: float
    exit_type: int
    tf_min: int


@dataclass
class TfData:
    tf_min: int
    bars: BarArrays
    ema_matrix: np.ndarray
    ema_index: dict[int, int]
    atr_vals: np.ndarray
    adx_vals: np.ndarray
    grid: list[Params]
    ema_rows: np.ndarray
    distance_thresh_atr: np.ndarray
    adx_max: np.ndarray
    atr_stop_mult: np.ndarray
    exit_type: np.ndarray
    max_hold_bars: np.ndarray
    warm_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for ema_p in EMA_PERIODS:
        for dist_t in DISTANCE_THRESH_ATR:
            for adx_m in ADX_MAXES:
                for atr_m in ATR_STOP_MULTS:
                    for exit_t in EXIT_TYPES:
                        grid.append(
                            Params(
                                ema_period=ema_p,
                                distance_thresh_atr=dist_t,
                                adx_max=adx_m,
                                atr_stop_mult=atr_m,
                                exit_type=exit_t,
                                tf_min=tf_min,
                            )
                        )
    return grid


def _grid_arrays(grid: list[Params], ema_index: dict[int, int]) -> tuple[np.ndarray, ...]:
    n = len(grid)
    ema_rows = np.empty(n, dtype=np.int64)
    distance_thresh_atr = np.empty(n, dtype=np.float64)
    adx_max = np.empty(n, dtype=np.float64)
    atr_stop_mult = np.empty(n, dtype=np.float64)
    exit_type = np.empty(n, dtype=np.int64)
    max_hold_bars = np.empty(n, dtype=np.int64)
    warm_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        ema_rows[i] = ema_index[p.ema_period]
        distance_thresh_atr[i] = p.distance_thresh_atr
        adx_max[i] = float(p.adx_max)
        atr_stop_mult[i] = p.atr_stop_mult
        exit_type[i] = p.exit_type
        max_hold_bars[i] = MAX_HOLD_BARS
        warm_bars[i] = max(p.ema_period, ATR_PERIOD, ADX_PERIOD * 2) + 1
    return (
        ema_rows, distance_thresh_atr, adx_max, atr_stop_mult, exit_type,
        max_hold_bars, warm_bars,
    )


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    ema_matrix, ema_index = build_ema_cache(bars_tf.close, EMA_PERIODS)
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    adx_vals = adx(bars_tf.high, bars_tf.low, bars_tf.close, ADX_PERIOD)
    grid = build_grid(tf_min)
    (
        ema_rows, distance_thresh_atr, adx_max, atr_stop_mult, exit_type,
        max_hold_bars, warm_bars,
    ) = _grid_arrays(grid, ema_index)
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        ema_matrix=ema_matrix,
        ema_index=ema_index,
        atr_vals=atr_vals,
        adx_vals=adx_vals,
        grid=grid,
        ema_rows=ema_rows,
        distance_thresh_atr=distance_thresh_atr,
        adx_max=adx_max,
        atr_stop_mult=atr_stop_mult,
        exit_type=exit_type,
        max_hold_bars=max_hold_bars,
        warm_bars=warm_bars,
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
        tf.ema_matrix,
        tf.atr_vals,
        tf.adx_vals,
        tf.ema_rows,
        tf.distance_thresh_atr,
        tf.adx_max,
        tf.atr_stop_mult,
        tf.exit_type,
        tf.max_hold_bars,
        tf.warm_bars,
        s,
        e,
        out_sharpe,
        out_pf,
        out_mdd,
        out_ret,
        out_ntrades,
    )

    return [
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
        for i, params in enumerate(tf.grid)
    ]


def _eval_single(tf: TfData, params: Params, start_ts: int, end_ts: int) -> Metrics:
    s, e = ts_range(tf.bars.ts, start_ts, end_ts)
    out_sharpe = np.empty(1, dtype=np.float64)
    out_pf = np.empty(1, dtype=np.float64)
    out_mdd = np.empty(1, dtype=np.float64)
    out_ret = np.empty(1, dtype=np.float64)
    out_ntrades = np.empty(1, dtype=np.int64)

    warm = max(params.ema_period, ATR_PERIOD, ADX_PERIOD * 2) + 1

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.ema_matrix,
        tf.atr_vals,
        tf.adx_vals,
        np.array([tf.ema_index[params.ema_period]], dtype=np.int64),
        np.array([params.distance_thresh_atr], dtype=np.float64),
        np.array([float(params.adx_max)], dtype=np.float64),
        np.array([params.atr_stop_mult], dtype=np.float64),
        np.array([params.exit_type], dtype=np.int64),
        np.array([MAX_HOLD_BARS], dtype=np.int64),
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
            "mr17_ema_touch_return/"
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
            "ema_period,distance_thresh_atr,adx_max,atr_stop_mult,exit_type,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.ema_period},{p.distance_thresh_atr:.2f},{p.adx_max},"
                f"{p.atr_stop_mult:.2f},{_EXIT_LABELS[p.exit_type]},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'ema':<4} {'dist':<5} {'adx<':<5} {'stop':<5} {'exit':<14} {'tf':<4}  "
        f"{'sharpe':>8}  {'pf':>7}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{p.ema_period:<4} {p.distance_thresh_atr:<5.1f} {p.adx_max:<5} "
            f"{p.atr_stop_mult:<5.1f} {_EXIT_LABELS[p.exit_type]:<14} {p.tf_min:<4}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>7.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_ema_period,sel_distance_thresh_atr,sel_adx_max,"
            "sel_atr_stop_mult,sel_exit_type,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<50}  "
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

            exit_lbl = _EXIT_LABELS[sel_params.exit_type]
            selected_label = (
                f"ema{sel_params.ema_period} dist{sel_params.distance_thresh_atr:.1f} "
                f"adx<{sel_params.adx_max} stop{sel_params.atr_stop_mult:.1f}x "
                f"{exit_lbl} {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<50}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>7.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.ema_period},{sel_params.distance_thresh_atr:.2f},"
                f"{sel_params.adx_max},{sel_params.atr_stop_mult:.2f},{exit_lbl},"
                f"{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
