# RESULTS — TF-06 ADX + EMA Directional System

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf06_adx_ema` |
| Strategy | ADX + EMA Directional System |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-06` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 5 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Same backtester conventions as TF-01/TF-02 (one position at a time, entries at bar close, stop checked before target intrabar, P&L in R units, spread `0.00008`). See [`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `adx_period` | [10, 14, 20]               — 3 values |
| `adx_threshold` | [15, 20, 25, 30]           — 4 values |
| `trend_ema` | [20, 50, 100]              — 3 values |
| `di_cross` | [true, false]              — 2 values |
| `atr_stop_mult` | [1.0, 1.5, 2.0]           — 3 values |
| `timeframe` | [5min, 15min]              — 2 values |

| **Total combinations** | **432** (~216 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `adx_period` | 20 |
| `adx_threshold` | 30 |
| `trend_ema` | 100 |
| `di_cross` | True |
| `atr_stop_mult` | 1.50 |
| `tf_min` | 15 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-0.2715** |
| Profit Factor | 0.8427 |
| Max Drawdown (R, absolute) | 34.44 |
| Total Return (R) | -26.51 |
| Number of Trades | 313 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | adx_period=20, adx_threshold=30, trend_ema=100, di_cross=True, atr_mult=2.00, tf=5 | -0.079 | -1.720 | 0.527 | 44.1 | 166 |
| 2 | 2003–2016 | 2017–2020 | adx_period=14, adx_threshold=30, trend_ema=100, di_cross=True, atr_mult=1.50, tf=15 | -0.146 | -1.493 | 0.620 | 49.0 | 208 |
| 3 | 2003–2018 | 2019–2022 | adx_period=20, adx_threshold=25, trend_ema=100, di_cross=True, atr_mult=1.50, tf=15 | -0.265 | -0.336 | 0.905 | 27.2 | 243 |
| 4 | 2003–2020 | 2021–2025 | adx_period=20, adx_threshold=30, trend_ema=100, di_cross=True, atr_mult=1.50, tf=15 | -0.163 | -0.638 | 0.683 | 14.2 | 70 |

All 4 oos windows negative.

---

## Key Finding

**No edge found on full history.** All 432 combinations produce negative Sharpe and profit factor below 1.0.

- 0 / 432 combinations with Sharpe > 0
- 0 / 432 combinations with Profit Factor > 1.0
- Best Sharpe: -0.2715 (adx_period=20, adx_threshold=30, trend_ema=100, di_cross=True, atr_stop_mult=1.50, tf_min=15)
- Worst Sharpe: -22.2464 (adx_period=10, adx_threshold=15, trend_ema=20, di_cross=False, atr_stop_mult=1.00, tf_min=5)

Compared to TF-02 (-0.17) and TF-03 (-2.10), best Sharpe -0.2715 sits between prior MACD/EMA variants.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 15-min (15-min mean -2.53, 5-min mean -8.14) |
| `atr_stop_mult` | Wider stops less bad (2.00× vs 1.00×) |


---

## Recommendation

**Do not implement TF-06 standalone.** No expectancy edge on EURUSD under this grid.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 432 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
