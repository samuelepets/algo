# RESULTS — MR-17 EMA Touch Return

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr17_ema_touch_return` |
| Strategy | EMA Touch Return |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-17` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 3.3 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `ema_period` | 10, 20, 50 (3 values) |
| `distance_thresh_atr` | 0.5, 1.0, 1.5, 2.0 (4 values) |
| `adx_max` | 15, 20, 25 (3 values) |
| `atr_stop_mult` | 0.5, 1.0, 1.5 (3 values) |
| `exit_type` | ema_touch, half_distance (2 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **432** (216 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `ema_period` | 10 |
| `distance_thresh_atr` | 2.0 |
| `adx_max` | 15 |
| `atr_stop_mult` | 1.0 |
| `exit_type` | ema_touch |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.2095** |
| Profit Factor | 0.7853 |
| Max Drawdown (R, absolute) | 13.17 |
| Total Return (R) | −10.97 |
| Number of Trades | 80 |

> Only 80 trades over 23 years — near the `≥ 50` floor. The tight ADX gate
> (`<15`) combined with a wide 2.0-ATR distance requirement makes this a very
> rare setup; treat this "best" result as low-confidence.

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | ema50 dist2.0 adx<20 stop1.5x ema_touch 15m | −0.003 | −0.323 | 0.960 | 1,122 |
| 2 | 2003–2016 | 2017–2020 | ema50 dist2.0 adx<20 stop1.5x half_distance 15m | −0.030 | −1.795 | 0.794 | 1,111 |
| 3 | 2003–2018 | 2019–2022 | ema10 dist2.0 adx<15 stop1.0x ema_touch 15m | **+0.036** | −0.653 | 0.568 | 24 |
| 4 | 2003–2020 | 2021–2025 | ema10 dist2.0 adx<15 stop1.5x half_distance 15m | −0.073 | −0.841 | 0.348 | 14 |

Window 3's IS Sharpe is mildly positive but on only 52 IS trades, and its
OOS window collapses to 24 trades — not statistically meaningful either way.

---

## Key Finding

**No edge found (and mostly untestable at scale).** 0 / 432 combinations
have positive Sharpe or PF > 1.0. The strategy's own design — requiring both
a tight ADX regime gate AND a wide ATR-distance extension AND a one-bar
reversal confirmation — is intrinsically low-frequency, so even the
"best" cells sit near the 50-trade statistical floor. Wider distance
thresholds and tighter ADX gates both reduce (but don't eliminate) the
negative Sharpe, consistent with "fewer, more selective signals are less
bad" — the same direction as every other strategy in this category, but
here it also means there isn't enough data to validate the tail combinations
with confidence.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `distance_thresh_atr` | Much less bad at wider thresholds (avg −2.18 at 2.0 ATR vs −9.93 at 0.5 ATR) |
| `adx_max` | Tighter regime gate less bad (avg −3.73 at 15 vs −7.10 at 25) |
| `tf_min` | 15-min much better than 5-min (avg −2.65 vs −8.45) |
| `exit_type` | `ema_touch` slightly better than `half_distance` (avg −5.24 vs −5.86) |
| `ema_period` | Weak effect, shorter slightly better (avg −5.18 at 10 vs −5.89 at 50) |

---

## Recommendation

**Do not implement MR-17 standalone.** No configuration reaches positive
Sharpe with a meaningful trade count, and the strategy's selectivity means
robust conclusions would need either a longer history or a looser trigger
(which the grid shows makes things worse, not better).

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 432 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
