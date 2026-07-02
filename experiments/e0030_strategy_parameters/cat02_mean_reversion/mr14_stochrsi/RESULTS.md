# RESULTS — MR-14 Stochastic RSI Reversion

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr14_stochrsi` |
| Strategy | Stochastic RSI Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-14` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 5.3 s end-to-end |
| Run date | 2026-07-02 (re-run after ATR-floor numerical fix — see README) |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `rsi_period` | 10, 14 (2 values) |
| `stoch_period` | 10, 14 (2 values) |
| `smooth_k` | 3, 5 (2 values) |
| `smooth_d` | 3 (fixed) |
| `oversold_thresh` | 0.05, 0.10, 0.15, 0.20 (4 values) |
| `overbought_thresh` | 0.95, 0.90, 0.85, 0.80 (4 values) |
| `atr_stop_mult` | 0.75, 1.0, 1.5 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **768** (384 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `rsi_period` | 10 |
| `stoch_period` | 14 |
| `smooth_k` | 5 |
| `oversold_thresh` | 0.05 |
| `overbought_thresh` | 0.95 |
| `atr_stop_mult` | 1.5 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.6332** |
| Profit Factor | 0.9448 |
| Max Drawdown (R, absolute) | 471.50 |
| Total Return (R) | −417.69 |
| Number of Trades | 16,536 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

The same configuration (`rsi10/stoch14/k5`, `os0.05/ob0.95`, `stop1.5×`,
15-min) was selected in every window.

| Window | IS | OOS | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | +0.028 | −0.614 | 0.946 | 2,969 |
| 2 | 2003–2016 | 2017–2020 | +0.043 | −1.769 | 0.850 | 2,961 |
| 3 | 2003–2018 | 2019–2022 | −0.150 | −1.391 | 0.881 | 2,972 |
| 4 | 2003–2020 | 2021–2025 | −0.409 | −1.368 | 0.888 | 3,807 |

IS Sharpe hovers near zero and turns negative in later windows; OOS is
negative in all 4.

---

## Key Finding

**No edge found (after fixing a numerical-stability bug).** 0 / 768
combinations have positive Sharpe or PF > 1.0. An initial (buggy) run showed
a top-10 cluster with Sharpe up to +0.169 and PF up to 1.31 — but this was
an artifact of Wilder ATR decaying to near machine-epsilon during flat-price
data stretches, combined with StochRSI's scale-invariance letting it still
fire "extreme" signals on sub-pip noise during those same stretches (a
near-zero-risk stop then turns a routine subsequent price move into a
massive R-multiple outlier). Adding a realistic `ATR < 1e-6` floor (matching
`mr09_ema_distance`'s existing `ATR_FLOOR` guard) eliminated the spurious
cluster entirely — see README.md's "Numerical stability fix" section.
Post-fix, the best full-history Sharpe is a comprehensively negative −0.633.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `tf_min` | 15-min much better than 5-min (avg Sharpe −2.41 vs −8.45) |
| `atr_stop_mult` | Wider stop less bad (avg −4.27 at 1.5× vs −6.49 at 0.75×) |
| `oversold_thresh` / `overbought_thresh` | More extreme (0.05/0.95) less bad than looser (0.20/0.80) — avg −4.74 vs −5.97 |
| `smooth_k` | `smooth_k=5` less bad than `smooth_k=3` (avg −4.71 vs −6.15) |
| `stoch_period` | `14` less bad than `10` (avg −5.03 vs −5.83) |
| `rsi_period` | Weak effect (avg −5.40 at 14 vs −5.46 at 10) |

---

## Recommendation

**Do not implement MR-14 standalone.** Comprehensively negative across the
full grid once the numerical artifact is removed — consistent with MR-05
(plain Stochastic), suggesting oscillator-crossover triggers without a
regime filter don't hold up on EURUSD intraday data regardless of the exact
oscillator construction.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 768 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
