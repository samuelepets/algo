"""TF-13 EMA Ribbon (multi-MA alignment) parameter search."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backtest import MAX_RIBBON, RR_RATIO, STOP_ATR_MULT, search_range
from data import BarArrays, load_eurusd, resample, ts_range, year_start_ts
from indicators import ATR_PERIOD, atr, build_ema_cache

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

EMA_STARTS = [3, 5, 8]
EMA_RATIOS = [1.5, 1.618, 2.0]
EMA_COUNTS = [4, 5, 6]
ALIGNMENT_PCTS = [0.8, 0.9, 1.0]
EXPANSION_BARS = [2, 3, 5]
TIMEFRAMES = [5, 15]
MIN_TRADES = 50

WALK_FORWARD_WINDOWS: list[tuple[int, int, int, int]] = [
    (2003, 2014, 2015, 2018),
    (2003, 2016, 2017, 2020),
    (2003, 2018, 2019, 2022),
    (2003, 2020, 2021, 2025),
]


def ribbon_periods(start: int, ratio: float, count: int) -> list[int]:
    """Strictly-increasing geometric EMA periods ``round(start · ratio**k)``."""
    periods: list[int] = []
    prev = 0
    for k in range(count):
        p = int(round(start * (ratio**k)))
        if p <= prev:
            p = prev + 1
        periods.append(p)
        prev = p
    return periods


@dataclass
class Params:
    ema_start: int
    ema_ratio: float
    ema_count: int
    alignment_pct: float
    expansion_bars: int
    tf_min: int

    @property
    def periods(self) -> list[int]:
        return ribbon_periods(self.ema_start, self.ema_ratio, self.ema_count)


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
    ema_matrix: np.ndarray
    ema_row: dict[int, int]
    atr_vals: np.ndarray
    grid: list[Params]
    ribbon_rows: np.ndarray
    counts: np.ndarray
    slow_period: np.ndarray
    alignment_pct: np.ndarray
    expansion_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for start in EMA_STARTS:
        for ratio in EMA_RATIOS:
            for count in EMA_COUNTS:
                for align in ALIGNMENT_PCTS:
                    for exp in EXPANSION_BARS:
                        grid.append(
                            Params(
                                ema_start=start,
                                ema_ratio=ratio,
                                ema_count=count,
                                alignment_pct=align,
                                expansion_bars=exp,
                                tf_min=tf_min,
                            )
                        )
    return grid


def _all_periods() -> list[int]:
    periods: set[int] = set()
    for start in EMA_STARTS:
        for ratio in EMA_RATIOS:
            for count in EMA_COUNTS:
                periods.update(ribbon_periods(start, ratio, count))
    return sorted(periods)


def _grid_arrays(grid: list[Params], ema_row: dict[int, int]) -> tuple[np.ndarray, ...]:
    n = len(grid)
    ribbon_rows = np.zeros((n, MAX_RIBBON), dtype=np.int64)
    counts = np.empty(n, dtype=np.int64)
    slow_period = np.empty(n, dtype=np.int64)
    alignment_pct = np.empty(n, dtype=np.float64)
    expansion_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        periods = p.periods
        for k, period in enumerate(periods):
            ribbon_rows[i, k] = ema_row[period]
        counts[i] = len(periods)
        slow_period[i] = periods[-1]
        alignment_pct[i] = p.alignment_pct
        expansion_bars[i] = p.expansion_bars
    return ribbon_rows, counts, slow_period, alignment_pct, expansion_bars


def _top_params_entry(p: Params, m: Metrics) -> dict[str, float | int | str]:
    return {
        "alignment_pct": p.alignment_pct,
        "ema_count": p.ema_count,
        "ema_ratio": p.ema_ratio,
        "ema_start": p.ema_start,
        "expansion_bars": p.expansion_bars,
        "max_drawdown_r": m.max_drawdown_r,
        "n_trades": m.n_trades,
        "periods": str(p.periods),
        "profit_factor": m.profit_factor,
        "rr_ratio": RR_RATIO,
        "sharpe": m.sharpe,
        "stop_atr_mult": STOP_ATR_MULT,
        "tf_min": p.tf_min,
        "total_return": m.total_return,
    }


def _format_top_params_json(rows: list[dict[str, float | int | str]]) -> str:
    return json.dumps(rows, indent=2, sort_keys=True)


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    ema_matrix, ema_row = build_ema_cache(bars_tf.close, _all_periods())
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    ribbon_rows, counts, slow_period, alignment_pct, expansion_bars = _grid_arrays(
        grid, ema_row
    )
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        ema_matrix=ema_matrix,
        ema_row=ema_row,
        atr_vals=atr_vals,
        grid=grid,
        ribbon_rows=ribbon_rows,
        counts=counts,
        slow_period=slow_period,
        alignment_pct=alignment_pct,
        expansion_bars=expansion_bars,
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
        tf.ribbon_rows,
        tf.counts,
        tf.slow_period,
        tf.alignment_pct,
        tf.expansion_bars,
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

    periods = params.periods
    ribbon_rows = np.zeros((1, MAX_RIBBON), dtype=np.int64)
    for k, period in enumerate(periods):
        ribbon_rows[0, k] = tf.ema_row[period]
    counts = np.array([len(periods)], dtype=np.int64)
    slow_period = np.array([periods[-1]], dtype=np.int64)
    alignment_pct = np.array([params.alignment_pct], dtype=np.float64)
    expansion_bars = np.array([params.expansion_bars], dtype=np.int64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.ema_matrix,
        tf.atr_vals,
        ribbon_rows,
        counts,
        slow_period,
        alignment_pct,
        expansion_bars,
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
            "tf13_ema_ribbon/"
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
            "ema_start,ema_ratio,ema_count,alignment_pct,expansion_bars,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.ema_start},{p.ema_ratio:.3f},{p.ema_count},"
                f"{p.alignment_pct:.2f},{p.expansion_bars},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'start':<6} {'ratio':<6} {'cnt':<4} {'align':<6} {'exp':<4} {'tf':<5}  "
        f"{'sharpe':>8}  {'pf':>8}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    top10 = []
    for p, m in valid[:10]:
        print(
            f"{p.ema_start:<6} {p.ema_ratio:<6.3f} {p.ema_count:<4} "
            f"{p.alignment_pct:<6.2f} {p.expansion_bars:<4} {p.tf_min:<5}  "
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
            "sel_ema_start,sel_ema_ratio,sel_ema_count,sel_alignment_pct,"
            "sel_expansion_bars,sel_tf,"
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
                f"s{sel_params.ema_start} r{sel_params.ema_ratio:.2f} "
                f"c{sel_params.ema_count} a{sel_params.alignment_pct:.1f} "
                f"e{sel_params.expansion_bars} {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<30}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>8.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.ema_start},{sel_params.ema_ratio:.3f},"
                f"{sel_params.ema_count},{sel_params.alignment_pct:.2f},"
                f"{sel_params.expansion_bars},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
