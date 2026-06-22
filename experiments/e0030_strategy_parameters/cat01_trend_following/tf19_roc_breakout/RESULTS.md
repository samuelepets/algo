# RESULTS — TF-19 Rate of Change (ROC) Breakout

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf19_roc_breakout` |
| Strategy | Momentum (ROC) Breakout |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-19` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — 5-min grid only ≈ 5 s (`main.py` crashes on 1-min, exit 138) |
| Run date | 2026-06-22 |
| **Run scope** | **5-min timeframe only (432/864 combos)** — 1-min kernel aborts |

---

## Implementation Notes

ROC threshold breakout with optional longer-period ROC filter and fixed holding-period
exit. P&L in R units, spread `0.00008`. See [`README.md`](./README.md).

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `roc_period` | [3, 5, 10, 15, 20, 30]     — 6 values |
| `threshold_pct` | [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]  — 6 values |
| `long_roc_filter` | [none, 30, 60]              — 3 values |
| `holding_bars` | [5, 10, 20, 30]             — 4 values |
| `timeframe` | [1min, 5min]                — 2 values |

| **Total combinations** | **432** (5-min only; 1-min not run — see Run scope) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `roc_period` | 3 |
| `threshold_pct` | 0.30 |
| `long_roc_filter` | none |
| `holding_bars` | 20 |
| `tf_min` | 5 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **0.5659** |
| Profit Factor | 1.1407 |
| Max Drawdown (R, absolute) | 40.05 |
| Total Return (R) | 185.46 |
| Number of Trades | 2,619 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | roc3 t0.30 fnone h30 5m | 0.861 | 0.524 | 1.136 | 18.1 | 414 |
| 2 | 2003–2016 | 2017–2020 | roc3 t0.30 fnone h20 5m | 0.871 | -0.156 | 0.951 | 23.4 | 210 |
| 3 | 2003–2018 | 2019–2022 | roc3 t0.30 fnone h20 5m | 0.832 | -0.286 | 0.921 | 25.3 | 287 |
| 4 | 2003–2020 | 2021–2025 | roc3 t0.30 fnone h20 5m | 0.716 | -0.082 | 0.976 | 29.5 | 370 |

1 / 4 OOS windows positive Sharpe (window 1); IS consistently strong.

---

## Key Finding

**Modest edge on 5-min EURUSD.** 48 / 432 combinations show positive Sharpe and
PF > 1.0. Best cluster: short ROC period (3), high threshold (0.30%), no filter,
holding 20–30 bars.

- 48 / 432 combinations with Sharpe > 0
- 48 / 432 combinations with Profit Factor > 1.0
- Best Sharpe: 0.5659 (roc3 t0.30 fnone h20 5m)
- Worst Sharpe: -13.7507 (long ROC periods, low thresholds)

Walk-forward IS Sharpe 0.72–0.87 across windows; OOS degrades after window 1.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `roc_period` | Short period (3) dominates all top-10 |
| `threshold_pct` | 0.30% threshold required — lower thresholds overtrade |
| `holding_bars` | 20–30 bars optimal hold window |
| `long_roc_filter` | No filter beats 30/60-period filters on best combos |

---

## Recommendation

**Worth further validation.** Best Sharpe in this batch (+0.57) with reasonable
drawdown (+185 R, max DD 40 R). Confirm on 1-min grid (once kernel abort fixed),
out-of-sample holdout, and other instruments before deployment.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 432 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
