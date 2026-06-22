# RESULTS — TF-09 VWAP Trend Bias

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf09_vwap_trend` |
| Strategy | VWAP Trend Bias |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-09` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 4 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as the rest of the family (one position at a time, entries at bar close, stop checked first intrabar, P&L in R units, spread `0.00008`). See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `vwap_reset` | [daily, session]           — 2 values |
| `entry_type` | [vwap_bounce, above_vwap]  — 2 values |
| `band_width_sigma` | [1.0, 1.5, 2.0]           — 3 values |
| `atr_stop_mult` | [0.75, 1.0, 1.5]          — 3 values |
| `timeframe` | [1min, 5min]               — 2 values |

| **Total combinations** | **72** (~36 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `vwap_reset` | session |
| `entry_type` | above_vwap |
| `band_sigma` | 2.0 |
| `atr_stop_mult` | 1.50 |
| `tf_min` | 5 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-2.3921** |
| Profit Factor | 0.7886 |
| Max Drawdown (R, absolute) | 5,222.24 |
| Total Return (R) | -5,208.62 |
| Number of Trades | 29,193 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | vwap_reset=session, entry_type=above_vwap, band_sigma=2.0, atr_mult=1.50, tf=5 | -1.625 | -2.072 | 0.816 | 853.9 | 5097 |
| 2 | 2003–2016 | 2017–2020 | vwap_reset=session, entry_type=above_vwap, band_sigma=2.0, atr_mult=1.50, tf=5 | -1.805 | -3.325 | 0.732 | 1316.0 | 5270 |
| 3 | 2003–2018 | 2019–2022 | vwap_reset=session, entry_type=above_vwap, band_sigma=2.0, atr_mult=1.50, tf=5 | -1.743 | -4.310 | 0.674 | 1607.2 | 5366 |
| 4 | 2003–2020 | 2021–2025 | vwap_reset=session, entry_type=above_vwap, band_sigma=2.0, atr_mult=1.50, tf=5 | -2.153 | -3.206 | 0.732 | 1590.2 | 6574 |

All 4 oos windows negative.

---

## Key Finding

**No edge found on full history.** All 72 combinations produce negative Sharpe and profit factor below 1.0.

- 0 / 72 combinations with Sharpe > 0
- 0 / 72 combinations with Profit Factor > 1.0
- Best Sharpe: -2.3921 (vwap_reset=session, entry_type=above_vwap, band_sigma=2.0, atr_stop_mult=1.50, tf_min=5)
- Worst Sharpe: -52.5733 (vwap_reset=daily, entry_type=vwap_bounce, band_sigma=1.5, atr_stop_mult=1.50, tf_min=1)

Compared to TF-01 (-0.56), TF-02 (-0.17), and TF-03 (-2.10), best Sharpe -2.3921 shows no improvement on EURUSD full history.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 5-min (1-min mean -24.92, 5-min mean -6.70) |
| `atr_stop_mult` | Wider stops less bad (1.50× vs 0.75×) |


---

## Recommendation

**Do not implement TF-09 standalone.** No expectancy edge on EURUSD under this grid.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 72 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
