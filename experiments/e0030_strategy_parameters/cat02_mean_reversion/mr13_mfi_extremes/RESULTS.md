# RESULTS — MR-13 Money Flow Index (MFI) Extremes

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr13_mfi_extremes` |
| Strategy | Money Flow Index (MFI) Extremes |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-13` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 2.7 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `mfi_period` | 7, 10, 14, 20 (4 values) |
| `oversold_thresh` | 10, 15, 20, 25 (4 values) |
| `overbought_thresh` | 90, 85, 80, 75 (4 values) |
| `exit_level` | 50 (1 value) |
| `atr_stop_mult` | 1.0, 1.5 (2 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **256** (128 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `mfi_period` | 14 |
| `oversold_thresh` | 10 |
| `overbought_thresh` | 90 |
| `exit_level` | 50 |
| `atr_stop_mult` | 1.0 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.0118** |
| Profit Factor | 0.9966 |
| Max Drawdown (R, absolute) | 78.34 |
| Total Return (R) | −2.71 |
| Number of Trades | 1,565 |

> Nearly breakeven — the closest-to-zero full-history result across all
> mean-reversion strategies documented so far in `cat02_mean_reversion`.

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

The same configuration (`mfi14`, `os10/ob90`, `exit50`, `stop1.0×`, 15-min)
was selected in every window.

| Window | IS | OOS | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | +0.468 | **+0.114** | 1.041 | 214 |
| 2 | 2003–2016 | 2017–2020 | +0.482 | −0.876 | 0.782 | 297 |
| 3 | 2003–2018 | 2019–2022 | +0.363 | −1.487 | 0.701 | 383 |
| 4 | 2003–2020 | 2021–2025 | +0.166 | −0.608 | 0.867 | 533 |

IS Sharpe is strongly positive in every window — but this is on the full
`mfi14/os10/ob90` combination's in-sample performance, which is *not* the
same as the modest full-history-only best above (the walk-forward IS metric
is computed on the growing IS window, not the full 23-year history). Window 1
is OOS-positive; windows 2–4 are OOS-negative and progressively worse.

---

## Key Finding

**No robust edge, but the least-bad and most internally-consistent result in
the category.** 0 / 256 combinations clear positive Sharpe/PF>1 on
full-history, but the gap to breakeven is small (Sharpe −0.012 vs. e.g.
MR-05's −2.13 or MR-01's −0.15). The `mfi14/os10/ob90` configuration is
selected consistently across all 4 walk-forward windows (unlike MR-08, where
IS selection wandered), and its IS Sharpe is consistently positive — but IS
positivity does not carry through to OOS reliably (1 of 4 windows OOS-
positive). Volume-weighting appears to filter out some of the false signals
that plague plain price oscillators (MR-05, MR-06) in this category, without
fully closing the gap to a tradable edge.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `tf_min` | 15-min much better than 5-min (avg Sharpe −0.95 vs −3.72) |
| `mfi_period` | Longer period better (avg −1.03 at 20 vs −4.11 at 7) |
| `oversold_thresh` / `overbought_thresh` | More extreme thresholds (10/90) better than looser (25/75) — avg −1.90 vs −2.81 |
| `atr_stop_mult` | Wider stop better (avg −2.02 at 1.5× vs −2.65 at 1.0×) |

---

## Recommendation

**Do not implement MR-13 standalone as-is, but it is the strongest candidate
for follow-up work in this category alongside MR-08.** Two possible next
steps: (1) tighten the exit rule (e.g. a partial R:R target in addition to
the MFI-50 crossback, since the crossback exit alone can give back much of
the move) or (2) test whether the OOS-positive window 1 result generalises
with a regime filter that would have avoided the later, more adverse
periods. As implemented, the walk-forward split is inconsistent (1 of 4
windows OOS-positive) and does not clear the bar for live/paper trading.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 256 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
