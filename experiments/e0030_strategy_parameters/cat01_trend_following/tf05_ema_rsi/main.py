"""TF-05 EMA Crossover + RSI Momentum Filter parameter search."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backtest import RR_RATIO, search_range
from data import BarArrays, load_eurusd, resample, ts_range, year_start_ts
from indicators import ATR_PERIOD, atr, build_ema_cache, build_rsi_cache

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

FAST_EMAS = [5, 7, 9, 12]
SLOW_EMAS = [18, 20, 21, 26]
RSI_PERIODS = [7, 10, 14]
# Long/short RSI thresholds are searched as symmetric pairs (long, short).
RSI_THRESHOLDS = [(50.0, 50.0), (52.0, 48.0), (55.0, 45.0), (57.0, 43.0)]
ATR_MULTS = [0.75, 1.0, 1.5, 2.0]
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
    fast_ema: int
    slow_ema: int
    rsi_period: int
    rsi_long: float
    rsi_short: float
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
    ema_matrix: np.ndarray
    ema_row: dict[int, int]
    rsi_matrix: np.ndarray
    rsi_row: dict[int, int]
    atr_vals: np.ndarray
    grid: list[Params]
    fast_rows: np.ndarray
    slow_rows: np.ndarray
    rsi_rows: np.ndarray
    slow_p: np.ndarray
    rsi_p: np.ndarray
    rsi_long: np.ndarray
    rsi_short: np.ndarray
    atr_mult: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for fast in FAST_EMAS:
        for slow in SLOW_EMAS:
            if slow <= fast:
                continue
            for rsi_p in RSI_PERIODS:
                for long_t, short_t in RSI_THRESHOLDS:
                    for atr_m in ATR_MULTS:
                        grid.append(
                            Params(
                                fast_ema=fast,
                                slow_ema=slow,
                                rsi_period=rsi_p,
                                rsi_long=long_t,
                                rsi_short=short_t,
                                atr_stop_mult=atr_m,
                                tf_min=tf_min,
                            )
                        )
    return grid


def _grid_arrays(
    grid: list[Params], ema_row: dict[int, int], rsi_row: dict[int, int]
) -> tuple[np.ndarray, ...]:
    n = len(grid)
    fast_rows = np.empty(n, dtype=np.int64)
    slow_rows = np.empty(n, dtype=np.int64)
    rsi_rows = np.empty(n, dtype=np.int64)
    slow_p = np.empty(n, dtype=np.int64)
    rsi_p = np.empty(n, dtype=np.int64)
    rsi_long = np.empty(n, dtype=np.float64)
    rsi_short = np.empty(n, dtype=np.float64)
    atr_mult = np.empty(n, dtype=np.float64)
    for i, p in enumerate(grid):
        fast_rows[i] = ema_row[p.fast_ema]
        slow_rows[i] = ema_row[p.slow_ema]
        rsi_rows[i] = rsi_row[p.rsi_period]
        slow_p[i] = p.slow_ema
        rsi_p[i] = p.rsi_period
        rsi_long[i] = p.rsi_long
        rsi_short[i] = p.rsi_short
        atr_mult[i] = p.atr_stop_mult
    return fast_rows, slow_rows, rsi_rows, slow_p, rsi_p, rsi_long, rsi_short, atr_mult


def _top_params_entry(p: Params, m: Metrics) -> dict[str, float | int | str]:
    return {
        "atr_stop_mult": p.atr_stop_mult,
        "fast_ema": p.fast_ema,
        "max_drawdown_r": m.max_drawdown_r,
        "n_trades": m.n_trades,
        "profit_factor": m.profit_factor,
        "rr_ratio": RR_RATIO,
        "rsi_long": p.rsi_long,
        "rsi_period": p.rsi_period,
        "rsi_short": p.rsi_short,
        "sharpe": m.sharpe,
        "slow_ema": p.slow_ema,
        "tf_min": p.tf_min,
        "total_return": m.total_return,
    }


def _format_top_params_json(rows: list[dict[str, float | int | str]]) -> str:
    return json.dumps(rows, indent=2, sort_keys=True)


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    ema_matrix, ema_row = build_ema_cache(bars_tf.close, sorted(set(FAST_EMAS) | set(SLOW_EMAS)))
    rsi_matrix, rsi_row = build_rsi_cache(bars_tf.close, RSI_PERIODS)
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    (
        fast_rows,
        slow_rows,
        rsi_rows,
        slow_p,
        rsi_p,
        rsi_long,
        rsi_short,
        atr_mult,
    ) = _grid_arrays(grid, ema_row, rsi_row)
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        ema_matrix=ema_matrix,
        ema_row=ema_row,
        rsi_matrix=rsi_matrix,
        rsi_row=rsi_row,
        atr_vals=atr_vals,
        grid=grid,
        fast_rows=fast_rows,
        slow_rows=slow_rows,
        rsi_rows=rsi_rows,
        slow_p=slow_p,
        rsi_p=rsi_p,
        rsi_long=rsi_long,
        rsi_short=rsi_short,
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
        tf.ema_matrix,
        tf.rsi_matrix,
        tf.atr_vals,
        tf.fast_rows,
        tf.slow_rows,
        tf.rsi_rows,
        tf.slow_p,
        tf.rsi_p,
        tf.rsi_long,
        tf.rsi_short,
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

    fast_row = np.array([tf.ema_row[params.fast_ema]], dtype=np.int64)
    slow_row = np.array([tf.ema_row[params.slow_ema]], dtype=np.int64)
    rsi_r = np.array([tf.rsi_row[params.rsi_period]], dtype=np.int64)
    slow_p = np.array([params.slow_ema], dtype=np.int64)
    rsi_p = np.array([params.rsi_period], dtype=np.int64)
    rsi_long = np.array([params.rsi_long], dtype=np.float64)
    rsi_short = np.array([params.rsi_short], dtype=np.float64)
    atr_mult = np.array([params.atr_stop_mult], dtype=np.float64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.ema_matrix,
        tf.rsi_matrix,
        tf.atr_vals,
        fast_row,
        slow_row,
        rsi_r,
        slow_p,
        rsi_p,
        rsi_long,
        rsi_short,
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
            "tf05_ema_rsi/"
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
            "fast_ema,slow_ema,rsi_period,rsi_long,rsi_short,atr_stop_mult,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.fast_ema},{p.slow_ema},{p.rsi_period},"
                f"{p.rsi_long:.0f},{p.rsi_short:.0f},"
                f"{p.atr_stop_mult:.2f},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'fast':<5} {'slow':<5} {'rsiP':<5} {'rLong':<6} {'rShrt':<6} {'atr_m':<6} "
        f"{'tf':<5}  {'sharpe':>8}  {'pf':>8}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    top10 = []
    for p, m in valid[:10]:
        print(
            f"{p.fast_ema:<5} {p.slow_ema:<5} {p.rsi_period:<5} "
            f"{p.rsi_long:<6.0f} {p.rsi_short:<6.0f} {p.atr_stop_mult:<6.2f} {p.tf_min:<5}  "
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
            "sel_fast,sel_slow,sel_rsi_period,sel_rsi_long,sel_rsi_short,"
            "sel_atr_mult,sel_tf,"
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
                f"{sel_params.fast_ema}/{sel_params.slow_ema} "
                f"rsi{sel_params.rsi_period} "
                f"{sel_params.rsi_long:.0f}/{sel_params.rsi_short:.0f} "
                f"{sel_params.atr_stop_mult:.2f}× {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<30}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>8.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.fast_ema},{sel_params.slow_ema},{sel_params.rsi_period},"
                f"{sel_params.rsi_long:.0f},{sel_params.rsi_short:.0f},"
                f"{sel_params.atr_stop_mult:.2f},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
