# RESULTS — TF-10 Parabolic SAR

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf10_parabolic_sar` |
| Strategy | Parabolic SAR |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-10` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 4 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as the rest of the family (entries at bar close, stop checked first intrabar, P&L in R units, spread `0.00008`). SAR is the trailing stop (indicator-as-stop family); P&L is normalised by the initial SAR distance. See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `af_start` | [0.01, 0.02, 0.03, 0.05]     — 4 values |
| `af_step` | [0.01, 0.02, 0.03]           — 3 values |
| `af_max` | [0.10, 0.15, 0.20, 0.30]    — 4 values |
| `mode` | [standalone, exit_only]      — 2 values |
| `timeframe` | [5min, 15min]               — 2 values |

| **Total combinations** | **192** (~96 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `af_start` | 0.01 |
| `af_step` | 0.03 |
| `af_max` | 0.30 |
| `mode` | exit_only |
| `tf_min` | 5 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **35.3237** |
| Profit Factor | 60.3333 |
| Max Drawdown (R, absolute) | 56.41 |
| Total Return (R) | 38,471.20 |
| Number of Trades | 56,694 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | af_start=0.01, af_step=0.03, af_max=0.30, mode=exit_only, tf=5 | 37.378 | 33.881 | 59.485 | 3.2 | 9939 |
| 2 | 2003–2016 | 2017–2020 | af_start=0.02, af_step=0.01, af_max=0.30, mode=exit_only, tf=5 | 36.319 | 35.559 | 66.387 | 3.1 | 8852 |
| 3 | 2003–2018 | 2019–2022 | af_start=0.01, af_step=0.03, af_max=0.30, mode=exit_only, tf=5 | 36.456 | 30.969 | 44.585 | 1.5 | 9875 |
| 4 | 2003–2020 | 2021–2025 | af_start=0.01, af_step=0.03, af_max=0.30, mode=exit_only, tf=5 | 36.208 | 32.345 | 54.091 | 2.7 | 12216 |

4 of 4 oos windows positive.

---

## Research Caveat (indicator-as-stop family)

Full-history Sharpe and profit factor values are **not credible for deployment**.
SAR-as-stop with `R = |entry − SAR|` can be near-zero, producing implausible metrics
(best Sharpe 35.32, PF 60.33 on 56k trades). Treat as engine smoke test only.

---

## Key Finding

**Engine metrics not trustworthy.** All 192 combos report Sharpe > 0 with magnitudes
that indicate R-normalisation artifacts, not real edge.

- 192 / 192 combinations with Sharpe > 0
- 192 / 192 combinations with Profit Factor > 1.0
- Best Sharpe: 35.3237 (af_start=0.01, af_step=0.03, af_max=0.30, mode=exit_only, tf_min=5)
- Worst Sharpe: 4.3670 (af_start=0.01, af_step=0.03, af_max=0.10, mode=standalone, tf_min=15)

Compared to TF-02 (best Sharpe −0.17), **do not interpret TF-10 Sharpe values as
comparable** until SAR-as-stop P&L normalisation is fixed.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 5-min (15-min mean 14.77, 5-min mean 27.81) |


---

## Recommendation

**Do not implement TF-10 standalone.** Pending backtest engine audit for
SAR-as-stop R normalisation.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 192 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
