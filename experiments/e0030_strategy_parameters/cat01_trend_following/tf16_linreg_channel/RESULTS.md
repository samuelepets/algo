# RESULTS — TF-16 Linear Regression Channel

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf16_linreg_channel` |
| Strategy | Linear Regression Channel (bounce / breakout) |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-16` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 65 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Rolling OLS regression on close prices defines center line and σ-bands.
Entry modes: bounce from center (bull) or breakout above upper channel.
Same backtester conventions (entries at bar close, stop first intrabar, P&L in R,
spread `0.00008`). See [`README.md`](./README.md).

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `linreg_period` | [30, 50, 75, 100, 150, 200]   — 6 values |
| `channel_width_k` | [1.0, 1.5, 2.0, 2.5]          — 4 values |
| `entry_type` | [bounce_center, breakout_upper]  — 2 values |
| `atr_stop_mult` | [1.0, 1.5, 2.0]                — 3 values |
| `timeframe` | [5min, 15min]                     — 2 values |

| **Total combinations** | **288** |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `linreg_period` | 200 |
| `channel_width_k` | 2.50 |
| `entry_type` | breakout_upper |
| `atr_stop_mult` | 2.00 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-0.0502** |
| Profit Factor | 0.9928 |
| Max Drawdown (R, absolute) | 197.21 |
| Total Return (R) | -23.62 |
| Number of Trades | 4,793 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | lr150 k2.5 breakout_upper 2.0x 15m | 0.854 | -0.042 | 0.995 | 52.2 | 1,029 |
| 2 | 2003–2016 | 2017–2020 | lr150 k2.5 breakout_upper 2.0x 15m | 0.720 | -0.866 | 0.894 | 116.0 | 1,040 |
| 3 | 2003–2018 | 2019–2022 | lr150 k2.5 breakout_upper 2.0x 15m | 0.628 | -1.796 | 0.793 | 163.0 | 1,042 |
| 4 | 2003–2020 | 2021–2025 | lr150 k2.5 breakout_upper 2.0x 15m | 0.368 | -1.617 | 0.810 | 196.1 | 1,293 |

IS Sharpe positive in all windows; all 4 OOS windows negative.

---

## Key Finding

**No robust edge on full history.** Best full-history Sharpe is essentially flat
(-0.05) with PF below 1.0. Walk-forward IS periods look favourable but OOS
degrades sharply — classic overfit signature.

- 0 / 288 combinations with Sharpe > 0
- 0 / 288 combinations with Profit Factor > 1.0
- Best Sharpe: -0.0502 (lr200 k2.5 breakout_upper 2.0x 15m)
- Worst Sharpe: -14.9501 (tight channel / bounce on 5m)

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min mean Sharpe -1.83 vs 5-min mean -5.92 |
| `entry_type` | breakout_upper dominates top-10; bounce_center much worse |
| `channel_width_k` | Wider channels (k=2.5) least bad |
| `linreg_period` | Longer periods (150–200) preferred |

---

## Recommendation

**Do not implement TF-16 standalone.** Marginal full-history result does not
survive walk-forward OOS. Investigate only as part of a broader ensemble if at all.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 288 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
