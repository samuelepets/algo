# RESULTS — TF-20 Elder Impulse System

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf20_elder_impulse` |
| Strategy | Elder Impulse System |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-20` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 75 s end-to-end |
| Run date | 2026-06-22 |
| **Run scope** | **Full grid completed — zero trades across all combinations** |

---

## Implementation Notes

Bar color from EMA slope + MACD histogram slope (Green / Red / Neutral).
Entry on first colored bar after neutral sequence. Same backtester conventions
(spread `0.00008`). See [`README.md`](./README.md).

**Known issue:** `macd_histogram()` returns all-NaN values after warmup in unit
tests; `elder_impulse_colors()` therefore emits only Neutral (0) bars, producing
zero trades for every parameter combination. Results below reflect this bug — not
a valid strategy evaluation.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `ema_period` | [10, 13, 20, 26]               — 4 values |
| `macd_fast` | [8, 10, 12]                    — 3 values |
| `macd_slow` | [21, 24, 26]                   — 3 values |
| `macd_signal` | [7, 9]                         — 2 values |
| `entry_condition` | [first_colored, any_colored]   — 2 values |
| `exit_condition` | [first_neutral, opposite_color] — 2 values |
| `atr_stop_mult` | [1.0, 1.5, 2.0]               — 3 values |
| `timeframe` | [5min, 15min]                  — 2 values |

| **Total combinations** | **1,728** |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| — | **No valid combination** (0 trades on all 1,728 sets) |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **n/a** |
| Profit Factor | n/a |
| Max Drawdown (R, absolute) | n/a |
| Total Return (R) | n/a |
| Number of Trades | 0 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

All 4 windows skipped — no IS combination met the ≥ 50 trades filter.

---

## Key Finding

**Results invalid — implementation bug.** Grid search completed but every
combination produced zero trades because MACD histogram values are never finite
after indicator warmup. Fix `indicators.macd_histogram` before re-running.

- 0 / 1,728 combinations with ≥ 50 trades
- 0 / 1,728 combinations with Sharpe > 0
- Unit tests `test_macd_histogram_warmup` and `test_elder_impulse_all_rising`
  also fail

---

## Parameter Insights

Not applicable until MACD histogram is fixed and grid search re-run.

---

## Recommendation

**Fix indicators, then re-run.** Do not draw conclusions about Elder Impulse on
EURUSD until `macd_histogram` produces valid post-warmup values and trades fire.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 1,728 combinations — all zero trades (not committed) |
| `outputs/top_params.json` | Empty top-10 (not committed) |
| `outputs/walkforward.csv` | Empty — no valid windows (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
