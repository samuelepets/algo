# RESULTS — TF-17 Donchian Channel Breakout

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf17_donchian` |
| Strategy | Turtle-style Donchian Channel Breakout |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-17` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 62 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Separate entry and exit Donchian channels (exit < entry). Long entry on close
above upper entry band; exit on close below exit lower band. Optional ATR buffer
on entry. Exits are channel-based (no fixed R:R target). Spread `0.00008`.
See [`README.md`](./README.md).

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `entry_channel` | [10, 15, 20, 30, 40, 55]   — 6 values |
| `exit_channel` | [5, 8, 10, 15, 20]          — 5 values |
| `buffer_atr` | [0.0, 0.1, 0.2]                — 3 values |
| `timeframe` | [5min, 15min, 1h]               — 3 values |

| **Total combinations** | **216** (270 nominal; exit ≥ entry pairs excluded) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `entry_channel` | 20 |
| `exit_channel` | 15 |
| `buffer_atr` | 0.20 |
| `tf_min` | 60 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **0.0287** |
| Profit Factor | 1.0069 |
| Max Drawdown (R, absolute) | 127.68 |
| Total Return (R) | 14.24 |
| Number of Trades | 3,479 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | entry15/exit8 buf0.2 60m | 0.249 | 0.140 | 1.028 | 31.8 | 867 |
| 2 | 2003–2016 | 2017–2020 | entry15/exit8 buf0.2 60m | 0.255 | -0.252 | 0.953 | 42.6 | 866 |
| 3 | 2003–2018 | 2019–2022 | entry20/exit8 buf0.2 60m | 0.240 | -0.598 | 0.889 | 52.7 | 764 |
| 4 | 2003–2020 | 2021–2025 | entry20/exit8 buf0.2 60m | 0.157 | -0.497 | 0.903 | 66.0 | 976 |

1 / 4 OOS windows positive Sharpe (window 1 only).

---

## Key Finding

**Marginal edge on 1-hour timeframe only.** Only 4 / 216 combinations show
positive Sharpe and PF > 1.0 — all on 60-min bars. Lower timeframes are strongly
negative.

- 4 / 216 combinations with Sharpe > 0 (all tf=60)
- 4 / 216 combinations with Profit Factor > 1.0
- Best Sharpe: 0.0287 (entry20/exit15 buf0.2 60m)
- Worst Sharpe: -8.8452 (short channels on 5m)

Walk-forward: first OOS window mildly positive; subsequent windows negative.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 60-min mean Sharpe -0.22 vs 15-min -1.59 vs 5-min -5.44 |
| `entry_channel` | Medium entry (15–20) with exit 8–15 best on 1h |
| `buffer_atr` | Small positive buffer (0.1–0.2 ATR) helps on 1h |

---

## Recommendation

**Low priority.** Statistically negligible full-history edge (+14 R over 23 years,
Sharpe ≈ 0.03). Turtle-style Donchian on EURUSD 1h warrants further scrutiny
but not standalone deployment without OOS confirmation.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 216 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
