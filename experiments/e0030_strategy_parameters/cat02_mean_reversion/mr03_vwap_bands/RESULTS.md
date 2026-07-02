# RESULTS — MR-03 VWAP Standard Deviation Bands

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr03_vwap_bands` |
| Strategy | VWAP Standard Deviation Bands |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-03` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → 1-min (native) and 5-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 11.2 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `vwap_reset` | daily, session_london, session_ny (3 values) |
| `entry_sigma` | 1.0, 1.5, 2.0, 2.5, 3.0 (5 values) |
| `exit_sigma` | 0.0, 0.5, 1.0 (3 values) |
| `atr_stop_mult` | 0.5, 1.0, 1.5 (3 values) |
| `tf_min` | 1, 5 (2 values) |
| **Total combinations** | **270** (135 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `vwap_reset` | session_ny |
| `entry_sigma` | 3.0 |
| `exit_sigma` | 0.0 |
| `atr_stop_mult` | 1.5 |
| `tf_min` | 5 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−1.2770** |
| Profit Factor | 0.8454 |
| Max Drawdown (R, absolute) | 7,293.53 |
| Total Return (R) | −6,648.21 |
| Number of Trades | 47,766 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. The same configuration
(`session_ny e3.0s x0.0s stop1.5x 5m`) was selected in all 4 windows.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | session_ny e3.0s x0.0s stop1.5x 5m | −1.170 | −3.939 | 0.7484 | 8,917 |
| 2 | 2003–2016 | 2017–2020 | session_ny e3.0s x0.0s stop1.5x 5m | −1.348 | −3.054 | 0.7692 | 8,710 |
| 3 | 2003–2018 | 2019–2022 | session_ny e3.0s x0.0s stop1.5x 5m | −1.644 | −1.512 | 0.8564 | 8,304 |
| 4 | 2003–2020 | 2021–2025 | session_ny e3.0s x0.0s stop1.5x 5m | −1.662 | −0.594 | 0.9023 | 10,385 |

All 4 OOS windows are negative — no window produced positive out-of-sample
Sharpe, and the IS-selected configuration was already negative in-sample in
every window (best IS Sharpe −1.170).

---

## Key Finding

**No edge found.** Of the 270 combinations, all 270 clear the `≥ 50` trades
filter:

- 0 / 270 with Sharpe > 0
- 0 / 270 with Profit Factor > 1.0
- Best Sharpe: −1.2770 (5-min, session_ny reset, wide 3.0σ entry, VWAP-line
  exit, 1.5× stop)
- Worst Sharpe: −67.98 (1-min, daily reset, tight 1.0σ entry/1.0σ exit,
  0.5× stop — 370,525 trades, fully spread-dominated)

No combination shows positive Sharpe/PF anywhere in the grid, unlike MR-01
where a handful of below-threshold outliers were positive. Fading VWAP
deviation bands has no exploitable edge on EURUSD across the full 23-year
history, at either timeframe tested.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 5-min clearly outperforms 1-min (mean Sharpe −9.95 vs −24.04) — 1-min running-std bands are noisy and spread-dominated |
| `entry_sigma` | Wider bands are markedly less bad (mean −30.45 at 1.0σ → −6.70 at 3.0σ) — fading shallow VWAP deviations overtrades badly |
| `vwap_reset` | `session_ny` slightly best (mean −15.30), then `session_london` (−16.62), then `daily` (−19.06) — narrower NY-afternoon sessions build cleaner bands than the full trading day |
| `exit_sigma` | Exiting exactly at VWAP (`0.0`) beats partial-retracement exits (mean −14.63 vs −19.86 at `1.0`) — waiting for a deeper reversion pays off when it works, though not enough to flip the sign |
| `atr_stop_mult` | Wider stops reduce loss (mean −19.63 at 0.5× → −14.21 at 1.5×) |

Direction of "least bad": 5-min, `session_ny` reset, wide entry (3.0σ),
VWAP-line exit, wide ATR stop (1.5×). Even at these settings expectancy
stays clearly negative — same pattern as MR-01: the search narrows the
loss, it does not flip it positive.

---

## Recommendation

**Do not implement MR-03 standalone.**

Session-anchored VWAP band fading, across daily/London/NY resets and both
sub-hourly timeframes tested, is net-losing on EURUSD across the full grid
and every walk-forward window. The running (expanding) population std used
for the bands means the bands are extremely tight early in each session —
tight bands overtrade at 1-min and even at 5-min the strategy never clears
the round-trip spread cost by a meaningful margin.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | MR-04 Z-Score Reversion | Fixed-window statistics instead of an expanding intra-session std that starts at zero |
| 2 | MR-13 Money Flow Index Extremes | Volume-weighted oscillator signal, structurally different from a price-distance band |
| 3 | MR-09 EMA Rubber Band | Simple distance-based signal for comparison against both MR-01's and MR-03's band-touch triggers |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 270 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
