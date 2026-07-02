"""MR-16 Opening Range Mean Reversion parameter search."""

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

from backtest import TARGET_MID, TARGET_OPPOSITE, search_range
from indicators import (
    ATR_PERIOD,
    OR_DURATIONS,
    SESSIONS,
    atr,
    build_or_daily_cache,
    build_or_matrix,
)

REVERSAL_BARS_LIST = [1, 2, 3]
TARGETS = ["mid_range", "opposite_band"]
ATR_STOP_MULTS = [0.5, 1.0, 1.5]
SESSION_NAMES = ["london", "ny"]
TIMEFRAMES = [1, 5]
WARM_BARS = ATR_PERIOD + 2

_TARGET_LABELS = {TARGET_MID: "mid_range", TARGET_OPPOSITE: "opposite_band"}
_TARGET_CODES = {"mid_range": TARGET_MID, "opposite_band": TARGET_OPPOSITE}


@dataclass
class Params:
    or_duration_min: int
    reversal_bars: int
    target: str
    atr_stop_mult: float
    session: str
    tf_min: int


@dataclass
class TfData:
    tf_min: int
    bars: BarArrays
    atr_vals: np.ndarray
    orh_matrix: np.ndarray
    orl_matrix: np.ndarray
    row_index: dict[tuple[str, int], int]
    grid: list[Params]
    row_idx: np.ndarray
    or_window_end_min: np.ndarray
    reversal_bars: np.ndarray
    target_mode: np.ndarray
    atr_stop_mult: np.ndarray
    warm_bars: np.ndarray


def build_grid(tf_min: int) -> list[Params]:
    grid: list[Params] = []
    for or_dur in OR_DURATIONS:
        for rev_bars in REVERSAL_BARS_LIST:
            for target in TARGETS:
                for atr_m in ATR_STOP_MULTS:
                    for session in SESSION_NAMES:
                        grid.append(
                            Params(
                                or_duration_min=or_dur,
                                reversal_bars=rev_bars,
                                target=target,
                                atr_stop_mult=atr_m,
                                session=session,
                                tf_min=tf_min,
                            )
                        )
    return grid


def _grid_arrays(
    grid: list[Params], row_index: dict[tuple[str, int], int]
) -> tuple[np.ndarray, ...]:
    n = len(grid)
    row_idx = np.empty(n, dtype=np.int64)
    or_window_end_min = np.empty(n, dtype=np.int64)
    reversal_bars = np.empty(n, dtype=np.int64)
    target_mode = np.empty(n, dtype=np.int64)
    atr_stop_mult = np.empty(n, dtype=np.float64)
    warm_bars = np.empty(n, dtype=np.int64)
    for i, p in enumerate(grid):
        row_idx[i] = row_index[(p.session, p.or_duration_min)]
        or_window_end_min[i] = SESSIONS[p.session] + p.or_duration_min
        reversal_bars[i] = p.reversal_bars
        target_mode[i] = _TARGET_CODES[p.target]
        atr_stop_mult[i] = p.atr_stop_mult
        warm_bars[i] = WARM_BARS
    return row_idx, or_window_end_min, reversal_bars, target_mode, atr_stop_mult, warm_bars


