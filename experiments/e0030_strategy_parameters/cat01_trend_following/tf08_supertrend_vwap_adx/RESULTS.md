# RESULTS — TF-08 SuperTrend + VWAP + ADX Combo

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf08_supertrend_vwap_adx` |
| Strategy | SuperTrend + VWAP + ADX Combo |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-08` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 22 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as the rest of the family (one position at a time, entries at bar close, stop checked before target intrabar, P&L in R units, spread `0.00008`). Stop is the SuperTrend line (indicator-as-stop family). See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `st_atr` | [7, 10, 14]               — 3 values |
| `st_mult` | [2.0, 2.5, 3.0, 3.5]     — 4 values |
| `adx_period` | [10, 14]                  — 2 values |
| `adx_threshold` | [20, 25, 30]             — 3 values |
| `trend_ema` | [20, 21, 50]             — 3 values |
| `atr_target` | [1.5, 2.0, 2.5, 3.0]    — 4 values |
| `timeframe` | [5min, 15min]            — 2 values |

| **Total combinations** | **1728** (~864 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `st_atr` | 7 |
| `st_mult` | 3.5 |
| `adx_period` | 10 |
| `adx_threshold` | 20 |
| `trend_ema` | 21 |
| `atr_target` | 2.5 |
| `tf_min` | 5 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **15.1705** |
| Profit Factor | 1.9007 |
| Max Drawdown (R, absolute) | 14.20 |
| Total Return (R) | 13,262.46 |
| Number of Trades | 64,683 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | st_atr=7, st_mult=3.5, adx_period=10, adx_threshold=20, trend_ema=21, atr_target=2.5, tf=5 | 14.129 | 16.772 | 1.962 | 12.4 | 12587 |
| 2 | 2003–2016 | 2017–2020 | st_atr=7, st_mult=3.5, adx_period=10, adx_threshold=20, trend_ema=21, atr_target=2.5, tf=5 | 14.599 | 15.952 | 1.905 | 12.4 | 12664 |
| 3 | 2003–2018 | 2019–2022 | st_atr=7, st_mult=3.5, adx_period=10, adx_threshold=20, trend_ema=21, atr_target=2.5, tf=5 | 14.837 | 16.182 | 1.911 | 12.0 | 12910 |
| 4 | 2003–2020 | 2021–2025 | st_atr=7, st_mult=3.5, adx_period=10, adx_threshold=20, trend_ema=21, atr_target=2.5, tf=5 | 14.913 | 16.059 | 1.904 | 14.2 | 16390 |

4 of 4 oos windows positive.

---

## Research Caveat (indicator-as-stop family)

Full-history Sharpe and profit factor values are **not credible for deployment**.
SuperTrend-as-stop with `R = |entry − line|` can be near-zero, inflating R-normalised
metrics (best Sharpe 15.17 and PF 1.90 are not plausible on 23 years of EURUSD).
Treat as engine smoke test only; audit required before cross-strategy comparison.

---

## Key Finding

**Engine metrics not trustworthy.** 1704/1728 combos report Sharpe > 0, but magnitudes
indicate R-normalisation artifacts, not real edge.

- 1704 / 1728 combinations with Sharpe > 0
- 1704 / 1728 combinations with Profit Factor > 1.0
- Best Sharpe: 15.1705 (st_atr=7, st_mult=3.5, adx_period=10, adx_threshold=20, trend_ema=21, atr_target=2.5, tf_min=5)
- Worst Sharpe: -0.1422 (st_atr=10, st_mult=2.5, adx_period=14, adx_threshold=30, trend_ema=50, atr_target=2.5, tf_min=5)

Compared to TF-02 (best Sharpe −0.17), **do not interpret TF-08 Sharpe values as
comparable** until indicator-as-stop P&L normalisation is fixed.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 15-min (15-min mean 4.50, 5-min mean 4.44) |


---

## Recommendation

**Do not implement TF-08 standalone.** Pending backtest engine audit for
indicator-as-stop R normalisation.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 1728 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
