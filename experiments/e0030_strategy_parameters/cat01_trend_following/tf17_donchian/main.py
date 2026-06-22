"""TF-17 Donchian Channel Breakout parameter search."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backtest import search_range
from data import BarArrays, load_eurusd, resample, ts_range, year_start_ts
from indicators import ATR_PERIOD, atr, build_donchian_cache

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

ENTRY_CHANNELS = [10, 15, 20, 30, 40, 55]
EXIT_CHANNELS = [5, 8, 10, 15, 20]
BUFFER_ATRS = [0.0, 0.1, 0.2]
TIMEFRAMES = [5, 15, 60]
MIN_TRADES = 50
RR_RATIO = 2.0  # used only for interface; Donchian exits via channel

WALK_FORWARD_WINDOWS: list[tuple[int, int, int, int]] = [
    (2003, 2014, 2015, 2018),
    (2003, 2016, 2017, 2020),
    (2003, 2018, 2019, 2022),
    (2003, 2020, 2021, 2025),
]


@dataclass
class Params:
    entry_channel: int
    exit_channel: int
    buffer_atr: float
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
    upper_matrix: np.ndarray
    lower_matrix: np.ndarray
    period_index: dict[int, int]
    atr_vals: np.ndarray
    grid: list[Params]
    entry_rows: np.ndarray
    exit_rows: np.ndarray
    warm_bars: np.ndarray
    buffer_atr: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for entry in ENTRY_CHANNELS:
        for exit_ in EXIT_CHANNELS:
            if exit_ >= entry:
                continue
            for buf in BUFFER_ATRS:
                grid.append(
                    Params(
                        entry_channel=entry,
                        exit_channel=exit_,
                        buffer_atr=buf,
                        tf_min=tf_min,
                    )
                )
    return grid


def _grid_arrays(
    grid: list[Params], period_index: dict[int, int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(grid)
    entry_rows = np.empty(n, dtype=np.int64)
    exit_rows = np.empty(n, dtype=np.int64)
    warm_bars = np.empty(n, dtype=np.int64)
    buffer_atr = np.empty(n, dtype=np.float64)
    for i, p in enumerate(grid):
        entry_rows[i] = period_index[p.entry_channel]
        exit_rows[i] = period_index[p.exit_channel]
        warm_bars[i] = p.entry_channel
        buffer_atr[i] = p.buffer_atr
    return entry_rows, exit_rows, warm_bars, buffer_atr


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    grid = build_grid(tf_min)
    entry_periods = [p.entry_channel for p in grid]
    exit_periods = [p.exit_channel for p in grid]
    upper_matrix, lower_matrix, period_index = build_donchian_cache(
        bars_tf.high, bars_tf.low, entry_periods, exit_periods
    )
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    entry_rows, exit_rows, warm_bars, buffer_atr = _grid_arrays(grid, period_index)
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        upper_matrix=upper_matrix,
        lower_matrix=lower_matrix,
        period_index=period_index,
        atr_vals=atr_vals,
        grid=grid,
        entry_rows=entry_rows,
        exit_rows=exit_rows,
        warm_bars=warm_bars,
        buffer_atr=buffer_atr,
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
        tf.upper_matrix,
        tf.lower_matrix,
        tf.atr_vals,
        tf.entry_rows,
        tf.exit_rows,
        tf.warm_bars,
        tf.buffer_atr,
        RR_RATIO,
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

    entry_rows = np.array([tf.period_index[params.entry_channel]], dtype=np.int64)
    exit_rows = np.array([tf.period_index[params.exit_channel]], dtype=np.int64)
    warm_bars = np.array([params.entry_channel], dtype=np.int64)
    buffer_atr = np.array([params.buffer_atr], dtype=np.float64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.upper_matrix,
        tf.lower_matrix,
        tf.atr_vals,
        entry_rows,
        exit_rows,
        warm_bars,
        buffer_atr,
        RR_RATIO,
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
            "tf17_donchian/"
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
            "entry_channel,exit_channel,buffer_atr,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.entry_channel},{p.exit_channel},{p.buffer_atr:.2f},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'entry':<7} {'exit':<6} {'buf':<6} {'tf':<5}  "
        f"{'sharpe':>8}  {'pf':>8}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{p.entry_channel:<7} {p.exit_channel:<6} {p.buffer_atr:<6.2f} {p.tf_min:<5}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>8.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_entry,sel_exit,sel_buffer,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<28}  "
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
                f"entry{sel_params.entry_channel}/exit{sel_params.exit_channel} "
                f"buf{sel_params.buffer_atr:.1f} {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<28}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>8.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.entry_channel},{sel_params.exit_channel},"
                f"{sel_params.buffer_atr:.2f},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
