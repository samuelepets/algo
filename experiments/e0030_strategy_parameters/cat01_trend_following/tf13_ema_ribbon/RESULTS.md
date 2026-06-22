# RESULTS — TF-13 EMA Ribbon

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf13_ema_ribbon` |
| Strategy | EMA Ribbon |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-13` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 7 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as the rest of the family (entries at bar close, stop checked first intrabar, P&L in R units, spread `0.00008`). See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `ema_start` | [3, 5, 8]           — 3 values  (period of fastest EMA) |
| `ema_ratio` | [1.5, 1.618, 2.0]   — 3 values  (multiplicative step) |
| `ema_count` | [4, 5, 6]           — 3 values  (total EMAs) |
| `alignment_pct` | [0.8, 0.9, 1.0]     — 3 values  (min fraction in-order) |
| `expansion_bars` | [2, 3, 5]           — 3 values  (confirmation window) |
| `timeframe` | [5min, 15min]        — 2 values |

| **Total combinations** | **486** (~243 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `ema_start` | 8 |
| `ema_ratio` | 2.000 |
| `ema_count` | 6 |
| `alignment_pct` | 0.90 |
| `expansion_bars` | 5 |
| `tf_min` | 15 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-1.5576** |
| Profit Factor | 0.8692 |
| Max Drawdown (R, absolute) | 1,173.90 |
| Total Return (R) | -1,150.43 |
| Number of Trades | 12,210 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | ema_start=8, ema_ratio=1.618, ema_count=6, alignment_pct=0.90, expansion_bars=5, tf=15 | -1.508 | -1.229 | 0.909 | 211.9 | 2935 |
| 2 | 2003–2016 | 2017–2020 | ema_start=8, ema_ratio=1.618, ema_count=6, alignment_pct=0.90, expansion_bars=5, tf=15 | -1.533 | -0.958 | 0.928 | 194.7 | 2873 |
| 3 | 2003–2018 | 2019–2022 | ema_start=8, ema_ratio=1.618, ema_count=6, alignment_pct=0.90, expansion_bars=5, tf=15 | -1.424 | -2.224 | 0.842 | 337.4 | 2916 |
| 4 | 2003–2020 | 2021–2025 | ema_start=8, ema_ratio=2.000, ema_count=6, alignment_pct=0.90, expansion_bars=5, tf=15 | -1.379 | -2.191 | 0.823 | 363.3 | 2719 |

All 4 oos windows negative.

---

## Key Finding

**No edge found on full history.** All 486 combinations produce negative Sharpe and profit factor below 1.0.

- 0 / 486 combinations with Sharpe > 0
- 0 / 486 combinations with Profit Factor > 1.0
- Best Sharpe: -1.5576 (ema_start=8, ema_ratio=2.000, ema_count=6, alignment_pct=0.90, expansion_bars=5, tf_min=15)
- Worst Sharpe: -17.7374 (ema_start=3, ema_ratio=1.500, ema_count=4, alignment_pct=0.80, expansion_bars=2, tf_min=5)

Compared to TF-02 (-0.17) and TF-03 (-2.10), best Sharpe -1.5576 sits between prior MACD/EMA variants.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 15-min (15-min mean -2.98, 5-min mean -10.28) |


---

## Recommendation

**Do not implement TF-13 standalone.** No expectancy edge on EURUSD under this grid.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 486 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
