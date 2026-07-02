# RESULTS — MR-15 DeMarker Oscillator Reversion

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr15_demarker` |
| Strategy | DeMarker Oscillator Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-15` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 5.2 s end-to-end |
| Run date | 2026-07-02 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `demarker_period` | 5, 10, 14, 20 (4 values) |
| `oversold_thresh` | 0.05, 0.10, 0.15, 0.20 (4 values) |
| `overbought_thresh` | 0.95, 0.90, 0.85, 0.80 (4 values) |
| `exit_level` | 0.50 (1 value) |
| `atr_stop_mult` | 0.75, 1.0, 1.5 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **384** (192 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `demarker_period` | 20 |
| `oversold_thresh` | 0.05 |
| `overbought_thresh` | 0.95 |
| `exit_level` | 0.50 |
| `atr_stop_mult` | 1.00 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **+0.1843** |
| Profit Factor | 1.2064 |
| Max Drawdown (R, absolute) | 26.33 |
| Total Return (R) | 30.00 |
| Number of Trades | 218 |

> Only 218 trades over 23 years — a selective setup. The 5 next-best
> combinations are all close variants (same period, same or adjacent
> thresholds), confirming this is a real (if narrow) cluster rather than an
> isolated lucky cell.

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

The same `dem20/os0.05` family was selected in every window.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | dem20 os0.05/ob0.95 x0.50 stop1.0x 15m | **+0.437** | −0.921 | 0.517 | 35 |
| 2 | 2003–2016 | 2017–2020 | dem20 os0.05/ob0.90 x0.50 stop1.0x 15m | +0.300 | −1.020 | 0.686 | 164 |
| 3 | 2003–2018 | 2019–2022 | dem20 os0.05/ob0.95 x0.50 stop1.0x 15m | +0.252 | −0.196 | 0.870 | 49 |
| 4 | 2003–2020 | 2021–2025 | dem20 os0.05/ob0.95 x0.50 stop1.0x 15m | +0.278 | −0.089 | 0.918 | 57 |

IS Sharpe (+0.25 to +0.44) is the strongest and most consistent seen in this
category — but OOS is negative in every window, with generally thin trade
counts (35–164).

---

## Key Finding

**Real but narrow full-history cluster with the best IS walk-forward Sharpe
in the category, yet still fails OOS in all 4 windows.** 6 / 384 combinations
clear positive Sharpe and PF > 1.0 — verified clean of numerical artifacts
(max |total_return| row's per-trade average is a sane −0.22R across 188,973
trades, fully explained by overtrading at short periods, not corruption).
Unlike MR-13 (near-breakeven, thousands of trades) or MR-20/MR-08 (broader
clusters, thousands of trades), MR-15's positive region is both narrow (6
cells) and thin on trades (as low as 218 full-history, 35 in the worst OOS
window) — the strongest apparent in-sample signal in the category, but also
the least statistically robust due to low trade counts.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `demarker_period` | Longer period much less bad (avg Sharpe −0.85 at 20 vs −7.00 at 5) — dominant driver |
| `tf_min` | 15-min much better than 5-min (avg −1.36 vs −4.84) |
| `atr_stop_mult` | Wider stop less bad (avg −2.40 at 1.5× vs −3.76 at 0.75×) |
| `oversold_thresh` / `overbought_thresh` | More extreme (0.05/0.95) less bad than looser (0.20/0.80) — avg −2.55 vs −3.66 |

---

## Recommendation

**Do not implement MR-15 standalone — trade counts are too thin to trust,
despite the best in-sample walk-forward Sharpe in the category.** If
pursued further, the priority would be extending the setup to more
instruments/timeframes to build up trade count before drawing conclusions,
since the current 5-min/15-min EURUSD-only sample size (as low as 35–218
trades in the interesting region) is below what's needed for confident
OOS validation.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 384 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
