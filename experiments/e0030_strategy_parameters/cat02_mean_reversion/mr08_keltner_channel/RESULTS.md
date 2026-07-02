# RESULTS — MR-08 Keltner Channel Reversion

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr08_keltner_channel` |
| Strategy | Keltner Channel Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-08` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 3.1 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `ema_period` | 10, 20, 30 (3 values) |
| `atr_period` | 10, 14 (2 values) |
| `k_mult` | 1.0, 1.5, 2.0, 2.5, 3.0 (5 values) |
| `entry_type` | close_outside, wick_touch (2 values) |
| `atr_stop_mult` | 0.5, 1.0, 1.5 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **360** (180 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `ema_period` | 30 |
| `atr_period` | 10 |
| `k_mult` | 2.5 |
| `entry_type` | close_outside |
| `atr_stop_mult` | 1.5 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **+0.2011** |
| Profit Factor | 2.1176 |
| Max Drawdown (R, absolute) | 592.27 |
| Total Return (R) | 10,803.25 |
| Number of Trades | 15,697 |

> This is the first positive full-history Sharpe/PF>1 combination found in
> `cat02_mean_reversion` so far. Note the top-10 combinations by Sharpe are
> all clustered at `ema_period=30, atr_period=10, tf_min=15`, varying only
> `k_mult` (2.0–3.0) and `atr_stop_mult` — a real, non-isolated cluster, not
> a single lucky cell. See "Key Finding" below for why this does not survive
> walk-forward.

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | ema30/atr10 k2.0x close_outside stop1.5x 5m | −0.273 | −2.866 | 0.904 | 14,716 |
| 2 | 2003–2016 | 2017–2020 | ema30/atr10 k3.0x close_outside stop1.5x 5m | −0.308 | −1.593 | 0.915 | 5,873 |
| 3 | 2003–2018 | 2019–2022 | ema10/atr10 k3.0x close_outside stop0.5x 5m | −0.347 | −0.420 | 0.919 | 600 |
| 4 | 2003–2020 | 2021–2025 | ema10/atr10 k3.0x close_outside stop0.5x 5m | −0.400 | −0.568 | 0.889 | 804 |

Note IS-only selection consistently picks **5-min** and (in later windows)
**short EMA(10)** — the opposite corner of the grid from the full-history
best (15-min, EMA(30)). IS Sharpe is negative from window 1 onward, and OOS
is negative in all 4 windows.

---

## Key Finding

**Weak full-history signal, does not survive walk-forward — likely a
full-sample artifact, not a genuine tradable edge.**

- 41 / 360 combinations (11%) have Sharpe > 0 and PF > 1.0 — a real cluster,
  not noise from a handful of low-trade-count outliers (all 41 have
  thousands of trades).
- The cluster is narrow and specific: 15-min, EMA(30), ATR(10), wide
  `k_mult` (2.0–3.0), `close_outside` entry. Best Sharpe +0.20, PF 2.12–3.26.
- Walk-forward IS-only optimisation never selects this cluster: with less
  data (any window ending before 2025), the grid search prefers 5-min /
  short EMA(10) instead, and that selection is IS-negative from the start.
- This mismatch (full-sample winner ≠ any-subsample winner) is the classic
  signature of overfitting to a small number of favourable regimes/years
  rather than a stable, exploitable statistical edge.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `ema_period` | Longer center line much better (avg Sharpe −0.44 at 30 vs −3.54 at 10) |
| `k_mult` | Wider bands better (avg −1.02 at 3.0 vs −4.29 at 1.0) — fewer, more extreme entries |
| `tf_min` | 15-min better than 5-min (avg −1.49 vs −2.96) |
| `entry_type` | `close_outside` slightly better than `wick_touch` (avg −1.59 vs −2.87) |
| `atr_stop_mult` | Wider stops better (avg −1.46 at 1.5× vs −3.28 at 0.5×) |

---

## Recommendation

**Do not implement MR-08 standalone, but flag for follow-up.** This is the
first strategy in the category with a real full-history positive cluster —
worth a closer look with a proper walk-forward-robust selection procedure
(e.g., requiring parameter stability across windows, or a coarser grid
around the EMA(30)/wide-k region specifically) before dismissing it outright.
As implemented, it fails the walk-forward bar the same way MR-01/MR-05/MR-11
do.

| Priority | Next step | Rationale |
|---|---|---|
| 1 | Re-run walk-forward restricted to `ema_period ∈ {20,30}`, `k_mult ∈ {2.0,2.5,3.0}` | Narrow the IS search space around the full-history-stable region instead of the full grid, to see if OOS turns positive |
| 2 | Add an ADX/regime filter | Not in the current grid; MR-01's ADX filter didn't help much, but MR-08's wider bands may interact differently |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 360 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
