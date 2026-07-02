"""MR-14 Stochastic RSI Reversion parameter search."""

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

from backtest import search_range
from indicators import (
    ATR_PERIOD,
    RSI_PERIODS,
    SMOOTH_D,
    SMOOTH_K_LIST,
    STOCH_PERIODS,
    atr,
    build_k_cache,
)

OVERSOLD_THRESHOLDS = [0.05, 0.10, 0.15, 0.20]
OVERBOUGHT_THRESHOLDS = [0.95, 0.90, 0.85, 0.80]
ATR_STOP_MULTS = [0.75, 1.0, 1.5]
TIMEFRAMES = [5, 15]


@dataclass
class Params:
    rsi_period: int
    stoch_period: int
    smooth_k: int
    oversold_thresh: float
    overbought_thresh: float
    atr_stop_mult: float
    tf_min: int


@dataclass
class TfData:
    tf_min: int
    bars: BarArrays
    k_matrix: np.ndarray
    combo_index: dict[tuple[int, int, int], int]
    atr_vals: np.ndarray
    grid: list[Params]
    combo_rows: np.ndarray
    oversold_thresh: np.ndarray
    overbought_thresh: np.ndarray
    atr_stop_mult: np.ndarray
    warm_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for rsi_p in RSI_PERIODS:
        for stoch_p in STOCH_PERIODS:
            for smooth_k in SMOOTH_K_LIST:
                for oversold in OVERSOLD_THRESHOLDS:
                    for overbought in OVERBOUGHT_THRESHOLDS:
                        for atr_m in ATR_STOP_MULTS:
                            grid.append(
                                Params(
                                    rsi_period=rsi_p,
                                    stoch_period=stoch_p,
                                    smooth_k=smooth_k,
                                    oversold_thresh=oversold,
                                    overbought_thresh=overbought,
                                    atr_stop_mult=atr_m,
                                    tf_min=tf_min,
                                )
                            )
    return grid


def _grid_arrays(
    grid: list[Params], combo_index: dict[tuple[int, int, int], int]
) -> tuple[np.ndarray, ...]:
    n = len(grid)
    combo_rows = np.empty(n, dtype=np.int64)
    oversold_thresh = np.empty(n, dtype=np.float64)
    overbought_thresh = np.empty(n, dtype=np.float64)
    atr_stop_mult = np.empty(n, dtype=np.float64)
    warm_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        combo_rows[i] = combo_index[(p.rsi_period, p.stoch_period, p.smooth_k)]
        oversold_thresh[i] = p.oversold_thresh
        overbought_thresh[i] = p.overbought_thresh
        atr_stop_mult[i] = p.atr_stop_mult
        warm_bars[i] = p.rsi_period + p.stoch_period + p.smooth_k + 2
    return combo_rows, oversold_thresh, overbought_thresh, atr_stop_mult, warm_bars


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    k_matrix, combo_index = build_k_cache(
        bars_tf.close, RSI_PERIODS, STOCH_PERIODS, SMOOTH_K_LIST
    )
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    combo_rows, oversold_thresh, overbought_thresh, atr_stop_mult, warm_bars = _grid_arrays(
        grid, combo_index
    )
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        k_matrix=k_matrix,
        combo_index=combo_index,
        atr_vals=atr_vals,
        grid=grid,
        combo_rows=combo_rows,
        oversold_thresh=oversold_thresh,
        overbought_thresh=overbought_thresh,
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
        tf.k_matrix,
        tf.atr_vals,
        tf.combo_rows,
        tf.oversold_thresh,
        tf.overbought_thresh,
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

    warm = params.rsi_period + params.stoch_period + params.smooth_k + 2
    row = tf.combo_index[(params.rsi_period, params.stoch_period, params.smooth_k)]

    search_range(
        tf.bars.close,
        tf.bars.high,
        tf.bars.low,
        tf.bars.ts,
        tf.k_matrix,
        tf.atr_vals,
        np.array([row], dtype=np.int64),
        np.array([params.oversold_thresh], dtype=np.float64),
        np.array([params.overbought_thresh], dtype=np.float64),
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
            "mr14_stochrsi/"
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
            "rsi_period,stoch_period,smooth_k,smooth_d,oversold_thresh,overbought_thresh,"
            "atr_stop_mult,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.rsi_period},{p.stoch_period},{p.smooth_k},{SMOOTH_D},"
                f"{p.oversold_thresh:.2f},{p.overbought_thresh:.2f},"
                f"{p.atr_stop_mult:.2f},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'rsi':<4} {'stoch':<6} {'k':<3} {'os':<5} {'ob':<5} {'stop':<5} {'tf':<4}  "
        f"{'sharpe':>8}  {'pf':>7}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{p.rsi_period:<4} {p.stoch_period:<6} {p.smooth_k:<3} "
            f"{p.oversold_thresh:<5.2f} {p.overbought_thresh:<5.2f} "
            f"{p.atr_stop_mult:<5.2f} {p.tf_min:<4}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>7.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_rsi_period,sel_stoch_period,sel_smooth_k,sel_oversold_thresh,"
            "sel_overbought_thresh,sel_atr_stop_mult,sel_tf,"
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
                f"rsi{sel_params.rsi_period}/stoch{sel_params.stoch_period}/k{sel_params.smooth_k} "
                f"os{sel_params.oversold_thresh:.2f}/ob{sel_params.overbought_thresh:.2f} "
                f"stop{sel_params.atr_stop_mult:.2f}x {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<52}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>7.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.rsi_period},{sel_params.stoch_period},{sel_params.smooth_k},"
                f"{sel_params.oversold_thresh:.2f},{sel_params.overbought_thresh:.2f},"
                f"{sel_params.atr_stop_mult:.2f},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
