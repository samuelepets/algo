"""MR-02 RSI(2) Ultra-Short Reversion parameter search."""

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
from indicators import ATR_PERIOD, RSI_PERIODS, TREND_PERIODS, atr, build_rsi_cache, build_sma_cache

LONG_THRESHOLDS = [2, 5, 10, 15]
SHORT_THRESHOLDS = [98, 95, 90, 85]
EXIT_RSI_LONG = [50, 55, 60, 65]
EXIT_RSI_SHORT = [50, 45, 40, 35]
TREND_EMA_LIST = [0, 100, 200]  # 0 = no trend filter
MAX_HOLD_BARS_LIST = [3, 5, 10, 15]
TIMEFRAMES = [5, 15]


@dataclass
class Params:
    rsi_period: int
    long_threshold: int
    short_threshold: int
    exit_rsi_long: int
    exit_rsi_short: int
    trend_ema: int
    max_hold_bars: int
    tf_min: int


@dataclass
class TfData:
    tf_min: int
    bars: BarArrays
    rsi_matrix: np.ndarray
    rsi_period_index: dict[int, int]
    trend_sma_matrix: np.ndarray
    trend_period_index: dict[int, int]
    atr_vals: np.ndarray
    grid: list[Params]
    rsi_row: np.ndarray
    trend_row: np.ndarray
    long_threshold: np.ndarray
    short_threshold: np.ndarray
    exit_rsi_long: np.ndarray
    exit_rsi_short: np.ndarray
    trend_ema: np.ndarray
    max_hold_bars: np.ndarray
    warm_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for rsi_period in RSI_PERIODS:
        for long_t in LONG_THRESHOLDS:
            for short_t in SHORT_THRESHOLDS:
                for exit_l in EXIT_RSI_LONG:
                    for exit_s in EXIT_RSI_SHORT:
                        for trend_e in TREND_EMA_LIST:
                            for max_h in MAX_HOLD_BARS_LIST:
                                grid.append(
                                    Params(
                                        rsi_period=rsi_period,
                                        long_threshold=long_t,
                                        short_threshold=short_t,
                                        exit_rsi_long=exit_l,
                                        exit_rsi_short=exit_s,
                                        trend_ema=trend_e,
                                        max_hold_bars=max_h,
                                        tf_min=tf_min,
                                    )
                                )
    return grid


