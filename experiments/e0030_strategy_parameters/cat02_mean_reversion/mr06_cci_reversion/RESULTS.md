# RESULTS — MR-06 CCI Extreme Reversion

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr06_cci_reversion` |
| Strategy | CCI Extreme Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-06` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 7.1 s (script-internal), 9.3 s wall-clock |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `cci_period` | 10, 14, 20, 30 (4 values) |
| `entry_threshold` | 100, 125, 150, 200 (4 values) |
| `exit_threshold` | 0, 25, 50 (3 values) |
| `adx_filter` | none, <20, <25 (3 values) |
| `atr_stop_mult` | 1.0, 1.5, 2.0 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **864** (432 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |
| Forced-exit safety net (fixed, not grid-searched) | 100 bars |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `cci_period` | 10 |
| `entry_threshold` | 200 |
| `exit_threshold` | 0 |
| `adx_filter` | none |
| `atr_stop_mult` | 1.5 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **+0.5554** |
| Profit Factor | 1.0935 |
| Max Drawdown (R, absolute) | 195.52 |
| Total Return (R) | 729.73 |
| Number of Trades | 9,013 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. Unlike the full-history best
combination, the IS-selected combo differs across windows.

| Window | IS | OOS | Selected | IS Sharpe | IS PF | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | cci20/entry100/exit0 no_adx stop1.5x 15m | +0.830 | 1.108 | +0.067 | 1.008 | 2,661 |
| 2 | 2003–2016 | 2017–2020 | cci10/entry200/exit0 no_adx stop1.5x 15m | +0.897 | 1.154 | −0.613 | 0.910 | 1,608 |
| 3 | 2003–2018 | 2019–2022 | cci20/entry150/exit0 adx<20 stop1.5x 15m | +0.806 | 1.160 | −0.127 | 0.977 | 1,320 |
| 4 | 2003–2020 | 2021–2025 | cci20/entry150/exit0 adx<20 stop1.5x 15m | +0.732 | 1.144 | −0.455 | 0.920 | 1,726 |

Mean OOS Sharpe across all 4 windows: **−0.28**. Every window shows a strong
positive IS Sharpe (0.73–0.90) that does not carry over OOS: 3 of 4 windows
are OOS-negative, and the sole positive OOS window (+0.067, PF 1.008) is
statistically indistinguishable from breakeven despite 2,661 trades.

---

## Key Finding

**No robust edge — an IS-overfitting pattern, not a genuine signal.** Of the
864 combinations that clear the `≥ 50` trades filter (all of them, at these
entry/exit thresholds the strategy trades frequently):

- 72 / 864 with Sharpe > 0 (8.3%)
- 72 / 864 with Profit Factor > 1.0 (same set)
- Best full-history Sharpe: +0.5554 (15-min, `cci10/entry200/exit0`, no ADX
  filter, 1.5× ATR stop, 9,013 trades)
- Worst Sharpe: −13.92 (5-min, `cci10/entry100/exit50`, no ADX filter, 1.0×
  ATR stop — 265,849 trades, fully spread-dominated)

The full-history best combination looks promising in isolation (positive
Sharpe, PF > 1, thousands of trades), but walk-forward exposes it as
in-sample-fit: IS Sharpe is consistently strong (0.73–0.90) while OOS Sharpe
is negative in 3 of 4 windows and effectively zero in the fourth. This is the
classic signature of a parameter search finding noise that happened to work
well on the training window rather than a persistent statistical edge.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min clearly outperforms 5-min (mean Sharpe −0.92 vs −3.87 across all 864 combos) — 5-min reversion trading is dominated by the fixed 0.8-pip spread, same pattern as MR-01 |
| `entry_threshold` | Higher (stricter) thresholds are less bad (mean −3.26 at 100 → −1.30 at 200) — fewer, more extreme signals outperform frequent shallow-deviation entries |
| `exit_threshold` | Counter-intuitively, the strictest target (`0`, i.e. essentially wait for a full return to the mean or the 100-bar forced exit) is least bad (mean −0.59) versus looser targets (−2.90 at 25, −3.70 at 50) — exiting on a partial CCI reversion cuts winners short relative to the move needed to overcome the spread and the size of the initial (200-threshold) entry |
| `adx_filter` | Modest help: `<20` (mean −2.19) and `<25` (mean −2.39) both beat no filter (mean −2.62), but the effect is small and does not flip any timeframe/period combination to a robust positive |
| `atr_stop_mult` | Wider stops are markedly less bad (mean −1.82 at 2.0× vs −3.13 at 1.0×) — tight stops get clipped by intrabar noise before the reversion plays out |
| `cci_period` | Longer periods are less bad (mean −1.91 at 30 vs −2.83 at 10) — shorter CCI windows produce noisier, less reliable extremes |

Direction of "least bad": 15-min, high entry threshold (200), strict exit
threshold (0), wide ATR stop (2.0×), longer CCI period (20–30), ADX filter
<20. Even the single best full-history point along this direction does not
survive walk-forward — the parameter search narrows the loss and can produce
an in-sample-positive pocket, but it does not demonstrate an edge that
generalises out-of-sample.

---

## Recommendation

**Do not implement MR-06 standalone.**

CCI extreme reversion produces a handful of full-history-positive parameter
combinations, but the one best combination fails walk-forward validation
(strong IS Sharpe, negative-to-flat OOS Sharpe in every window). As
implemented — CCI extremes with an ATR stop and either a full mean-reversion
target or a forced-time exit — this is not a demonstrated, robust edge on
EURUSD across the 23-year history.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | MR-04 Z-Score Reversion | Statistically cleaner signal on log-returns instead of a MAD-scaled price band |
| 2 | MR-03 VWAP Deviation | Session-anchored institutional reference, not a rolling SMA-of-typical-price |
| 3 | MR-09 EMA Rubber Band | Simpler distance-based signal; compare against MR-06's CCI-extreme trigger and its exit-threshold sensitivity |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 864 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
