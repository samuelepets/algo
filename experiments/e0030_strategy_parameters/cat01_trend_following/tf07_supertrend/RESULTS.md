# RESULTS — TF-07 SuperTrend

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf07_supertrend` |
| Strategy | SuperTrend |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-07` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 34 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as the rest of the family (one position at a time, entries at bar close, stop checked before target intrabar, P&L in R units, spread `0.00008`). SuperTrend belongs to the family whose **stop is the indicator itself**. See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `atr_period` | [5, 7, 10, 12, 14]       — 5 values |
| `multiplier` | [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]  — 6 values |
| `htf_filter` | [none, 15min, 1h]         — 3 values |
| `atr_target` | [1.0, 1.5, 2.0]          — 3 values (ATR multiple for fixed target) |
| `timeframe` | [1min, 5min, 15min]       — 3 values |

| **Total combinations** | **810** (~270 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `atr_period` | 5 |
| `multiplier` | 1.5 |
| `htf_filter` | none |
| `atr_target` | 2.0 |
| `tf_min` | 5 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **10.1530** |
| Profit Factor | 1.4671 |
| Max Drawdown (R, absolute) | 168.31 |
| Total Return (R) | 10,509.49 |
| Number of Trades | 84,357 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | atr_period=5, multiplier=3.5, htf=none, atr_target=2.0, tf=1 | 11.926 | 12.975 | 1.407 | 18.0 | 33124 |
| 2 | 2003–2016 | 2017–2020 | atr_period=5, multiplier=3.5, htf=none, atr_target=2.0, tf=1 | 12.514 | 5.046 | 1.149 | 479.9 | 32115 |
| 3 | 2003–2018 | 2019–2022 | atr_period=5, multiplier=3.5, htf=none, atr_target=2.0, tf=1 | 12.199 | 3.648 | 1.105 | 479.9 | 32790 |
| 4 | 2003–2020 | 2021–2025 | atr_period=5, multiplier=3.5, htf=none, atr_target=2.0, tf=1 | 10.655 | 4.761 | 1.138 | 320.8 | 42124 |

4 of 4 oos windows positive.

---

## Research Caveat (indicator-as-stop family)

Full-history Sharpe and profit factor values in this run are **not credible for
deployment**. When the trailing stop is the SuperTrend line, initial risk
`R = |entry − line|` can be vanishingly small on many entries, inflating
R-normalised P&L and annualised Sharpe (values ≫ 1 are a red flag on 23 years of
EURUSD). Treat these outputs as a **smoke test that the engine runs**, not evidence
of edge. An engine audit (minimum-R floor, stop/entry sequencing) is required before
any cross-strategy comparison.

---

## Key Finding

**Engine metrics not trustworthy.** The grid reports 615/810 combos with Sharpe > 0,
but the magnitude (best Sharpe 10.15) indicates R-normalisation artifacts, not a
real edge. Do not compare these numbers to TF-01..TF-06.

- 615 / 810 combinations with Sharpe > 0
- 615 / 810 combinations with Profit Factor > 1.0
- Best Sharpe: 10.1530 (atr_period=5, multiplier=1.5, htf_filter=none, atr_target=2.0, tf_min=5)
- Worst Sharpe: -34.1952 (atr_period=10, multiplier=1.5, htf_filter=none, atr_target=1.0, tf_min=1)

Compared to TF-02 (best Sharpe −0.17), **do not interpret TF-07 Sharpe values as
comparable** until the indicator-as-stop P&L normalisation is fixed.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 5-min (1-min mean -6.10, 15-min mean 4.53, 5-min mean 4.97) |


---

## Recommendation

**Do not implement TF-07 standalone.** Pending backtest engine audit for
indicator-as-stop R normalisation before any research conclusions.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 810 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
