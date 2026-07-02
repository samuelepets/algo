"""MR-04 Z-Score Statistical Reversion parameter search."""

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

from backtest import INPUT_CLOSE_DETRENDED, INPUT_LOG_RETURN, search_range
from indicators import ATR_PERIOD, ZSCORE_WINDOWS, atr, build_zscore_cache

ENTRY_THRESHOLDS = [1.5, 2.0, 2.5, 3.0]
EXIT_THRESHOLDS = [0.0, 0.5]
ATR_STOP_MULTS = [0.75, 1.0, 1.5, 2.0]
INPUT_TYPES = [INPUT_LOG_RETURN, INPUT_CLOSE_DETRENDED]
TIMEFRAMES = [5, 15]

_INPUT_LABELS = {INPUT_LOG_RETURN: "log_return", INPUT_CLOSE_DETRENDED: "close_detrended"}


@dataclass
class Params:
    zscore_window: int
    entry_threshold: float
    exit_threshold: float
    atr_stop_mult: float
    input_type: int
    tf_min: int


@dataclass
class TfData:
    tf_min: int
    bars: BarArrays
    log_return_matrix: np.ndarray
    close_detrended_matrix: np.ndarray
    atr_vals: np.ndarray
    window_index: dict[int, int]
    grid: list[Params]
    window_rows: np.ndarray
    input_type: np.ndarray
    entry_threshold: np.ndarray
    exit_threshold: np.ndarray
    atr_stop_mult: np.ndarray
    warm_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for window in ZSCORE_WINDOWS:
        for entry_t in ENTRY_THRESHOLDS:
            for exit_t in EXIT_THRESHOLDS:
                for atr_m in ATR_STOP_MULTS:
                    for input_t in INPUT_TYPES:
                        grid.append(
                            Params(
                                zscore_window=window,
                                entry_threshold=entry_t,
                                exit_threshold=exit_t,
                                atr_stop_mult=atr_m,
                                input_type=input_t,
                                tf_min=tf_min,
                            )
                        )
    return grid


def _grid_arrays(
    grid: list[Params], window_index: dict[int, int]
) -> tuple[np.ndarray, ...]:
    n = len(grid)
    window_rows = np.empty(n, dtype=np.int64)
    input_type = np.empty(n, dtype=np.int64)
    entry_threshold = np.empty(n, dtype=np.float64)
    exit_threshold = np.empty(n, dtype=np.float64)
    atr_stop_mult = np.empty(n, dtype=np.float64)
    warm_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        window_rows[i] = window_index[p.zscore_window]
        input_type[i] = p.input_type
        entry_threshold[i] = p.entry_threshold
        exit_threshold[i] = p.exit_threshold
        atr_stop_mult[i] = p.atr_stop_mult
        warm_bars[i] = p.zscore_window + 2
    return window_rows, input_type, entry_threshold, exit_threshold, atr_stop_mult, warm_bars


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    log_return_matrix, close_detrended_matrix, window_index = build_zscore_cache(
        bars_tf.close, ZSCORE_WINDOWS
    )
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    window_rows, input_type, entry_threshold, exit_threshold, atr_stop_mult, warm_bars = (
        _grid_arrays(grid, window_index)
    )
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        log_return_matrix=log_return_matrix,
        close_detrended_matrix=close_detrended_matrix,
        atr_vals=atr_vals,
        window_index=window_index,
        grid=grid,
        window_rows=window_rows,
        input_type=input_type,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        atr_stop_mult=atr_stop_mult,
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
        tf.log_return_matrix,
        tf.close_detrended_matrix,
        tf.atr_vals,
        tf.window_rows,
        tf.input_type,
        tf.entry_threshold,
        tf.exit_threshold,
        tf.atr_stop_mult,
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

    warm = params.zscore_window + 2

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.log_return_matrix,
        tf.close_detrended_matrix,
        tf.atr_vals,
        np.array([tf.window_index[params.zscore_window]], dtype=np.int64),
        np.array([params.input_type], dtype=np.int64),
        np.array([params.entry_threshold], dtype=np.float64),
        np.array([params.exit_threshold], dtype=np.float64),
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
            "mr04_zscore_reversion/"
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
            "zscore_window,entry_threshold,exit_threshold,atr_stop_mult,input_type,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.zscore_window},{p.entry_threshold:.2f},{p.exit_threshold:.2f},"
                f"{p.atr_stop_mult:.2f},{_INPUT_LABELS[p.input_type]},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'win':<5} {'entry':<6} {'exit':<5} {'stop':<5} {'input':<16} {'tf':<4}  "
        f"{'sharpe':>8}  {'pf':>7}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{p.zscore_window:<5} {p.entry_threshold:<6.1f} {p.exit_threshold:<5.1f} "
            f"{p.atr_stop_mult:<5.2f} {_INPUT_LABELS[p.input_type]:<16} {p.tf_min:<4}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>7.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_zscore_window,sel_entry_threshold,sel_exit_threshold,"
            "sel_atr_stop_mult,sel_input_type,sel_tf,"
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

            input_lbl = _INPUT_LABELS[sel_params.input_type]
            selected_label = (
                f"w{sel_params.zscore_window} in{sel_params.entry_threshold:.1f} "
                f"out{sel_params.exit_threshold:.1f} stop{sel_params.atr_stop_mult:.2f}x "
                f"{input_lbl} {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<50}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>7.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.zscore_window},{sel_params.entry_threshold:.2f},"
                f"{sel_params.exit_threshold:.2f},{sel_params.atr_stop_mult:.2f},"
                f"{input_lbl},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
