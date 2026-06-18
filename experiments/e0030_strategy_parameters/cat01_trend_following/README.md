# cat01 — Trend-Following Parameter Search

## Overview

Sub-experiment of `e0030_strategy_parameters`. Searches for optimal parameters
for each of the **20 trend-following strategies** documented in
[`strategies/01_TREND_FOLLOWING.md`](../../../strategies/01_TREND_FOLLOWING.md).

## Instrument

**EURUSD** — full history 2003–2025 (≈ 5.8 M 1-minute bars across 22 years).
Data path: `data/bars/EURUSD/EURUSD_<YEAR>.csv.gz` (read-only).

## Method

Each strategy is implemented as an independent **Python** project (uv-managed).
Follow the performance playbook in
[`tf01_ema_crossover_python/`](./tf01_ema_crossover_python/) — copy its patterns
into each folder; never import across experiments. The driver:

1. Loads and concatenates all EURUSD yearly files (Polars → NumPy struct-of-arrays).
2. Resamples 1-min bars to the strategy's target timeframe (5-min or 15-min).
3. Iterates over the full parameter grid defined in the strategy's `README.md`.
4. For each combination, simulates the strategy and computes:
   - Sharpe Ratio (annualised)
   - Profit Factor
   - Maximum Drawdown
   - Total Return
   - Number of trades
5. Writes all results to `outputs/results.csv` and the top-10 by Sharpe to
   `outputs/top_params.json`.
6. Runs a walk-forward validation on the top combination and writes
   `outputs/walkforward.csv`.

## Common Python Project Phases

All 20 sub-sub-experiments follow identical implementation phases (documented
in each strategy's `ROADMAP.md`; canonical detail in
[`tf01_ema_crossover_python/ROADMAP.md`](./tf01_ema_crossover_python/ROADMAP.md)):

| Phase | Task |
|---|---|
| 0 | `uv init` — Python project setup, pinned deps, pytest + ruff |
| 1 | Data loading — Polars CSV read → NumPy struct-of-arrays |
| 2 | Resampling — Numba `@njit` aggregation to target TF |
| 3 | Indicator computation — Numba kernels for strategy-specific indicators |
| 4 | Backtest engine — Numba `@njit` signal generation, position tracking, P&L |
| 5 | Parameter grid search — enumerate all combinations; `numba.prange` |
| 6 | Walk-forward validation — rolling in-sample/out-of-sample windows |
| 7 | Output reporting — write CSV/JSON results |

## Sub-Sub-Experiments

| # | Strategy | Folder | Approx. Grid Size |
|---|---|---|---|
| TF-01 | EMA Crossover | `tf01_ema_crossover_python/` (canonical; Rust sibling `tf01_ema_crossover/`) | ~1,500 |
| TF-02 | Triple EMA Alignment | `tf02_triple_ema/` | 720 |
| TF-03 | MACD Crossover | `tf03_macd_crossover/` | ~720 |
| TF-04 | MACD + 200 EMA | `tf04_macd_200ema/` | ~648 |
| TF-05 | EMA + RSI | `tf05_ema_rsi/` | ~1,536 |
| TF-06 | ADX + EMA | `tf06_adx_ema/` | ~432 |
| TF-07 | SuperTrend | `tf07_supertrend/` | ~810 |
| TF-08 | SuperTrend + VWAP + ADX | `tf08_supertrend_vwap_adx/` | ~576 |
| TF-09 | VWAP Trend Bias | `tf09_vwap_trend/` | ~120 |
| TF-10 | Parabolic SAR | `tf10_parabolic_sar/` | ~240 |
| TF-11 | Ichimoku Cloud | `tf11_ichimoku/` | ~216 |
| TF-12 | Williams Alligator | `tf12_alligator/` | ~150 |
| TF-13 | EMA Ribbon | `tf13_ema_ribbon/` | ~324 |
| TF-14 | Hull MA (HMA) | `tf14_hma/` | ~300 |
| TF-15 | EMA Pullback | `tf15_ema_pullback/` | ~480 |
| TF-16 | LinReg Channel | `tf16_linreg_channel/` | ~288 |
| TF-17 | Donchian Breakout | `tf17_donchian/` | ~270 |
| TF-18 | N-Bar Breakout | `tf18_nbar_breakout/` | ~420 |
| TF-19 | ROC Breakout | `tf19_roc_breakout/` | ~480 |
| TF-20 | Elder Impulse | `tf20_elder_impulse/` | ~1,728 |

## Status

All 20 sub-sub-experiments have their folder structure defined.
TF-01 is complete (Python reference + legacy Rust sibling). TF-02 is complete
(Python). TF-03–20: Python implementation pending — follow
[`tf01_ema_crossover_python/`](./tf01_ema_crossover_python/).
