# RESULTS — MR-16 Opening Range Mean Reversion

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr16_opening_range_reversion` |
| Strategy | Opening Range Mean Reversion (failed-breakout fade) |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-16` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 1-min and 5-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 8.8 s end-to-end |
| Run date | 2026-07-02 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `or_duration_min` | 5, 10, 15, 30 (4 values) |
| `reversal_bars` | 1, 2, 3 (3 values) |
| `target` | mid_range, opposite_band (2 values) |
| `atr_stop_mult` | 0.5, 1.0, 1.5 (3 values) |
| `session` | london, ny (2 values) |
| `tf_min` | 1, 5 (2 values) |
| **Total combinations** | **288** (144 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `or_duration_min` | 15 |
| `reversal_bars` | 1 |
| `target` | opposite_band |
| `atr_stop_mult` | 1.0 |
| `session` | ny |
| `tf_min` | 5 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.3675** |
| Profit Factor | 0.9113 |
| Max Drawdown (R, absolute) | 71.72 |
| Total Return (R) | −65.57 |
| Number of Trades | 1,779 |

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | or30m rev1 opposite_band stop1.5x london 5m | −0.173 | −1.533 | 0.661 | 262 |
| 2 | 2003–2016 | 2017–2020 | or5m rev1 opposite_band stop1.5x ny 1m | −0.327 | −1.936 | 0.618 | 320 |
| 3 | 2003–2018 | 2019–2022 | or15m rev1 opposite_band stop1.0x ny 5m | −0.398 | **+0.244** | 1.065 | 305 |
| 4 | 2003–2020 | 2021–2025 | or15m rev1 opposite_band stop1.0x ny 5m | −0.320 | −0.540 | 0.870 | 385 |

Selection is unstable across windows (session and OR duration both change);
only window 3 is OOS-positive.

---

## Key Finding

**No edge found.** 0 / 288 combinations have positive Sharpe or PF > 1.0.
Best Sharpe −0.368. Worst: −5.89 (5-min OR, 3-bar reversal wait, mid_range
target, tight 0.5× stop, London session, 1-min TF — 3,028 trades, PF 0.25).
The failed-breakout premise has some signal (NY session and fast 1-bar
reversal confirmation both help materially) but not enough to overcome
transaction costs at any grid point.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `session` | NY clearly better than London (avg Sharpe −1.58 vs −2.64) — consistent with NY being the dominant EURUSD session |
| `target` | `opposite_band` beats `mid_range` (avg −1.55 vs −2.67) — the full retrace target captures more of the move when it works |
| `or_duration_min` | Longer opening range less bad (avg −1.52 at 30min vs −2.81 at 5min) — a longer range is a more meaningful level |
| `reversal_bars` | Faster confirmation (1 bar) better than waiting (avg −1.81 at 1 bar vs −2.38 at 3 bars) — waiting longer gives back edge |
| `tf_min` | 5-min slightly better than 1-min (avg −1.97 vs −2.25) |

---

## Recommendation

**Do not implement MR-16 standalone.** The clearest directional insight — NY
session, longer OR (15–30 min), fast reversal confirmation, opposite-band
target — is worth carrying forward qualitatively into related session-based
strategies (e.g. MR-03 VWAP or MR-12 Pivot Point), but as a standalone signal
it does not clear the transaction-cost bar, and walk-forward selection is
unstable across windows.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 288 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
