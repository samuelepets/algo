"""MR-18 High-Low Channel Fade parameter search."""

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

from backtest import TARGET_CENTER, TARGET_OPPOSITE, search_range
from indicators import ATR_PERIOD, RANGE_PERIODS, atr, build_range_cache

ENTRY_PCTS = [0.80, 0.85, 0.90, 0.95]
ATR_RANGE_RATIOS = [0.20, 0.30, 0.40]
TARGET_MODES = [TARGET_CENTER, TARGET_OPPOSITE]
ATR_STOP_MULTS = [0.5, 1.0]
TIMEFRAMES = [5, 15]

_TARGET_LABELS = {TARGET_CENTER: "center", TARGET_OPPOSITE: "opposite_side"}


@dataclass
class Params:
    range_period: int
    entry_pct: float
    atr_range_ratio: float
    target_mode: int
    atr_stop_mult: float
    tf_min: int


@dataclass
class TfData:
    tf_min: int
    bars: BarArrays
    range_high_matrix: np.ndarray
    range_low_matrix: np.ndarray
    period_index: dict[int, int]
    atr_vals: np.ndarray
    grid: list[Params]
    period_rows: np.ndarray
    entry_pct: np.ndarray
    atr_range_ratio: np.ndarray
    target_mode: np.ndarray
    atr_stop_mult: np.ndarray
    warm_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for period in RANGE_PERIODS:
        for entry_pct in ENTRY_PCTS:
            for ratio in ATR_RANGE_RATIOS:
                for target in TARGET_MODES:
                    for atr_m in ATR_STOP_MULTS:
                        grid.append(
                            Params(
                                range_period=period,
                                entry_pct=entry_pct,
                                atr_range_ratio=ratio,
                                target_mode=target,
                                atr_stop_mult=atr_m,
                                tf_min=tf_min,
                            )
                        )
    return grid


def _grid_arrays(
    grid: list[Params], period_index: dict[int, int]
) -> tuple[np.ndarray, ...]:
    n = len(grid)
    period_rows = np.empty(n, dtype=np.int64)
    entry_pct = np.empty(n, dtype=np.float64)
    atr_range_ratio = np.empty(n, dtype=np.float64)
    target_mode = np.empty(n, dtype=np.int64)
    atr_stop_mult = np.empty(n, dtype=np.float64)
    warm_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        period_rows[i] = period_index[p.range_period]
        entry_pct[i] = p.entry_pct
        atr_range_ratio[i] = p.atr_range_ratio
        target_mode[i] = p.target_mode
        atr_stop_mult[i] = p.atr_stop_mult
        warm_bars[i] = p.range_period + 2
    return period_rows, entry_pct, atr_range_ratio, target_mode, atr_stop_mult, warm_bars


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    range_high_matrix, range_low_matrix, period_index = build_range_cache(
        bars_tf.high, bars_tf.low, RANGE_PERIODS
    )
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    period_rows, entry_pct, atr_range_ratio, target_mode, atr_stop_mult, warm_bars = (
        _grid_arrays(grid, period_index)
    )
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        range_high_matrix=range_high_matrix,
        range_low_matrix=range_low_matrix,
        period_index=period_index,
        atr_vals=atr_vals,
        grid=grid,
        period_rows=period_rows,
        entry_pct=entry_pct,
        atr_range_ratio=atr_range_ratio,
        target_mode=target_mode,
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
        tf.bars.close,
        tf.bars.high,
        tf.bars.low,
        tf.bars.ts,
        tf.range_high_matrix,
        tf.range_low_matrix,
        tf.atr_vals,
        tf.period_rows,
        tf.entry_pct,
        tf.atr_range_ratio,
        tf.target_mode,
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

    warm = params.range_period + 2

    search_range(
        tf.bars.close,
        tf.bars.high,
        tf.bars.low,
        tf.bars.ts,
        tf.range_high_matrix,
        tf.range_low_matrix,
        tf.atr_vals,
        np.array([tf.period_index[params.range_period]], dtype=np.int64),
        np.array([params.entry_pct], dtype=np.float64),
        np.array([params.atr_range_ratio], dtype=np.float64),
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
            "mr18_hl_channel_fade/"
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
            "range_period,entry_pct,atr_range_ratio,target,atr_stop_mult,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.range_period},{p.entry_pct:.2f},{p.atr_range_ratio:.2f},"
                f"{_TARGET_LABELS[p.target_mode]},{p.atr_stop_mult:.2f},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'per':<4} {'pct':<5} {'ratio':<6} {'target':<14} {'stop':<5} {'tf':<4}  "
        f"{'sharpe':>8}  {'pf':>7}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{p.range_period:<4} {p.entry_pct:<5.2f} {p.atr_range_ratio:<6.2f} "
            f"{_TARGET_LABELS[p.target_mode]:<14} {p.atr_stop_mult:<5.2f} {p.tf_min:<4}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>7.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_range_period,sel_entry_pct,sel_atr_range_ratio,sel_target,"
            "sel_atr_stop_mult,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<52}  "
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
                f"rp{sel_params.range_period} pct{sel_params.entry_pct:.2f} "
                f"ratio{sel_params.atr_range_ratio:.2f} "
                f"{_TARGET_LABELS[sel_params.target_mode]} "
                f"stop{sel_params.atr_stop_mult:.2f}x {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<52}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>7.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.range_period},{sel_params.entry_pct:.2f},"
                f"{sel_params.atr_range_ratio:.2f},{_TARGET_LABELS[sel_params.target_mode]},"
                f"{sel_params.atr_stop_mult:.2f},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
