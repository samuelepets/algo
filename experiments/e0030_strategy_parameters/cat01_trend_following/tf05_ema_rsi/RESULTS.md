# RESULTS — TF-05 EMA Crossover + RSI Momentum Filter

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf05_ema_rsi` |
| Strategy | EMA Crossover + RSI Momentum Filter |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — sequential grid ≈ 118 s end-to-end (parallel OOM on 1-min) |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as TF-01/TF-02 (one position at a time, entries at bar close, stop checked before target intrabar, P&L in R units, spread `0.00008`). See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `fast_ema` | [5, 7, 9, 12]          — 4 values |
| `slow_ema` | [18, 20, 21, 26]        — 4 values |
| `rsi_period` | [7, 10, 14]            — 3 values |
| `rsi_long_thresh` | [50, 52, 55, 57]       — 4 values |
| `rsi_short_thresh` | [50, 48, 45, 43]       — 4 values |
| `atr_stop_mult` | [0.75, 1.0, 1.5, 2.0] — 4 values |
| `timeframe` | [1min, 5min]           — 2 values |

| **Total combinations** | **1536** (768 per timeframe when applicable) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `fast_ema` | 7 |
| `slow_ema` | 20 |
| `rsi_period` | 14 |
| `rsi_long` | 57 |
| `rsi_short` | 43 |
| `atr_stop_mult` | 2.00 |
| `tf_min` | 5 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-4.0009** |
| Profit Factor | 0.7678 |
| Max Drawdown (R, absolute) | 3,687.59 |
| Total Return (R) | -3,685.83 |
| Number of Trades | 26,118 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. Selected params are logged.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | fast=7, slow=20, rsi_period=14, rsi_long=57, rsi_short=43, atr_mult=2.00 | -3.569 | -4.096 | 0.768 | 705.2 | 4630 |
| 2 | 2003–2016 | 2017–2020 | fast=7, slow=20, rsi_period=14, rsi_long=57, rsi_short=43, atr_mult=2.00 | -3.618 | -5.003 | 0.727 | 857.7 | 4695 |
| 3 | 2003–2018 | 2019–2022 | fast=9, slow=21, rsi_period=14, rsi_long=57, rsi_short=43, atr_mult=2.00 | -3.704 | -5.740 | 0.702 | 1022.1 | 4967 |
| 4 | 2003–2020 | 2021–2025 | fast=12, slow=18, rsi_period=14, rsi_long=57, rsi_short=43, atr_mult=2.00 | -3.936 | -4.848 | 0.747 | 1105.2 | 6424 |

All 4 oos windows are negative. IS-only selection details in `outputs/walkforward.csv`.

---

## Key Finding

**No edge found on full history.** All 1536 combinations produce negative Sharpe ratios and profit factors below 1.0.

- 0 / 1536 combinations with Sharpe > 0
- 0 / 1536 combinations with Profit Factor > 1.0
- Best Sharpe overall: -4.0009 (fast_ema=7, slow_ema=20, rsi_period=14, rsi_long=57, rsi_short=43, atr_stop_mult=2.00, 5m)
- Worst Sharpe: -84.5439 (fast_ema=5, slow_ema=18, rsi_period=10, rsi_long=50, rsi_short=50, atr_stop_mult=0.75, 1m)

Compared to TF-01 (best Sharpe -0.56), TF-02 (best Sharpe -0.17), and TF-03 (best Sharpe -2.10), this strategy is **materially worse** on EURUSD full history (best Sharpe -4.0009).

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 5-min; all: 1-min (mean -48.28), 5-min (mean -9.99) |
| `atr_stop_mult` | Wider stops less bad (2.00× mean -18.85 vs 0.75× mean -42.34) |
| `rsi_long` | Best level 57 (mean Sharpe -25.87) |
| `rsi_short` | Best level 43 (mean Sharpe -25.87) |


---

## Recommendation

**Do not implement TF-05 standalone.**

No expectancy edge on EURUSD under this grid.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 1536 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