def _prepare_tf(
    bars_1min: BarArrays,
    tf_min: int,
    daily_cache: dict[tuple[str, int], tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> TfData:
    bars_tf = resample(bars_1min, tf_min)
    atr_vals = atr(bars_tf.high, bars_tf.low, bars_tf.close, ATR_PERIOD)
    orh_matrix, orl_matrix, row_index = build_or_matrix(bars_tf.ts, daily_cache)
    grid = build_grid(tf_min)
    row_idx, or_window_end_min, reversal_bars, target_mode, atr_stop_mult, warm_bars = (
        _grid_arrays(grid, row_index)
    )
    return TfData(
        tf_min=tf_min,
        bars=bars_tf,
        atr_vals=atr_vals,
        orh_matrix=orh_matrix,
        orl_matrix=orl_matrix,
        row_index=row_index,
        grid=grid,
        row_idx=row_idx,
        or_window_end_min=or_window_end_min,
        reversal_bars=reversal_bars,
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
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.atr_vals,
        tf.orh_matrix,
        tf.orl_matrix,
        tf.row_idx,
        tf.or_window_end_min,
        tf.reversal_bars,
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

    row = tf.row_index[(params.session, params.or_duration_min)]
    or_window_end_min = SESSIONS[params.session] + params.or_duration_min

    search_range(
        tf.bars.open,
        tf.bars.high,
        tf.bars.low,
        tf.bars.close,
        tf.bars.ts,
        tf.atr_vals,
        tf.orh_matrix,
        tf.orl_matrix,
        np.array([row], dtype=np.int64),
        np.array([or_window_end_min], dtype=np.int64),
        np.array([params.reversal_bars], dtype=np.int64),
        np.array([_TARGET_CODES[params.target]], dtype=np.int64),
        np.array([params.atr_stop_mult], dtype=np.float64),
        np.array([WARM_BARS], dtype=np.int64),
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
            "mr16_opening_range_reversion/"
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

    print("\nComputing daily opening-range cache (8 session x duration combos)...")
    t_or = time.perf_counter()
    daily_cache = build_or_daily_cache(bars_1min.ts, bars_1min.high, bars_1min.low)
    print(f"  done [{time.perf_counter() - t_or:.2f}s]")

    tf_data: list[TfData] = []
    for tf_min in TIMEFRAMES:
        print(f"\nTimeframe: {tf_min}-min")
        t1 = time.perf_counter()
        tf = _prepare_tf(bars_1min, tf_min, daily_cache)
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
            "or_duration_min,reversal_bars,target,atr_stop_mult,session,tf_min,"
            "sharpe,profit_factor,max_drawdown_r,total_return,n_trades\n"
        )
        for p, m in all_results:
            fh.write(
                f"{p.or_duration_min},{p.reversal_bars},{p.target},"
                f"{p.atr_stop_mult:.2f},{p.session},{p.tf_min},"
                f"{m.sharpe:.6f},{m.profit_factor:.6f},"
                f"{m.max_drawdown_r:.6f},{m.total_return:.4f},{m.n_trades}\n"
            )
    print(f"  {len(all_results):,} rows written")

    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    valid = [(p, m) for p, m in all_results if m.n_trades >= MIN_TRADES]

    print(f"\nTop-10 (min {MIN_TRADES} trades, sorted by Sharpe):")
    print(
        f"{'or':<4} {'rev':<4} {'target':<14} {'stop':<5} {'sess':<7} {'tf':<4}  "
        f"{'sharpe':>8}  {'pf':>7}  {'max_dd_r':>8}  {'tot_R':>8}  {'trades':>7}"
    )
    for p, m in valid[:10]:
        print(
            f"{p.or_duration_min:<4} {p.reversal_bars:<4} {p.target:<14} "
            f"{p.atr_stop_mult:<5.1f} {p.session:<7} {p.tf_min:<4}  "
            f"{m.sharpe:>8.4f}  {m.profit_factor:>7.4f}  "
            f"{m.max_drawdown_r:>8.4f}  {m.total_return:>8.2f}  {m.n_trades:>7}"
        )

    print("\nWalk-forward optimisation (IS-only grid search per window)...")
    wf_path = outputs / "walkforward.csv"
    with wf_path.open("w", encoding="utf-8") as wf:
        wf.write(
            "window,is_start,is_end,oos_start,oos_end,"
            "sel_or_duration_min,sel_reversal_bars,sel_target,sel_atr_stop_mult,"
            "sel_session,sel_tf,"
            "is_sharpe,is_pf,is_n_trades,"
            "oos_sharpe,oos_pf,oos_max_drawdown_r,oos_n_trades\n"
        )
        print(
            f"\n{'win':<4}  {'IS':<12}  {'OOS':<12}  {'selected':<46}  "
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
                f"or{sel_params.or_duration_min}m rev{sel_params.reversal_bars} "
                f"{sel_params.target} stop{sel_params.atr_stop_mult:.1f}x "
                f"{sel_params.session} {sel_params.tf_min}m"
            )
            print(
                f"{idx + 1:<4}  {is_s}-{is_e:<7}  {oos_s}-{oos_e:<7}  "
                f"{selected_label:<46}  {is_m.sharpe:>8.4f}  {oos_m.sharpe:>8.4f}  "
                f"{oos_m.profit_factor:>7.4f}  {oos_m.n_trades:>7}"
            )
            wf.write(
                f"{idx + 1},{is_s},{is_e},{oos_s},{oos_e},"
                f"{sel_params.or_duration_min},{sel_params.reversal_bars},{sel_params.target},"
                f"{sel_params.atr_stop_mult:.2f},{sel_params.session},{sel_params.tf_min},"
                f"{is_m.sharpe:.6f},{is_m.profit_factor:.6f},{is_m.n_trades},"
                f"{oos_m.sharpe:.6f},{oos_m.profit_factor:.6f},"
                f"{oos_m.max_drawdown_r:.6f},{oos_m.n_trades}\n"
            )

    print(f"\nSaved {wf_path}")
    print(f"\nTotal elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
