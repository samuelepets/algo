"""TF-18 N-Period High/Low Breakout parameter search."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backtest import search_range
from data import BarArrays, load_eurusd, resample, ts_range, year_start_ts
from indicators import ATR_PERIOD, atr, build_breakout_cache

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

BREAKOUT_NS = [5, 10, 15, 20, 30, 40, 50]
CONFIRMATIONS = [0, 1]   # CONFIRM_CLOSE=0, CONFIRM_HIGH=1
VOL_FILTERS = [False, True]
ATR_MULTS = [1.0, 1.5, 2.0, 2.5]
RR_RATIOS = [1.0, 1.5, 2.0]
TIMEFRAMES = [5, 15]
MIN_TRADES = 50

WALK_FORWARD_WINDOWS: list[tuple[int, int, int, int]] = [
    (2003, 2014, 2015, 2018),
    (2003, 2016, 2017, 2020),
    (2003, 2018, 2019, 2022),
    (2003, 2020, 2021, 2025),
]

_CONFIRM_LABELS = {0: "close", 1: "high"}


@dataclass
class Params:
    breakout_n: int
    confirm: int
    confirm_label: str
    use_vol_filter: bool
    atr_stop_mult: float
    rr_ratio: float
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
    max_matrix: np.ndarray
    min_matrix: np.ndarray
    vol_matrix: np.ndarray
    bo_index: dict[int, int]
    atr_vals: np.ndarray
    grid: list[Params]
    bo_rows: np.ndarray
    warm_bars: np.ndarray
    confirm: np.ndarray
    use_vol_filter: np.ndarray
    atr_mult: np.ndarray
    rr: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for n in BREAKOUT_NS:
        for conf in CONFIRMATIONS:
            for vf in VOL_FILTERS:
                for atr_m in ATR_MULTS:
                    for rr in RR_RATIOS:
                        grid.append(
                            Params(
                                breakout_n=n,
                                confirm=conf,
                                confirm_label=_CONFIRM_LABELS[conf],
                                use_vol_filter=vf,
                                atr_stop_mult=atr_m,
                                rr_ratio=rr,
                                tf_min=tf_min,
                            )
                        )
    return grid


def _grid_arrays(grid: list[Params], bo_index: dict[int, int]) -> tuple[np.ndarray, ...]:
    n = len(grid)
    bo_rows = np.empty(n, dtype=np.int64)
    warm_bars = np.empty(n, dtype=np.int64)
    confirm = np.empty(n, dtype=np.int64)
    use_vol_filter = np.empty(n, dtype=np.int64)
    atr_mult = np.empty(n, dtype=np.float64)
    rr = np.empty(n, dtype=np.float64)
    for i, p in enumerate(grid):
        bo_rows[i] = bo_index[p.breakout_n]
        warm_bars[i] = p.breakout_n
        confirm[i] = p.confirm
        use_vol_filter[i] = 1 if p.use_vol_filter else 0
        atr_mult[i] = p.atr_stop_mult
        rr[i] = p.rr_ratio
    return bo_rows, warm_bars, confirm, use_vol_filter, atr_mult, rr


def _top_params_entry(p: Params, m: Metrics) -> dict[str, float | int | str | bool]:
    return {
        "atr_stop_mult": p.atr_stop_mult,
        "breakout_n": p.breakout_n,
        "confirm": p.confirm_label,
        "max_drawdown_r": m.max_drawdown_r,
        "n_trades": m.n_trades,
        "profit_factor": m.profit_factor,
        "rr_ratio": p.rr_ratio,
        "sharpe": m.sharpe,
        "tf_min": p.tf_min,
        "total_return": m.total_return,
        "use_vol_filter": p.use_vol_filter,
    }


def _format_top_params_json(rows: list[dict[str, float | int | str | bool]]) -> str:
    return json.dumps(rows, indent=2, sort_keys=True)


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    max_matrix, min_matrix, vol_matrix, bo_index = build_breakout_cache(
        bars_tf.high, bars_tf.low, bars_tf.volume, BREAKOUT_NS
    )
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    bo_rows, warm_bars, confirm, use_vol_filter, atr_mult, rr = _grid_arrays(grid, bo_index)
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        max_matrix=max_matrix,
        min_matrix=min_matrix,
        vol_matrix=vol_matrix,
        bo_index=bo_index,
        atr_vals=atr_vals,
        grid=grid,
        bo_rows=bo_rows,
        warm_bars=warm_bars,
        confirm=confirm,
        use_vol_filter=use_vol_filter,
        atr_mult=atr_mult,
        rr=rr,
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
        tf.bars.volume,
        tf.max_matrix,
        tf.min_matrix,
        tf.vol_matrix,
        tf.atr_vals,
        tf.bo_rows,
        tf.warm_bars,
        tf.confirm,
        tf.use_vol_filter,
        tf.atr_mult,
        tf.rr,
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

    bo_rows = np.array([tf.bo_index[params.breakout_n]], dtype=np.int64)
    warm_bars = np.array([params.breakout_n], dtype=np.int64)
    confirm = np.array([params.confirm], dtype=np.int64)
    use_vol_filter = np.array([1 if params.use_vol_filter else 0], dtype=np.int64)
    atr_mult = np.array([params.atr_stop_mult], dtype=np.float64)
    rr = np.array([params.rr_ratio], dtype=np.float64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.bars.volume,
        tf.max_matrix,
        tf.min_matrix,
        tf.vol_matrix,
        tf.atr_vals,
        bo_rows,
        warm_bars,
        confirm,
        use_vol_filter,
        atr_mult,
        rr,
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
            "tf18_nbar_breakout/"
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
            "breakout_n,confirm,vol_filter,atr_stop_mult,rr_ratio,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.breakout_n},{p.confirm_label},{p.use_vol_filter},"
                f"{p.atr_stop_mult:.2f},{p.rr_ratio:.2f},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'n':<5} {'conf':<6} {'vol':<6} {'atr_m':<6} {'rr':<5} {'tf':<5}  "
        f"{'sharpe':>8}  {'pf':>8}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    top10 = []
    for p, m in valid[:10]:
        print(
            f"{p.breakout_n:<5} {p.confirm_label:<6} {str(p.use_vol_filter):<6} "
            f"{p.atr_stop_mult:<6.1f} {p.rr_ratio:<5.1f} {p.tf_min:<5}  "
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
            "sel_n,sel_confirm,sel_vol,sel_atr,sel_rr,sel_tf,"
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

            selected_label = (
                f"n{sel_params.breakout_n} {sel_params.confirm_label} "
                f"vol={sel_params.use_vol_filter} "
                f"{sel_params.atr_stop_mult:.1f}x rr{sel_params.rr_ratio:.1f} "
                f"{sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<35}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>8.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.breakout_n},{sel_params.confirm_label},"
                f"{sel_params.use_vol_filter},{sel_params.atr_stop_mult:.2f},"
                f"{sel_params.rr_ratio:.2f},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
