# RESULTS — TF-18 N-Bar High/Low Breakout

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf18_nbar_breakout` |
| Strategy | N-Period High/Low Breakout |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-18` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 64 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Simpler than Donchian: single N-bar lookback for entry, ATR stop and fixed R:R
target for exit. Optional volume filter. Spread `0.00008`. See [`README.md`](./README.md).

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `breakout_n` | [5, 10, 15, 20, 30, 40, 50]   — 7 values |
| `confirmation` | [close, high]                  — 2 values |
| `volume_filter` | [true, false]                 — 2 values |
| `atr_stop_mult` | [1.0, 1.5, 2.0, 2.5]         — 4 values |
| `rr_ratio` | [1.0, 1.5, 2.0]                    — 3 values |
| `timeframe` | [5min, 15min]                     — 2 values |

| **Total combinations** | **672** |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `breakout_n` | 15 |
| `confirmation` | high |
| `volume_filter` | false |
| `atr_stop_mult` | 2.50 |
| `rr_ratio` | 2.00 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-0.4290** |
| Profit Factor | 0.9607 |
| Max Drawdown (R, absolute) | 368.74 |
| Total Return (R) | -309.78 |
| Number of Trades | 11,442 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | n5 close vol=False 2.5x rr2.0 15m | -0.004 | -0.772 | 0.928 | 118.5 | 1,896 |
| 2 | 2003–2016 | 2017–2020 | n5 high vol=True 2.5x rr2.0 15m | -0.077 | 0.048 | 1.004 | 85.6 | 2,069 |
| 3 | 2003–2018 | 2019–2022 | n5 high vol=True 2.5x rr2.0 15m | -0.014 | -1.177 | 0.900 | 158.2 | 2,175 |
| 4 | 2003–2020 | 2021–2025 | n5 high vol=True 2.5x rr2.0 15m | -0.054 | -2.068 | 0.835 | 368.8 | 2,868 |

1 / 4 OOS windows marginally positive (window 2, Sharpe +0.05).

---

## Key Finding

**No edge found on full history.** All 672 combinations produce negative Sharpe
and PF below 1.0.

- 0 / 672 combinations with Sharpe > 0
- 0 / 672 combinations with Profit Factor > 1.0
- Best Sharpe: -0.4290 (n15 high vol=False 2.5x rr2.0 15m)
- Worst Sharpe: -31.6441 (short lookback, tight stops on 5m)

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min mean Sharpe -2.83 vs 5-min mean -9.26 |
| `breakout_n` | Longer N (15–40) least bad on 15m |
| `atr_stop_mult` | Wider stops (2.5×) dominate top-10 |
| `rr_ratio` | Higher R:R (2.0) slightly better than 1.0 |

---

## Recommendation

**Do not implement TF-18 standalone.** N-bar breakouts on EURUSD are net
losers under this grid despite occasional positive OOS windows.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 672 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
