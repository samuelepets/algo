# RESULTS — MR-05 Stochastic %K/%D Reversion

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr05_stochastic_reversion` |
| Strategy | Stochastic %K/%D Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-05` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 16 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `k_period` | 5, 9, 14, 21 (4 values) |
| `d_period` | 3, 5 (2 values) |
| `slowing` | 1, 3 (2 values) |
| `oversold_thresh` / `overbought_thresh` | 15/85, 20/80, 25/75 (3 pairs) |
| `atr_stop_mult` | 0.75, 1.0, 1.5 (3 values) |
| `max_hold_bars` | 5, 10, 15, 20 (4 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **3,456** (1,728 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `k_period` | 21 |
| `d_period` | 3 |
| `slowing` | 3 |
| `oversold_thresh` / `overbought_thresh` | 15 / 85 |
| `atr_stop_mult` | 1.5 |
| `max_hold_bars` | 20 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−2.1297** |
| Profit Factor | 0.8607 |
| Max Drawdown (R, absolute) | 1,778.09 |
| Total Return (R) | −1,757.79 |
| Number of Trades | 25,591 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

The same configuration (`k21/d3/s3`, 15m, `atr_stop=1.5x`) was selected in
every window (oversold threshold varied 15/20).

| Window | IS | OOS | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | −1.475 | −2.932 | 0.837 | 5,701 |
| 2 | 2003–2016 | 2017–2020 | −1.653 | −3.080 | 0.823 | 5,209 |
| 3 | 2003–2018 | 2019–2022 | −1.922 | −2.731 | 0.850 | 5,918 |
| 4 | 2003–2020 | 2021–2025 | −2.032 | −2.457 | 0.857 | 6,839 |

IS Sharpe is already strongly negative in every window (best −1.475); OOS is
consistently worse.

---

## Key Finding

**No edge found.** 0 / 3,456 combinations have positive Sharpe or PF > 1.0.
Best Sharpe: −2.13 (k21/d3/slow3, 15-min). Worst: −29.76 (k5, 5-min, tight
0.75× stop, 5-bar hold — 345,972 trades, fully cost-dominated). The
crossover-inside-extreme-zone trigger fires very frequently on short
lookbacks, generating overtrading; even the best (longest lookback, slowest
smoothing) combination cannot overcome transaction costs at this frequency.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min much less bad than 5-min (avg Sharpe −4.60 vs −15.04) |
| `k_period` | Longer lookback less bad (avg −7.80 at 21 vs −12.58 at 5) |
| `slowing` | `slowing=3` (slow stochastic) less bad than `slowing=1` (avg −8.42 vs −11.21) |
| `atr_stop_mult` | Wider stops less bad (avg −8.02 at 1.5× vs −11.60 at 0.75×) |
| `d_period` | Weak effect (avg −9.67 at 5 vs −9.97 at 3) |

---

## Recommendation

**Do not implement MR-05 standalone.** Even the least-bad corner of the grid
(longest %K lookback, slowest smoothing, widest stop, 15-min) stays deeply
Sharpe-negative — this is not a borderline case like MR-01, it is a
comprehensively failing signal at this cost model. A crossover-based trigger
without a regime/trend filter overtrades badly on EURUSD intraday data.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 3,456 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
