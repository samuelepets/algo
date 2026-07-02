# RESULTS — MR-11 Double Bollinger Band System

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr11_double_bollinger` |
| Strategy | Double Bollinger Band System |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-11` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 3.4 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `bb_period` | 14, 20, 30 (3 values) |
| `outer_sigma` | 1.5, 2.0, 2.5 (3 values) |
| `target` | inner_band, center_sma (2 values) |
| `adx_filter` | none, <20, <25 (3 values) |
| `atr_stop_mult` | 0.5, 1.0, 1.5 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **324** (162 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |
| Inner band | fixed 1.0σ (not grid-searched) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `bb_period` | 30 |
| `outer_sigma` | 2.5 |
| `target` | center_sma |
| `adx_filter` | <20 |
| `atr_stop_mult` | 1.5 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.2731** |
| Profit Factor | 0.9654 |
| Max Drawdown (R, absolute) | 142.37 |
| Total Return (R) | −134.08 |
| Number of Trades | 6,350 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | bb20/2.5σ center_sma no_adx stop1.5x 15m | −0.254 | −0.291 | 0.977 | 3,021 |
| 2 | 2003–2016 | 2017–2020 | bb20/2.5σ center_sma adx<25 stop1.5x 15m | −0.172 | −0.559 | 0.945 | 1,870 |
| 3 | 2003–2018 | 2019–2022 | bb30/2.5σ center_sma adx<20 stop1.5x 15m | −0.170 | −0.311 | 0.960 | 1,063 |
| 4 | 2003–2020 | 2021–2025 | bb30/2.5σ center_sma adx<20 stop1.5x 15m | −0.240 | −0.390 | 0.951 | 1,366 |

Windows 3 and 4 select essentially the full-history-best configuration, and
IS Sharpe is close to the full-history value (~−0.2) throughout — consistent
selection, still net-losing.

---

## Key Finding

**No edge found.** 0 / 324 combinations have positive Sharpe or PF > 1.0.
Best Sharpe: −0.273 (bb30, wide outer band, center-SMA target, 15-min).
Worst: −19.06 (bb14, narrow 1.5σ outer band, inner-band target, 5-min,
tight 0.5× stop — 259,541 trades). Unlike MR-08, this strategy's
walk-forward selection is *consistent* with the full-history best (windows
3–4 pick the exact same combo), which rules out the "full-sample artifact"
explanation seen in MR-08 — the double-band structure is just consistently,
mildly unprofitable after costs.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `outer_sigma` | Wider outer band less bad (avg −2.15 at 2.5σ vs −5.92 at 1.5σ) |
| `target` | `center_sma` beats `inner_band` (avg −3.38 vs −4.57) — the inner band adds path risk without benefit |
| `tf_min` | 15-min much better than 5-min (avg −2.00 vs −5.95) |
| `bb_period` | Longer period slightly better (avg −3.59 at 30 vs −4.32 at 14) |
| `adx_filter` | Weak effect; `<20` marginally best (avg −3.53) vs no filter (−4.40) |

---

## Recommendation

**Do not implement MR-11 standalone.** The extra inner-band structure over
plain MR-01 Bollinger fading does not add edge — the best full-history and
walk-forward-consistent configuration (wide outer band, center-SMA target,
15-min) still lands at Sharpe ≈ −0.2 to −0.3, in the same range as MR-01's
best (−0.15). The added complexity is not justified versus the simpler MR-01
baseline.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 324 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
