# RESULTS — TF-15 EMA Pullback to Dynamic Support

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf15_ema_pullback` |
| Strategy | EMA Pullback to Dynamic Support |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-15` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — 5-min grid only ≈ 5 s (`main.py` crashes on 1-min, exit 138) |
| Run date | 2026-06-22 |
| **Run scope** | **5-min timeframe only (360/720 combos)** — 1-min kernel aborts |

---

## Implementation Notes

Same backtester conventions as the rest of the family (entries at bar close, stop
checked first intrabar, P&L in R units, spread `0.00008`). Pullback entries
require price above slow EMA with a touch of fast EMA and optional candle-pattern
filter. See [`README.md`](./README.md).

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `fast_ema` | [8, 9, 13, 20, 21]                — 5 values |
| `slow_ema` | [50, 100, 200]                     — 3 values |
| `pullback_touch` | [low_touches, close_near_ema]    — 2 values |
| `candle_pattern` | [engulfing, hammer, any, none]   — 4 values |
| `atr_stop_mult` | [1.0, 1.5, 2.0]                  — 3 values |
| `timeframe` | [1min, 5min]                       — 2 values |

| **Total combinations** | **360** (5-min only; 1-min not run — see Run scope) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `fast_ema` | 20 |
| `slow_ema` | 200 |
| `pullback_touch` | low_touches |
| `candle_pattern` | hammer |
| `atr_stop_mult` | 2.00 |
| `tf_min` | 5 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-3.0027** |
| Profit Factor | 0.7778 |
| Max Drawdown (R, absolute) | 2,347.18 |
| Total Return (R) | -2,342.77 |
| Number of Trades | 13,879 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | ema20/200 low_touches hammer 2.0x 5m | -2.742 | -2.761 | 0.795 | 392.9 | 2,483 |
| 2 | 2003–2016 | 2017–2020 | ema20/200 low_touches hammer 2.0x 5m | -2.714 | -3.749 | 0.732 | 533.0 | 2,441 |
| 3 | 2003–2018 | 2019–2022 | ema20/200 low_touches hammer 2.0x 5m | -2.736 | -3.539 | 0.746 | 492.4 | 2,474 |
| 4 | 2003–2020 | 2021–2025 | ema20/200 low_touches hammer 2.0x 5m | -2.946 | -3.174 | 0.768 | 555.9 | 3,068 |

All 4 OOS windows negative.

---

## Key Finding

**No edge found on full history.** All 360 combinations (5-min) produce negative
Sharpe ratios and profit factors below 1.0.

- 0 / 360 combinations with Sharpe > 0
- 0 / 360 combinations with Profit Factor > 1.0
- Best Sharpe overall: -3.0027 (ema20/200, low_touches, hammer, 2.0x, 5m)
- Worst Sharpe: -50.7562 (tight stops / fast EMAs on 5m)

Compared to TF-19 (best Sharpe +0.57 on 5m ROC), EMA pullback entries on EURUSD
are materially unprofitable under this grid.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `slow_ema` | Longer slow EMA (200) least bad — best combos cluster at slow=200 |
| `candle_pattern` | Hammer filter slightly better than engulfing/any/none |
| `atr_stop_mult` | Wider stops (2.0×) dominate top-10 |
| `pullback_touch` | low_touches preferred over close_near_ema |

---

## Recommendation

**Do not implement TF-15 standalone.** No expectancy edge on EURUSD under this
grid. Re-run 1-min grid after resolving Numba kernel abort (exit 138).

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 360 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
