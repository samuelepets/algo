# RESULTS — MR-19 Connors RSI (3-Component) Reversion

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr19_connors_rsi` |
| Strategy | Connors RSI (3-Component) Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-19` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 32–34 s end-to-end |
| Run date | 2026-07-02 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `rsi_period` | 2, 3, 4 (3 values) |
| `ud_rsi_period` | 2, 3 (2 values) |
| `roc_rank_period` | 50, 100, 200 (3 values) |
| `oversold_thresh` | 5, 10, 15, 20 (4 values) |
| `overbought_thresh` | 95, 90, 85, 80 (4 values) |
| `exit_level` | 50, 55, 60 (3 values) |
| `trend_sma` | none, 100, 200 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **5,184** (2,592 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |
| ATR stop | **fixed** 1.5× ATR(14) — not a grid dimension (see README) |

---

## Best Combination (full history, min-trades filtered, by robustness)

| Parameter | Value |
|---|---|
| `rsi_period` | 3 |
| `ud_rsi_period` | 2 |
| `roc_rank_period` | 200 |
| `oversold_thresh` | 10 |
| `overbought_thresh` | 95 |
| `exit_level` | 60 |
| `trend_sma` | 100 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **+0.3803** |
| Profit Factor | 1.1315 |
| Max Drawdown (R, absolute) | 33.55 |
| Total Return (R) | 63.69 |
| Number of Trades | 2,102 |

> Picked as "best" over higher-PF alternatives specifically because it has a
> robust trade count (2,102) rather than the 81–589-trade family discussed
> below. The next 3 rows by Sharpe are close variants of the same family
> (`rsi3/ud2/roc200` or `roc100`, `os10`), all with 2,000+ trades — a real,
> broad cluster, not an isolated cell.

### The thin, high-PF family (flagged, not recommended as "best")

Combinations with `trend_sma=none` and tight thresholds (`os5/ob95`) show
much higher headline numbers but far fewer trades:

| rsi | ud | roc | trend | tf | Sharpe | PF | avg R/trade | n_trades |
|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 100 | none | 15m | 0.285 | 9.45 | 3.36 | 574 |
| 4 | 3 | 50 | none | 15m | 0.284 | 8.80 | 2.80 | 589 |
| 4 | 3 | 100 | none | 5m | 0.209 | 39.6 | 12.57 | 97 |

Verified this is **not** the ATR-floor numerical artifact seen in
mr14/mr20 (re-running with `ATR_FLOOR` at `1e-6` vs `1e-5` produced
byte-identical results for these rows) — it reflects a real but thin sample
where the no-trend-filter, tight-threshold setup occasionally rides a large
move for close to the full 50-bar hold before exiting. With under 600 trades
over 23 years, a handful of large winners can dominate the aggregate stats.
Not used as the headline "best combination" for this reason.

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | rsi4/ud2/roc200 os15/ob90 x60 trend100 15m | **+1.425** | −0.316 | 0.944 | 823 |
| 2 | 2003–2016 | 2017–2020 | rsi4/ud2/roc200 os15/ob85 x55 trend100 15m | +1.195 | −0.690 | 0.905 | 1,398 |
| 3 | 2003–2018 | 2019–2022 | rsi4/ud2/roc200 os15/ob90 x60 trend100 15m | +0.961 | −0.207 | 0.965 | 876 |
| 4 | 2003–2020 | 2021–2025 | rsi4/ud2/roc200 os15/ob90 x60 trend100 15m | +0.897 | −0.571 | 0.792 | 1,093 |

IS Sharpe (+0.90 to +1.42) is the strongest and most consistent seen across
all 20 mean-reversion strategies documented so far — yet every OOS window is
negative, and OOS trade counts are robust (823–1,398), ruling out a
small-sample explanation for the OOS failure itself.

---

## Key Finding

**The broadest full-history positive cluster in this category (42% of the
grid), combined with the strongest IS walk-forward Sharpe seen — and yet
the sharpest IS/OOS divergence.** This is a stronger signal of overfitting
than under-sampling: the IS-selected configuration is consistently strong
on growing in-sample windows (Sharpe rising from +0.90 to +1.42 as more data
accumulates) but fails to generalise to any of the 4 OOS windows, with
robust (800–1,400) trade counts on both sides ruling out noise as the sole
explanation. Compare to MR-15/MR-13 where OOS failure occurs on thin trade
counts — here the failure is well-sampled on both IS and OOS, making the
overfitting interpretation more credible than for those strategies.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `tf_min` | 15-min much better than 5-min (avg Sharpe −0.14 vs −1.72) |
| `trend_sma` | A trend filter clearly helps (avg −0.70 at 100, −0.67 at 200, vs −1.39 with none) — note this contradicts the thin high-PF family above, which uses `none`; the filter helps the *average* case but the tail-heavy family is an exception |
| `rsi_period` | Longer less bad (avg −0.29 at 4 vs −1.69 at 2) |
| `ud_rsi_period` | `3` beats `2` (avg −0.40 vs −1.46) |
| `overbought_thresh` | More extreme (95) better than looser (80) — avg −0.58 vs −1.64 |
| `oversold_thresh` | More extreme (5) better than looser (20) — avg −0.45 vs −1.65 |
| `roc_rank_period` | `100` best on average (avg −0.64) vs `200` (−1.12) or `50` (−1.03) |

---

## Recommendation

**Do not implement MR-19 standalone, but flag it as the highest-priority
follow-up candidate in the entire category.** The combination of a broad,
robustly-sampled full-history cluster and a strong, consistent IS Sharpe is
unusual — most other strategies here fail broadly (no cluster at all) or
show a narrow/thin cluster. The clean IS/OOS split (both well-sampled, both
consistent in direction) makes this the best candidate for deeper
walk-forward-robustness work: e.g., requiring the SAME configuration to be
top-ranked across multiple overlapping IS windows before ever trading it
live, or testing on additional instruments (XAUUSD) to see if the pattern
generalises beyond EURUSD.

| Priority | Next step | Rationale |
|---|---|---|
| 1 | Test `rsi4/ud2/roc200 os15/ob90 x60 trend100 15m` on XAUUSD | Cross-instrument validation would meaningfully strengthen or weaken the "real edge, badly overfit window selection" hypothesis |
| 2 | Investigate why IS Sharpe rises monotonically with window length (0.90→1.42) | May indicate the edge is time-varying/decaying, not stationary |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 5,184 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
