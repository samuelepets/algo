# RESULTS — MR-18 High-Low Channel Fade

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr18_hl_channel_fade` |
| Strategy | High-Low Channel Fade |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-18` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 6.5 s end-to-end |
| Run date | 2026-07-02 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `range_period` | 20, 30, 50, 100 (4 values) |
| `entry_pct` | 0.80, 0.85, 0.90, 0.95 (4 values) |
| `atr_range_ratio` | 0.20, 0.30, 0.40 (3 values) |
| `target` | center, opposite_side (2 values) |
| `atr_stop_mult` | 0.5, 1.0 (2 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **384** (192 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `range_period` | 100 |
| `entry_pct` | 0.95 |
| `atr_range_ratio` | 0.20 |
| `target` | opposite_side |
| `atr_stop_mult` | 0.5 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.2460** |
| Profit Factor | 0.9628 |
| Max Drawdown (R, absolute) | 859.13 |
| Total Return (R) | −647.31 |
| Number of Trades | 15,928 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | rp100 pct0.95 ratio0.30 opposite_side stop1.0x 15m | +0.189 | −1.440 | 0.827 | 2,234 |
| 2 | 2003–2016 | 2017–2020 | rp30 pct0.95 ratio0.30 opposite_side stop1.0x 15m | +0.060 | −1.598 | 0.863 | 3,396 |
| 3 | 2003–2018 | 2019–2022 | rp30 pct0.95 ratio0.30 opposite_side stop1.0x 15m | −0.204 | −0.456 | 0.959 | 3,374 |
| 4 | 2003–2020 | 2021–2025 | rp30 pct0.95 ratio0.30 opposite_side stop1.0x 15m | −0.333 | −0.454 | 0.957 | 4,328 |

Windows 1–2 have mildly positive IS Sharpe, but every OOS window is
negative.

---

## Key Finding

**No edge found.** 0 / 384 combinations have positive Sharpe or PF > 1.0.
Best Sharpe −0.246. Worst: −9.84 (short 20-bar range, loose 0.80 entry,
loose 0.40 ATR/range ratio filter, tight 0.5× stop, 5-min — 156,851 trades,
PF 0.75, sanity-checked clean at −0.27R/trade). The range-confirmation
filter and edge-fade premise have some signal (longer ranges, tighter entry
near the true edge, and opposite-side targeting all help), but not enough
to overcome transaction costs.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `target` | `opposite_side` beats `center` (avg Sharpe −1.91 vs −3.00) — the fuller retrace captures more when it works |
| `range_period` | Longer range less bad (avg −1.25 at 100 vs −3.15 at 20) — a longer-established range is a more meaningful level |
| `entry_pct` | Closer to the true edge (0.95) less bad (avg −1.88 vs −2.97 at 0.80) — fading only the extremes, not the general vicinity |
| `atr_range_ratio` | Tighter range-confirmation filter less bad (avg −1.98 at 0.20 vs −2.78 at 0.40) |
| `tf_min` | 15-min much better than 5-min (avg −1.33 vs −3.57) |
| `atr_stop_mult` | Wider stop less bad (avg −1.94 at 1.0× vs −2.96 at 0.5×) |

---

## Recommendation

**Do not implement MR-18 standalone.** All the directional insights point
the same way — longer, more established ranges; tighter edge-only entries;
tighter range-confirmation filters — but even at the best corner of the
grid, Sharpe stays negative. The general shape (tighter filters and more
selective entries hurt least) is consistent with the rest of this category.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 384 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
