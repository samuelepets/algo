# RESULTS — TF-11 Ichimoku Cloud System

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf11_ichimoku` |
| Strategy | Ichimoku Cloud System |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-11` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 3 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as the rest of the family (entries at bar close, stop checked first intrabar, P&L in R units, spread `0.00008`). Displacement = Kijun period `n2` (traditional). The Kijun-sen is the trailing stop. See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `tenkan` | [7, 9, 10, 13]                        — 4 values |
| `kijun` | [20, 22, 26, 30]                      — 4 values |
| `senkou_b` | [44, 52, 60]                           — 3 values |
| `signal_type` | [full_signal, tk_cross, cloud_break]   — 3 values |
| `timeframe` | [15min, 1h]                            — 2 values |

| **Total combinations** | **288** (~144 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `tenkan` | 13 |
| `kijun` | 26 |
| `senkou_b` | 60 |
| `signal_type` | full_signal |
| `tf_min` | 60 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-0.5510** |
| Profit Factor | 0.8645 |
| Max Drawdown (R, absolute) | 139.98 |
| Total Return (R) | -132.05 |
| Number of Trades | 1,797 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | tenkan=10, kijun=30, senkou_b=52, signal=full_signal, tf=60 | -0.348 | -0.682 | 0.814 | 38.2 | 236 |
| 2 | 2003–2016 | 2017–2020 | tenkan=10, kijun=26, senkou_b=52, signal=full_signal, tf=60 | -0.392 | -1.307 | 0.691 | 63.2 | 311 |
| 3 | 2003–2018 | 2019–2022 | tenkan=10, kijun=30, senkou_b=52, signal=full_signal, tf=60 | -0.431 | -1.009 | 0.755 | 41.2 | 268 |
| 4 | 2003–2020 | 2021–2025 | tenkan=13, kijun=26, senkou_b=60, signal=full_signal, tf=60 | -0.394 | -1.110 | 0.751 | 70.7 | 394 |

All 4 oos windows negative.

---

## Key Finding

**No edge found on full history.** All 288 combinations produce negative Sharpe and profit factor below 1.0.

- 0 / 288 combinations with Sharpe > 0
- 0 / 288 combinations with Profit Factor > 1.0
- Best Sharpe: -0.5510 (tenkan=13, kijun=26, senkou_b=60, signal_type=full_signal, tf_min=60)
- Worst Sharpe: -7.3792 (tenkan=9, kijun=20, senkou_b=44, signal_type=cloud_break, tf_min=15)

Compared to TF-02 (-0.17) and TF-03 (-2.10), best Sharpe -0.5510 sits between prior MACD/EMA variants.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 60-min (15-min mean -4.46, 60-min mean -1.25) |


---

## Recommendation

**Do not implement TF-11 standalone.** No expectancy edge on EURUSD under this grid.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 288 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
