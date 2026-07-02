"""Interactive chart demo: price, Bollinger Bands/ADX, and marked trades.

Renders the best full-history combination found by the MR-01 grid search
(see RESULTS.md) over a bounded window, using the shared
``algo_shared.plotting`` visualizer. Writes a standalone HTML file to
``outputs/demo_chart.html`` — open it in a browser to pan/zoom and inspect
individual trades (entry/exit markers, connecting line, win/loss color).

Usage (from this directory):
    uv run python plot_demo.py [start_year] [end_year]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent / ".numba_cache"))

import numpy as np

from algo_shared.data import load_eurusd, resample, ts_range, year_start_ts
from algo_shared.plotting import Trade, plot_trades, save_html

from backtest import ENTRY_REENTRY, MAX_TRADES, backtest_core_with_trades
from indicators import ADX_PERIOD, ATR_PERIOD, atr, adx, sma, rolling_std_bb

# Best full-history combination from RESULTS.md (still net-negative — see
# "No edge found" — used here only to demonstrate the visualizer on a real
# trade set, not as a strategy recommendation).
BB_PERIOD = 30
BB_MULT = 3.0
ENTRY_TYPE = ENTRY_REENTRY
ADX_FILTER = 20
ATR_STOP_MULT = 1.5
MAX_HOLD_BARS = 20
TF_MIN = 15


def main() -> None:
    start_year = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
    end_year = int(sys.argv[2]) if len(sys.argv) > 2 else 2021

    data_dir = Path("../../../../data/bars/EURUSD")
    if not data_dir.exists():
        raise SystemExit(f"ERROR: Data directory not found at {data_dir.resolve()}")

    print("Loading EURUSD 1-min bars...")
    bars_1min = load_eurusd(data_dir)
    print(f"  {bars_1min.ts.size:,} bars")

    print(f"Resampling to {TF_MIN}-min...")
    bars = resample(bars_1min, TF_MIN)
    print(f"  {bars.ts.size:,} bars")

    print("Computing indicators (SMA/std/ATR/ADX) over full history...")
    sma_vals = sma(bars.close, BB_PERIOD)
    std_vals = rolling_std_bb(bars.close, BB_PERIOD)
    atr_vals = atr(bars.high, bars.low, bars.close, ATR_PERIOD)
    adx_vals = adx(bars.high, bars.low, bars.close, ADX_PERIOD)

    start_ts = year_start_ts(start_year)
    end_ts = year_start_ts(end_year + 1)
    s, e = ts_range(bars.ts, start_ts, end_ts)
    print(f"Display window: {start_year}-{end_year}  ({e - s:,} bars)")

    warm = max(BB_PERIOD, ADX_PERIOD * 2) + 1
    out_entry_ts = np.empty(MAX_TRADES, dtype=np.int64)
    out_exit_ts = np.empty(MAX_TRADES, dtype=np.int64)
    out_entry_price = np.empty(MAX_TRADES, dtype=np.float64)
    out_exit_price = np.empty(MAX_TRADES, dtype=np.float64)
    out_is_long = np.empty(MAX_TRADES, dtype=np.bool_)

    n_trades = backtest_core_with_trades(
        bars.open[s:e], bars.high[s:e], bars.low[s:e], bars.close[s:e], bars.ts[s:e],
        sma_vals[s:e], std_vals[s:e], atr_vals[s:e], adx_vals[s:e],
        BB_MULT, ENTRY_TYPE, ADX_FILTER, ATR_STOP_MULT, MAX_HOLD_BARS, warm,
        out_entry_ts, out_exit_ts, out_entry_price, out_exit_price, out_is_long,
    )
    print(f"  {n_trades} trades in window")

    trades = [
        Trade(
            entry_ts=int(out_entry_ts[i]),
            exit_ts=int(out_exit_ts[i]),
            entry_price=float(out_entry_price[i]),
            exit_price=float(out_exit_price[i]),
            is_long=bool(out_is_long[i]),
            pnl=(
                float(out_exit_price[i] - out_entry_price[i])
                if out_is_long[i]
                else float(out_entry_price[i] - out_exit_price[i])
            ),
        )
        for i in range(n_trades)
    ]

    upper_band = sma_vals[s:e] + BB_MULT * std_vals[s:e]
    lower_band = sma_vals[s:e] - BB_MULT * std_vals[s:e]

    fig = plot_trades(
        ts=bars.ts[s:e],
        open_=bars.open[s:e],
        high=bars.high[s:e],
        low=bars.low[s:e],
        close=bars.close[s:e],
        trades=trades,
        overlay_indicators={
            "SMA(30)": sma_vals[s:e],
            "Upper band": upper_band,
            "Lower band": lower_band,
        },
        panel_indicators={"ADX(14)": adx_vals[s:e]},
        title=(
            f"MR-01 Bollinger Band — EURUSD {TF_MIN}m — {start_year}-{end_year} — "
            f"bb{BB_PERIOD}/{BB_MULT}x reentry adx<{ADX_FILTER} "
            f"stop{ATR_STOP_MULT}x hold{MAX_HOLD_BARS} — {n_trades} trades"
        ),
    )

    outputs = Path("outputs")
    outputs.mkdir(exist_ok=True)
    out_path = outputs / "demo_chart.html"
    save_html(fig, out_path)
    print(f"Saved {out_path.resolve()}")


if __name__ == "__main__":
    main()
