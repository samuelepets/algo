"""TF-14 Hull Moving Average (HMA) Trend parameter search."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backtest import MODE_CROSSOVER, MODE_SLOPE, RR_RATIO, search_range
from data import BarArrays, load_eurusd, resample, ts_range, year_start_ts
from indicators import ATR_PERIOD, atr, build_hma_cache, hma_warmup

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

HMA_FASTS = [6, 9, 12, 16, 20]
HMA_SLOWS = [20, 25, 36, 49]
SLOPE_BARS = [1, 2, 3]
ATR_MULTS = [1.0, 1.5, 2.0]
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
    hma_fast: int
    hma_slow: int
    mode_label: str
    mode: int
    slope_bars: int
    atr_stop_mult: float
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
    hma_matrix: np.ndarray
    hma_row: dict[int, int]
    atr_vals: np.ndarray
    grid: list[Params]
    fast_rows: np.ndarray
    slow_rows: np.ndarray
    warm_bars: np.ndarray
    mode: np.ndarray
    slope_bars: np.ndarray
    atr_mult: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    # Slope mode: only hma_fast and slope_bars matter (hma_slow unused).
    for fast in HMA_FASTS:
        for sb in SLOPE_BARS:
            for atr_m in ATR_MULTS:
                grid.append(
                    Params(
                        hma_fast=fast,
                        hma_slow=fast,
                        mode_label="slope",
                        mode=MODE_SLOPE,
                        slope_bars=sb,
                        atr_stop_mult=atr_m,
                        tf_min=tf_min,
                    )
                )
    # Crossover mode: hma_fast < hma_slow (slope_bars unused).
    for fast in HMA_FASTS:
        for slow in HMA_SLOWS:
            if slow <= fast:
                continue
            for atr_m in ATR_MULTS:
                grid.append(
                    Params(
                        hma_fast=fast,
                        hma_slow=slow,
                        mode_label="crossover",
                        mode=MODE_CROSSOVER,
                        slope_bars=1,
                        atr_stop_mult=atr_m,
                        tf_min=tf_min,
                    )
                )
    return grid


def _grid_arrays(grid: list[Params], hma_row: dict[int, int]) -> tuple[np.ndarray, ...]:
    n = len(grid)
    fast_rows = np.empty(n, dtype=np.int64)
    slow_rows = np.empty(n, dtype=np.int64)
    warm_bars = np.empty(n, dtype=np.int64)
    mode = np.empty(n, dtype=np.int64)
    slope_bars = np.empty(n, dtype=np.int64)
    atr_mult = np.empty(n, dtype=np.float64)
    for i, p in enumerate(grid):
        fast_rows[i] = hma_row[p.hma_fast]
        slow_rows[i] = hma_row[p.hma_slow]
        warm_bars[i] = max(hma_warmup(p.hma_fast), hma_warmup(p.hma_slow))
        mode[i] = p.mode
        slope_bars[i] = p.slope_bars
        atr_mult[i] = p.atr_stop_mult
    return fast_rows, slow_rows, warm_bars, mode, slope_bars, atr_mult


def _top_params_entry(p: Params, m: Metrics) -> dict[str, float | int | str]:
    return {
        "atr_stop_mult": p.atr_stop_mult,
        "hma_fast": p.hma_fast,
        "hma_slow": p.hma_slow if p.mode == MODE_CROSSOVER else None,
        "max_drawdown_r": m.max_drawdown_r,
        "mode": p.mode_label,
        "n_trades": m.n_trades,
        "profit_factor": m.profit_factor,
        "rr_ratio": RR_RATIO,
        "sharpe": m.sharpe,
        "slope_bars": p.slope_bars if p.mode == MODE_SLOPE else None,
        "tf_min": p.tf_min,
        "total_return": m.total_return,
    }


def _format_top_params_json(rows: list[dict[str, float | int | str]]) -> str:
    return json.dumps(rows, indent=2, sort_keys=True)


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    periods = sorted(set(HMA_FASTS) | set(HMA_SLOWS))
    hma_matrix, hma_row = build_hma_cache(bars_tf.close, periods)
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    fast_rows, slow_rows, warm_bars, mode, slope_bars, atr_mult = _grid_arrays(grid, hma_row)
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        hma_matrix=hma_matrix,
        hma_row=hma_row,
        atr_vals=atr_vals,
        grid=grid,
        fast_rows=fast_rows,
        slow_rows=slow_rows,
        warm_bars=warm_bars,
        mode=mode,
        slope_bars=slope_bars,
        atr_mult=atr_mult,
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
        tf.hma_matrix,
        tf.atr_vals,
        tf.fast_rows,
        tf.slow_rows,
        tf.warm_bars,
        tf.mode,
        tf.slope_bars,
        tf.atr_mult,
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

    fast_rows = np.array([tf.hma_row[params.hma_fast]], dtype=np.int64)
    slow_rows = np.array([tf.hma_row[params.hma_slow]], dtype=np.int64)
    warm_bars = np.array(
        [max(hma_warmup(params.hma_fast), hma_warmup(params.hma_slow))], dtype=np.int64
    )
    mode = np.array([params.mode], dtype=np.int64)
    slope_bars = np.array([params.slope_bars], dtype=np.int64)
    atr_mult = np.array([params.atr_stop_mult], dtype=np.float64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.hma_matrix,
        tf.atr_vals,
        fast_rows,
        slow_rows,
        warm_bars,
        mode,
        slope_bars,
        atr_mult,
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
            "tf14_hma/"
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
            "hma_fast,hma_slow,mode,slope_bars,atr_stop_mult,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            slow_out = p.hma_slow if p.mode == MODE_CROSSOVER else ""
            sb_out = p.slope_bars if p.mode == MODE_SLOPE else ""
            fh.write(
                f"{p.hma_fast},{slow_out},{p.mode_label},{sb_out},"
                f"{p.atr_stop_mult:.2f},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'fast':<5} {'slow':<5} {'mode':<10} {'sb':<4} {'atr_m':<6} {'tf':<5}  "
        f"{'sharpe':>8}  {'pf':>8}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    top10 = []
    for p, m in valid[:10]:
        slow_lbl = str(p.hma_slow) if p.mode == MODE_CROSSOVER else "-"
        sb_lbl = str(p.slope_bars) if p.mode == MODE_SLOPE else "-"
        print(
            f"{p.hma_fast:<5} {slow_lbl:<5} {p.mode_label:<10} {sb_lbl:<4} "
            f"{p.atr_stop_mult:<6.1f} {p.tf_min:<5}  "
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
            "sel_hma_fast,sel_hma_slow,sel_mode,sel_slope_bars,sel_atr_mult,sel_tf,"
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

            if sel_params.mode == MODE_CROSSOVER:
                selected_label = (
                    f"{sel_params.hma_fast}/{sel_params.hma_slow} xover "
                    f"{sel_params.atr_stop_mult:.1f}× {sel_params.tf_min}m"
                )
            else:
                selected_label = (
                    f"hma{sel_params.hma_fast} slope{sel_params.slope_bars} "
                    f"{sel_params.atr_stop_mult:.1f}× {sel_params.tf_min}m"
                )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<30}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>8.4f}  {oos_m.n_trades:>7}"
            )
            slow_out = sel_params.hma_slow if sel_params.mode == MODE_CROSSOVER else ""
            sb_out = sel_params.slope_bars if sel_params.mode == MODE_SLOPE else ""
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.hma_fast},{slow_out},{sel_params.mode_label},{sb_out},"
                f"{sel_params.atr_stop_mult:.2f},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