def _grid_arrays(
    grid: list[Params],
    rsi_period_index: dict[int, int],
    trend_period_index: dict[int, int],
) -> tuple[np.ndarray, ...]:
    n = len(grid)
    rsi_row = np.empty(n, dtype=np.int64)
    trend_row = np.empty(n, dtype=np.int64)
    long_threshold = np.empty(n, dtype=np.float64)
    short_threshold = np.empty(n, dtype=np.float64)
    exit_rsi_long = np.empty(n, dtype=np.float64)
    exit_rsi_short = np.empty(n, dtype=np.float64)
    trend_ema = np.empty(n, dtype=np.int64)
    max_hold_bars = np.empty(n, dtype=np.int64)
    warm_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        rsi_row[i] = rsi_period_index[p.rsi_period]
        trend_row[i] = trend_period_index[p.trend_ema] if p.trend_ema > 0 else 0
        long_threshold[i] = p.long_threshold
        short_threshold[i] = p.short_threshold
        exit_rsi_long[i] = p.exit_rsi_long
        exit_rsi_short[i] = p.exit_rsi_short
        trend_ema[i] = p.trend_ema
        max_hold_bars[i] = p.max_hold_bars
        warm_bars[i] = max(p.rsi_period, p.trend_ema, ATR_PERIOD) + 2
    return (
        rsi_row,
        trend_row,
        long_threshold,
        short_threshold,
        exit_rsi_long,
        exit_rsi_short,
        trend_ema,
        max_hold_bars,
        warm_bars,
    )


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    rsi_matrix, rsi_period_index = build_rsi_cache(bars_tf.close, RSI_PERIODS)
    trend_sma_matrix, trend_period_index = build_sma_cache(bars_tf.close, TREND_PERIODS)
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    grid = build_grid(tf_min)
    (
        rsi_row,
        trend_row,
        long_threshold,
        short_threshold,
        exit_rsi_long,
        exit_rsi_short,
        trend_ema,
        max_hold_bars,
        warm_bars,
    ) = _grid_arrays(grid, rsi_period_index, trend_period_index)
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        rsi_matrix=rsi_matrix,
        rsi_period_index=rsi_period_index,
        trend_sma_matrix=trend_sma_matrix,
        trend_period_index=trend_period_index,
        atr_vals=atr_vals,
        grid=grid,
        rsi_row=rsi_row,
        trend_row=trend_row,
        long_threshold=long_threshold,
        short_threshold=short_threshold,
        exit_rsi_long=exit_rsi_long,
        exit_rsi_short=exit_rsi_short,
        trend_ema=trend_ema,
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
        tf.rsi_matrix,
        tf.trend_sma_matrix,
        tf.atr_vals,
        tf.rsi_row,
        tf.trend_row,
        tf.long_threshold,
        tf.short_threshold,
        tf.exit_rsi_long,
        tf.exit_rsi_short,
        tf.trend_ema,
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

    warm = max(params.rsi_period, params.trend_ema, ATR_PERIOD) + 2
    trend_row = (
        tf.trend_period_index[params.trend_ema] if params.trend_ema > 0 else 0
    )

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.rsi_matrix,
        tf.trend_sma_matrix,
        tf.atr_vals,
        np.array([tf.rsi_period_index[params.rsi_period]], dtype=np.int64),
        np.array([trend_row], dtype=np.int64),
        np.array([params.long_threshold], dtype=np.float64),
        np.array([params.short_threshold], dtype=np.float64),
        np.array([params.exit_rsi_long], dtype=np.float64),
        np.array([params.exit_rsi_short], dtype=np.float64),
        np.array([params.trend_ema], dtype=np.int64),
        np.array([params.max_hold_bars], dtype=np.int64),
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


def _trend_label(trend_ema: int) -> str:
    return "none" if trend_ema == 0 else str(trend_ema)


def main() -> None:
    data_dir = Path("../../../../data/bars/EURUSD")
    if not data_dir.exists():
        raise SystemExit(
            f"ERROR: Data directory not found at {data_dir.resolve()}\n"
            "Run from experiments/e0030_strategy_parameters/cat02_mean_reversion/"
            "mr02_rsi2_reversion/"
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
            "rsi_period,long_threshold,short_threshold,exit_rsi_long,exit_rsi_short,"
            "trend_ema,max_hold_bars,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.rsi_period},{p.long_threshold},{p.short_threshold},"
                f"{p.exit_rsi_long},{p.exit_rsi_short},{p.trend_ema},"
                f"{p.max_hold_bars},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'rsi':<4} {'longT':<6} {'shortT':<7} {'exitL':<6} {'exitS':<6} "
        f"{'trend':<6} {'hold':<5} {'tf':<4}  "
        f"{'sharpe':>8}  {'pf':>7}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{p.rsi_period:<4} {p.long_threshold:<6} {p.short_threshold:<7} "
            f"{p.exit_rsi_long:<6} {p.exit_rsi_short:<6} "
            f"{_trend_label(p.trend_ema):<6} {p.max_hold_bars:<5} {p.tf_min:<4}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>7.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_rsi_period,sel_long_threshold,sel_short_threshold,"
            "sel_exit_rsi_long,sel_exit_rsi_short,sel_trend_ema,"
            "sel_max_hold_bars,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<58}  "
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

            trend_lbl = _trend_label(sel_params.trend_ema)
            selected_label = (
                f"rsi{sel_params.rsi_period} L<{sel_params.long_threshold} "
                f"S>{sel_params.short_threshold} exL{sel_params.exit_rsi_long} "
                f"exS{sel_params.exit_rsi_short} trend{trend_lbl} "
                f"hold{sel_params.max_hold_bars} {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<58}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>7.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.rsi_period},{sel_params.long_threshold},"
                f"{sel_params.short_threshold},{sel_params.exit_rsi_long},"
                f"{sel_params.exit_rsi_short},{sel_params.trend_ema},"
                f"{sel_params.max_hold_bars},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
