# RESULTS — MR-12 Pivot Point Reversion

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr12_pivot_point` |
| Strategy | Pivot Point Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-12` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 4.9 s end-to-end |
| Run date | 2026-07-02 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `pivot_period` | daily, weekly (2 values) |
| `fade_level` | S1/R1, S2/R2 (2 values) |
| `touch_atr_thresh` | 0.25, 0.5, 0.75, 1.0 (4 values) |
| `target` | P, mid_SR1_P (2 values) |
| `atr_stop_mult` | 0.5, 1.0, 1.5 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **192** (96 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `pivot_period` | weekly |
| `fade_level` | S2/R2 |
| `touch_atr_thresh` | 0.25 |
| `target` | mid_SR1_P |
| `atr_stop_mult` | 1.5 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.0128** |
| Profit Factor | 0.9962 |
| Max Drawdown (R, absolute) | 170.05 |
| Total Return (R) | −5.87 |
| Number of Trades | 1,917 |

> Second-closest full-history result to breakeven found in
> `cat02_mean_reversion`, after MR-13's −0.012. The top-10 combinations are
> all `weekly`/`S2/R2` variants — a real, consistent cluster.

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | weekly S2/R2 touch0.25 mid_SR1_P stop1.5x 15m | −0.108 | −0.119 | 0.967 | 406 |
| 2 | 2003–2016 | 2017–2020 | weekly S2/R2 touch0.25 P stop1.5x 15m | −0.226 | −0.063 | 0.981 | 340 |
| 3 | 2003–2018 | 2019–2022 | weekly S2/R2 touch0.25 P stop1.5x 15m | −0.122 | −0.721 | 0.798 | 321 |
| 4 | 2003–2020 | 2021–2025 | weekly S2/R2 touch0.25 mid_SR1_P stop1.5x 15m | −0.168 | **+0.559** | 1.197 | 362 |

Window 4 (2021–2025 OOS) is positive — the only OOS-positive walk-forward
window found across the fully-run strategies in this category besides
MR-16's window 3.

---

## Key Finding

**No edge found, but the closest thing to a stable near-breakeven signal
after MR-13.** 0 / 192 combinations have positive Sharpe or PF > 1.0. Best
Sharpe −0.013. Worst: −4.49 (daily pivots, S1/R1, loose 1.0 touch threshold,
`mid_SR1_P` target, tight 0.5× stop, 5-min — 57,974 trades, sanity-checked
clean at −0.27R/trade). Unlike MR-08/MR-20/MR-19 (broad or narrow positive
clusters that fail OOS), MR-12's grid is uniformly slightly negative but the
IS-selected configuration is consistent across windows and one OOS window
(2021–2025) is genuinely positive with a respectable trade count (362) — a
different failure mode than the rest of the category (consistently
near-breakeven rather than a strong-but-overfit cluster).

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `pivot_period` | Weekly much better than daily (avg Sharpe −0.87 vs −1.87) — weekly levels persist longer and are more institutionally relevant |
| `fade_level` | Extended `S2/R2` better than `S1/R1` (avg −1.05 vs −1.69) |
| `atr_stop_mult` | Wider stop much better (avg −0.83 at 1.5× vs −2.13 at 0.5×) |
| `target` | `P` (full pivot) better than `mid_SR1_P` (avg −1.19 vs −1.55) |
| `tf_min` | 15-min better than 5-min (avg −1.08 vs −1.66) |
| `touch_atr_thresh` | Weak effect; tighter (0.25) marginally best (avg −1.30 vs −1.46 at 1.0) |

---

## Recommendation

**Do not implement MR-12 standalone, but it's a reasonable secondary
follow-up alongside MR-13.** The consistent weekly/S2-R2/wide-stop signature
and the genuinely positive final OOS window are mildly encouraging, though
weaker evidence than MR-08/MR-19/MR-20's larger positive clusters. If
pursued, priority would be testing whether the 2021–2025 OOS-positive
result persists with more recent out-of-sample data, or whether it's a
one-off regime effect.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 192 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
