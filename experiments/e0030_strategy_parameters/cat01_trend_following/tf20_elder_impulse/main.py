"""TF-20 Elder Impulse System parameter search."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

os.environ.setdefault(
    "NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache")
)

from backtest import search_range  # noqa: E402
from data import BarArrays, load_eurusd, resample, ts_range, year_start_ts  # noqa: E402
from indicators import (  # noqa: E402
    build_impulse_cache,
    elder_impulse_colors,
    ema,
    macd_histogram,
)

EMA_PERIODS = [10, 13, 20, 26]
MACD_FASTS = [8, 10, 12]
MACD_SLOWS = [21, 24, 26]
MACD_SIGNALS = [7, 9]
ENTRY_CONDITIONS = [0, 1]  # ENTRY_FIRST=0, ENTRY_ANY=1
EXIT_CONDITIONS = [0, 1]   # EXIT_NEUTRAL=0, EXIT_OPPOSITE=1
ATR_MULTS = [1.0, 1.5, 2.0]
TIMEFRAMES = [5, 15]
MIN_TRADES = 50

WALK_FORWARD_WINDOWS: list[tuple[int, int, int, int]] = [
    (2003, 2014, 2015, 2018),
    (2003, 2016, 2017, 2020),
    (2003, 2018, 2019, 2022),
    (2003, 2020, 2021, 2025),
]

_ENTRY_LABELS = {0: "first", 1: "any"}
_EXIT_LABELS = {0: "neutral", 1: "opposite"}


@dataclass
class Params:
    ema_period: int
    macd_fast: int
    macd_slow: int
    macd_signal: int
    entry_cond: int
    entry_label: str
    exit_cond: int
    exit_label: str
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
    colors_matrix: np.ndarray
    atr_vals: np.ndarray
    grid: list[Params]
    warm_bars: np.ndarray
    entry_cond: np.ndarray
    exit_cond: np.ndarray
    atr_mult: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for ep in EMA_PERIODS:
        for mf in MACD_FASTS:
            for ms in MACD_SLOWS:
                if mf >= ms:
                    continue
                for sig in MACD_SIGNALS:
                    for ec in ENTRY_CONDITIONS:
                        for xc in EXIT_CONDITIONS:
                            for atr_m in ATR_MULTS:
                                grid.append(
                                    Params(
                                        ema_period=ep,
                                        macd_fast=mf,
                                        macd_slow=ms,
                                        macd_signal=sig,
                                        entry_cond=ec,
                                        entry_label=_ENTRY_LABELS[ec],
                                        exit_cond=xc,
                                        exit_label=_EXIT_LABELS[xc],
                                        atr_stop_mult=atr_m,
                                        tf_min=tf_min,
                                    )
                                )
    return grid


def _prepare_tf(bars_1min: BarArrays, tf_min: int) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    grid = build_grid(tf_min)

    # Build color cache via build_impulse_cache
    colors_dict, atr_vals = build_impulse_cache(
        bars_tf.close,
        bars_tf.high,
        bars_tf.low,
        EMA_PERIODS,
        MACD_FASTS,
        MACD_SLOWS,
        MACD_SIGNALS,
    )

    n = len(bars_tf.close)
    colors_matrix = np.empty((len(grid), n), dtype=np.int64)
    for i, p in enumerate(grid):
        key = (p.ema_period, p.macd_fast, p.macd_slow, p.macd_signal)
        colors_matrix[i] = colors_dict[key]

    # Grid arrays
    warm_bars = np.array(
        [p.macd_slow + p.macd_signal + p.ema_period for p in grid], dtype=np.int64
    )
    entry_cond = np.array([p.entry_cond for p in grid], dtype=np.int64)
    exit_cond = np.array([p.exit_cond for p in grid], dtype=np.int64)
    atr_mult = np.array([p.atr_stop_mult for p in grid], dtype=np.float64)

    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        colors_matrix=colors_matrix,
        atr_vals=atr_vals,
        grid=grid,
        warm_bars=warm_bars,
        entry_cond=entry_cond,
        exit_cond=exit_cond,
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
        tf.colors_matrix,
        tf.atr_vals,
        tf.warm_bars,
        tf.entry_cond,
        tf.exit_cond,
        tf.atr_mult,
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

    # Rebuild single color row matching this param combo
    n_bars = len(tf.bars.close)
    e_vals = ema(tf.bars.close, params.ema_period)
    h_vals = macd_histogram(
        tf.bars.close, params.macd_fast, params.macd_slow, params.macd_signal
    )
    single_colors = elder_impulse_colors(e_vals, h_vals)
    colors_1 = single_colors.reshape(1, n_bars)

    warm_bars = np.array(
        [params.macd_slow + params.macd_signal + params.ema_period], dtype=np.int64
    )
    entry_cond = np.array([params.entry_cond], dtype=np.int64)
    exit_cond = np.array([params.exit_cond], dtype=np.int64)
    atr_mult = np.array([params.atr_stop_mult], dtype=np.float64)

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        colors_1,
        tf.atr_vals,
        warm_bars,
        entry_cond,
        exit_cond,
        atr_mult,
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
            "tf20_elder_impulse/"
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
            "ema_period,macd_fast,macd_slow,macd_signal,entry_cond,exit_cond,"
            "atr_stop_mult,tf_min,sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.ema_period},{p.macd_fast},{p.macd_slow},{p.macd_signal},"
                f"{p.entry_cond},{p.exit_cond},"
                f"{p.atr_stop_mult:.2f},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'ep':<4} {'mf':<4} {'ms':<4} {'sig':<4} {'entry':<8} {'exit':<9} "
        f"{'atr':<5} {'tf':<4}  "
        f"{'sharpe':>8}  {'pf':>8}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{p.ema_period:<4} {p.macd_fast:<4} {p.macd_slow:<4} {p.macd_signal:<4} "
            f"{p.entry_label:<8} {p.exit_label:<9} "
            f"{p.atr_stop_mult:<5.1f} {p.tf_min:<4}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>8.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_ema,sel_mf,sel_ms,sel_msig,sel_entry,sel_exit,sel_atr,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<38}  "
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
                f"ema{sel_params.ema_period} "
                f"macd{sel_params.macd_fast}/{sel_params.macd_slow}/{sel_params.macd_signal} "
                f"{sel_params.entry_label}/{sel_params.exit_label} "
                f"{sel_params.atr_stop_mult:.1f}x {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<38}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>8.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.ema_period},{sel_params.macd_fast},{sel_params.macd_slow},"
                f"{sel_params.macd_signal},{sel_params.entry_cond},{sel_params.exit_cond},"
                f"{sel_params.atr_stop_mult:.2f},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
