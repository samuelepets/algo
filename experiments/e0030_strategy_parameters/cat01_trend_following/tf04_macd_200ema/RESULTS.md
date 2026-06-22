# RESULTS — TF-04 MACD + 200 EMA Trend Filter

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf04_macd_200ema` |
| Strategy | MACD + 200 EMA Trend Filter |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 8 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as TF-01/TF-02/TF-03 (one position at a time, entries at bar close, stop checked before target intrabar, P&L in R units, spread `0.00008`). See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `trend_ema` | [100, 150, 200, 250]    — 4 values |
| `macd_fast` | [8, 10, 12]            — 3 values |
| `macd_slow` | [21, 26, 30]           — 3 values |
| `macd_signal` | [7, 9]                 — 2 values |
| `atr_stop_mult` | [1.0, 1.5, 2.0]       — 3 values |
| `timeframe` | [5min, 15min]          — 2 values |

| **Total combinations** | **432** (216 per timeframe when applicable) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `trend_ema` | 100 |
| `macd_fast` | 12 |
| `macd_slow` | 30 |
| `macd_signal` | 9 |
| `atr_stop_mult` | 2.00 |
| `tf_min` | 15 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-2.3450** |
| Profit Factor | 0.8172 |
| Max Drawdown (R, absolute) | 1,502.97 |
| Total Return (R) | -1,479.07 |
| Number of Trades | 19,083 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. Selected params are logged.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | trend=250, fast=12, slow=26, signal=9, atr_mult=2.00, tf=15 | -2.259 | -2.504 | 0.816 | 317.2 | 3637 |
| 2 | 2003–2016 | 2017–2020 | trend=250, fast=12, slow=30, signal=9, atr_mult=2.00, tf=15 | -2.321 | -2.051 | 0.845 | 252.2 | 3537 |
| 3 | 2003–2018 | 2019–2022 | trend=250, fast=12, slow=26, signal=9, atr_mult=2.00, tf=15 | -2.315 | -2.516 | 0.817 | 312.7 | 3663 |
| 4 | 2003–2020 | 2021–2025 | trend=250, fast=12, slow=21, signal=9, atr_mult=2.00, tf=15 | -2.223 | -3.293 | 0.771 | 512.3 | 4709 |

All 4 oos windows are negative. IS-only selection details in `outputs/walkforward.csv`.

---

## Key Finding

**No edge found on full history.** All 432 combinations produce negative Sharpe ratios and profit factors below 1.0.

- 0 / 432 combinations with Sharpe > 0
- 0 / 432 combinations with Profit Factor > 1.0
- Best Sharpe overall: -2.3450 (trend_ema=100, macd_fast=12, macd_slow=30, macd_signal=9, atr_stop_mult=2.00, 15m)
- Worst Sharpe: -15.3285 (trend_ema=100, macd_fast=8, macd_slow=21, macd_signal=7, atr_stop_mult=1.00, 5m)

Compared to TF-01 (best Sharpe -0.56), TF-02 (best Sharpe -0.17), and TF-03 (best Sharpe -2.10), this strategy is **materially worse** on EURUSD full history (best Sharpe -2.3450).

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 15-min; all: 15-min (mean -3.26), 5-min (mean -11.22) |
| `atr_stop_mult` | Wider stops less bad (2.00× mean -6.24 vs 1.00× mean -8.60) |
| `macd_fast` | Best level 12 (mean Sharpe -6.84) |
| `macd_signal` | Best level 9 (mean Sharpe -6.96) |


---

## Recommendation

**Do not implement TF-04 standalone.**

No expectancy edge on EURUSD under this grid.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 432 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
