# RESULTS — MR-04 Z-Score Statistical Reversion

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr04_zscore_reversion` |
| Strategy | Z-Score Statistical Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-04` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 9.7 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `zscore_window` | 20, 30, 60, 120, 240 (5 values) |
| `entry_threshold` | 1.5, 2.0, 2.5, 3.0 (4 values) |
| `exit_threshold` | 0.0, 0.5 (2 values) |
| `atr_stop_mult` | 0.75, 1.0, 1.5, 2.0 (4 values) |
| `input_type` | log_return, close_detrended (2 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **640** (320 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |
| Forced-exit safety net (fixed, not grid-searched) | `MAX_HOLD_SAFETY = 200` bars |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `zscore_window` | 20 |
| `entry_threshold` | 3.0 |
| `exit_threshold` | 0.0 |
| `atr_stop_mult` | 1.5 |
| `input_type` | close_detrended |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.2215** |
| Profit Factor | 0.9716 |
| Max Drawdown (R, absolute) | 186.48 |
| Total Return (R) | −109.90 |
| Number of Trades | 6,470 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. All 4 windows selected a
`zscore_window=20, entry_threshold=2.5, exit_threshold=0.0, close_detrended,
15-min` configuration (the ATR stop varies slightly: 1.5× in windows 1–3,
2.0× in window 4).

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | w20 entry2.5 exit0.0 stop1.5x close_detrended 15m | −0.2536 | −0.2906 | 0.9769 | 3,021 |
| 2 | 2003–2016 | 2017–2020 | w20 entry2.5 exit0.0 stop1.5x close_detrended 15m | −0.2146 | −0.5820 | 0.9535 | 2,914 |
| 3 | 2003–2018 | 2019–2022 | w20 entry2.5 exit0.0 stop1.5x close_detrended 15m | −0.2669 | −0.8740 | 0.9313 | 2,873 |
| 4 | 2003–2020 | 2021–2025 | w20 entry2.5 exit0.0 stop2.0x close_detrended 15m | −0.2652 | −0.8667 | 0.9305 | 3,435 |

All 4 OOS windows are negative and, notably, every OOS Sharpe is
*more negative* than its corresponding IS Sharpe — expectancy erodes further
out of sample rather than holding steady.

---

## Key Finding

**No edge found.** Of the 640 combinations tested, all 640 clear the `≥ 50`
trades filter:

- 0 / 640 with Sharpe > 0
- 0 / 640 with Profit Factor > 1.0
- Best Sharpe: −0.2215 (15-min, `zscore_window=20`, `entry=3.0`,
  `exit=0.0`, `atr_stop=1.5×`, `close_detrended`)
- Worst Sharpe: −18.08 (5-min, `zscore_window=20`, `entry=1.5`,
  `exit=0.5`, `atr_stop=0.75×`, `log_return` — 188,913 trades, fully
  spread-dominated)

Not a single combination in the 640-point grid produces a positive Sharpe or
profit factor, unlike MR-01 where a handful of below-threshold outlier combos
showed positive (but statistically meaningless) numbers. MR-04's z-score
signal is directionally cleaner than MR-01's raw Bollinger Band touch, but it
does not flip the sign of the result on EURUSD.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `input_type` | `close_detrended` clearly outperforms `log_return` (mean Sharpe −2.07 vs −4.58) — detrended price appears to carry a cleaner mean-reversion signal than the noisier bar-over-bar return z-score |
| Timeframe | 15-min clearly outperforms 5-min (mean Sharpe −1.86 vs −4.78) — same spread-dominance pattern seen in MR-01, worse at high frequency |
| `entry_threshold` | Higher (more extreme) thresholds are systematically less bad (mean Sharpe −5.34 at 1.5 → −1.80 at 3.0) — fading shallow deviations overtrades and eats the spread |
| `atr_stop_mult` | Wider stops reduce loss (mean −4.12 at 0.75× → −2.66 at 2.0×) |
| `zscore_window` | Longer windows are less bad (mean −3.90 at 20 → −2.30 at 240) — a slower-moving mean/std estimate produces fewer, better-timed signals |
| `exit_threshold` | Weak effect; `exit=0.0` slightly less bad than `exit=0.5` (mean −3.12 vs −3.53) — waiting for a full reversion to the mean before exiting is marginally better than exiting early |

Direction of "least bad": 15-min, `close_detrended` input, long window (120–240),
high entry threshold (2.5–3.0), wide ATR stop (1.5–2.0×). As with MR-01, even
at these settings expectancy stays negative — the search narrows the loss, it
does not flip it positive.

---

## Recommendation

**Do not implement MR-04 standalone.**

The statistically cleaner z-score signal (vs. MR-01's raw Bollinger Band
touch) does narrow the loss meaningfully — best full-history Sharpe improves
from MR-01's −0.153 to a comparable −0.221, and MR-04's parameter search is
more decisive about *which* dimensions matter (`close_detrended` vs
`log_return`, window length) — but it still fails to produce a positive
expectancy anywhere in the 640-point grid or in any of the 4 walk-forward
windows. Both entry-signal families (band touch, z-score extreme) point to
the same conclusion: naive statistical/geometric mean reversion, on its own,
does not overcome the EURUSD spread cost across the full 23-year history.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | MR-03 VWAP Deviation | Session-anchored institutional reference, not a rolling SMA/std estimate |
| 2 | MR-09 EMA Rubber Band | Simpler distance-based signal; compare against MR-01/MR-04's band-touch/z-score triggers |
| 3 | MR-02 RSI(2) Reversion | Bounded oscillator signal instead of an unbounded z-score/band distance |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 640 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
