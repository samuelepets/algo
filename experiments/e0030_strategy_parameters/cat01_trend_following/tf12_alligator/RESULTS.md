# RESULTS — TF-12 Williams Alligator

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf12_alligator` |
| Strategy | Williams Alligator |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-12` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 3 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as the rest of the family (entries at bar close, stop checked first intrabar, P&L in R units, spread `0.00008`). SMMA lines are computed on the **median price** `(high + low) / 2` and shifted forward. See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|

| **Total combinations** | **30** (~15 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `scale_factor` | 1.30 |
| `atr_stop_mult` | 2.00 |
| `tf_min` | 15 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-1.0221** |
| Profit Factor | 0.8537 |
| Max Drawdown (R, absolute) | 400.55 |
| Total Return (R) | -393.48 |
| Number of Trades | 5,373 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | scale_factor=1.15, atr_mult=2.00, tf=15 | -0.926 | -0.634 | 0.913 | 86.0 | 1065 |
| 2 | 2003–2016 | 2017–2020 | scale_factor=1.15, atr_mult=2.00, tf=15 | -0.937 | -0.612 | 0.914 | 58.8 | 1012 |
| 3 | 2003–2018 | 2019–2022 | scale_factor=1.00, atr_mult=2.00, tf=15 | -0.804 | -1.475 | 0.808 | 114.1 | 1088 |
| 4 | 2003–2020 | 2021–2025 | scale_factor=1.15, atr_mult=2.00, tf=15 | -0.858 | -1.932 | 0.753 | 183.1 | 1273 |

All 4 oos windows negative.

---

## Key Finding

**No edge found on full history.** All 30 combinations produce negative Sharpe and profit factor below 1.0.

- 0 / 30 combinations with Sharpe > 0
- 0 / 30 combinations with Profit Factor > 1.0
- Best Sharpe: -1.0221 (scale_factor=1.30, atr_stop_mult=2.00, tf_min=15)
- Worst Sharpe: -6.7642 (scale_factor=0.70, atr_stop_mult=1.00, tf_min=5)

Compared to TF-02 (-0.17) and TF-03 (-2.10), best Sharpe -1.0221 sits between prior MACD/EMA variants.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 15-min (15-min mean -1.46, 5-min mean -5.17) |
| `atr_stop_mult` | Wider stops less bad (2.00× vs 1.00×) |


---

## Recommendation

**Do not implement TF-12 standalone.** No expectancy edge on EURUSD under this grid.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 30 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
