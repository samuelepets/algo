"""TF-19 Rate of Change (ROC) Breakout parameter search."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backtest import search_range
from data import BarArrays, load_eurusd, resample, ts_range, year_start_ts
from indicators import ATR_PERIOD, ROC_FILTER_NONE, atr, build_roc_cache

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

ROC_PERIODS = [3, 5, 10, 15, 20, 30]
THRESHOLD_PCTS = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
LONG_ROC_FILTERS = [0, 30, 60]  # 0 = none, else filter period
HOLDING_BARS = [5, 10, 20, 30]
TIMEFRAMES = [1, 5]
MIN_TRADES = 50

WALK_FORWARD_WINDOWS: list[tuple[int, int, int, int]] = [
    (2003, 2014, 2015, 2018),
    (2003, 2016, 2017, 2020),
    (2003, 2018, 2019, 2022),
    (2003, 2020, 2021, 2025),
]


@dataclass
class Params:
    roc_period: int
    threshold_pct: float
    filter_period: int
    holding_bars: int
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
    roc_matrix: np.ndarray
    roc_index: dict[int, int]
    atr_vals: np.ndarray
    grid: list[Params]
    roc_rows: np.ndarray
    filter_rows: np.ndarray
    warm_bars: np.ndarray
    threshold_pct: np.ndarray
    filter_type: np.ndarray
    holding_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for rp in ROC_PERIODS:
        for tp in THRESHOLD_PCTS:
            for fp in LONG_ROC_FILTERS:
                for hb in HOLDING_BARS:
                    grid.append(
                        Params(
                            roc_period=rp,
                            threshold_pct=tp,
                            filter_period=fp,
                            holding_bars=hb,
                            tf_min=tf_min,
                        )
                    )
    return grid


def _grid_arrays(grid: list[Params], roc_index: dict[int, int]) -> tuple[np.ndarray, ...]:
    n = len(grid)
    roc_rows = np.empty(n, dtype=np.int64)
    filter_rows = np.empty(n, dtype=np.int64)
    warm_bars = np.empty(n, dtype=np.int64)
    threshold_pct = np.empty(n, dtype=np.float64)
    filter_type = np.empty(n, dtype=np.int64)
    holding_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        roc_rows[i] = roc_index[p.roc_period]
        if p.filter_period == 0:
            filter_rows[i] = -1
            filter_type[i] = ROC_FILTER_NONE
        else:
            filter_rows[i] = roc_index[p.filter_period]
            filter_type[i] = 1
        warm_bars[i] = max(p.roc_period, p.filter_period if p.filter_period > 0 else 0)
        threshold_pct[i] = p.threshold_pct
        holding_bars[i] = p.holding_bars
    return roc_rows, filter_rows, warm_bars, threshold_pct, filter_type, holding_bars


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    # All unique ROC periods: signal periods + filter periods (excluding 0)
    all_periods = list(ROC_PERIODS) + [p for p in LONG_ROC_FILTERS if p > 0]
    roc_matrix, roc_index = build_roc_cache(bars_tf.close, all_periods)
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    roc_rows, filter_rows, warm_bars, threshold_pct, filter_type, holding_bars = _grid_arrays(grid, roc_index)
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        roc_matrix=roc_matrix,
        roc_index=roc_index,
        atr_vals=atr_vals,
        grid=grid,
        roc_rows=roc_rows,
        filter_rows=filter_rows,
        warm_bars=warm_bars,
        threshold_pct=threshold_pct,
        filter_type=filter_type,
        holding_bars=holding_bars,
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
        tf.roc_matrix,
        tf.atr_vals,
        tf.roc_rows,
        tf.filter_rows,
        tf.warm_bars,
        tf.threshold_pct,
        tf.filter_type,
        tf.holding_bars,
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

    roc_rows = np.array([tf.roc_index[params.roc_period]], dtype=np.int64)
    if params.filter_period == 0:
        filter_rows = np.array([-1], dtype=np.int64)
        filter_type = np.array([ROC_FILTER_NONE], dtype=np.int64)
    else:
        filter_rows = np.array([tf.roc_index[params.filter_period]], dtype=np.int64)
        filter_type = np.array([1], dtype=np.int64)
    warm_bars = np.array(
        [max(params.roc_period, params.filter_period if params.filter_period > 0 else 0)],
        dtype=np.int64,
    )
    threshold_pct = np.array([params.threshold_pct], dtype=np.float64)
    holding_bars = np.array([params.holding_bars], dtype=np.int64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.roc_matrix,
        tf.atr_vals,
        roc_rows,
        filter_rows,
        warm_bars,
        threshold_pct,
        filter_type,
        holding_bars,
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
            "tf19_roc_breakout/"
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
            "roc_period,threshold_pct,filter_period,holding_bars,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.roc_period},{p.threshold_pct:.2f},{p.filter_period},"
                f"{p.holding_bars},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'roc':<5} {'thresh':<8} {'filter':<8} {'hold':<6} {'tf':<5}  "
        f"{'sharpe':>8}  {'pf':>8}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        filter_lbl = str(p.filter_period) if p.filter_period > 0 else "none"
        print(
            f"{p.roc_period:<5} {p.threshold_pct:<8.2f} {filter_lbl:<8} "
            f"{p.holding_bars:<6} {p.tf_min:<5}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>8.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_roc,sel_thresh,sel_filter,sel_hold,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<35}  "
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

            filter_lbl = str(sel_params.filter_period) if sel_params.filter_period > 0 else "none"
            selected_label = (
                f"roc{sel_params.roc_period} t{sel_params.threshold_pct:.2f} "
                f"f{filter_lbl} h{sel_params.holding_bars} {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<35}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>8.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.roc_period},{sel_params.threshold_pct:.2f},"
                f"{sel_params.filter_period},{sel_params.holding_bars},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
