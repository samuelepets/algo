# RESULTS — MR-02 RSI(2) Ultra-Short Reversion

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr02_rsi2_reversion` |
| Strategy | RSI(2) Ultra-Short Reversion (Connors) |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-02` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 53.7 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `rsi_period` | 2, 3, 4 (3 values) |
| `long_threshold` | 2, 5, 10, 15 (4 values) |
| `short_threshold` | 98, 95, 90, 85 (4 values) |
| `exit_rsi_long` | 50, 55, 60, 65 (4 values) |
| `exit_rsi_short` | 50, 45, 40, 35 (4 values) |
| `trend_ema` (SMA period) | none, 100, 200 (3 values) |
| `max_hold_bars` | 3, 5, 10, 15 (4 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **18,432** (9,216 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |
| ATR stop | fixed 1.5x ATR(14) (not a grid dimension) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `rsi_period` | 3 |
| `long_threshold` | 5 |
| `short_threshold` | 98 |
| `exit_rsi_long` | 50 |
| `exit_rsi_short` | 40 |
| `trend_ema` | 100 (SMA) |
| `max_hold_bars` | 10 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **0.8499** |
| Profit Factor | 1.4192 |
| Max Drawdown (R, absolute) | 8.09 |
| Total Return (R) | 98.29 |
| Number of Trades | 848 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. All 4 windows independently
selected the same `RSI(3)` / SMA(100) filter / 15-min family (window 4 picked
a slightly tighter `long<5`/`short>98`/`exit_rsi_long=55` variant, the others
picked `long<10`/`short>90`/`exit_rsi_long=65`).

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | rsi3 L<10 S>90 exL65 exS40 trend100 hold15 15m | +1.455 | +0.665 | 1.097 | 1,085 |
| 2 | 2003–2016 | 2017–2020 | rsi3 L<10 S>90 exL65 exS40 trend100 hold15 15m | +1.442 | +0.017 | 1.002 | 1,120 |
| 3 | 2003–2018 | 2019–2022 | rsi3 L<10 S>90 exL65 exS40 trend100 hold15 15m | +1.239 | −0.562 | 0.925 | 1,134 |
| 4 | 2003–2020 | 2021–2025 | rsi3 L<5 S>98 exL55 exS40 trend100 hold15 15m | +1.131 | −0.139 | 0.951 | 216 |

IS Sharpe is consistently strong (1.13–1.46) across all 4 windows — the
selection is stable, not noisy — but OOS Sharpe monotonically decays from
+0.665 (earliest OOS window) to −0.562 (2019–2022) before a mild recovery to
−0.139 (2021–2025). 2 of 4 OOS windows are net negative.

---

## Key Finding

**Weak edge, not confirmed out-of-sample — decays with time.** Of the 18,240
combinations that clear the `≥ 50` trades filter:

- 3,600 / 18,240 (19.7%) have Sharpe > 0
- 3,600 / 18,240 (19.7%) have Profit Factor > 1.0 (identical set — PF > 1
  and Sharpe > 0 agree on every single row)
- Best Sharpe: 0.8499 (15-min, `RSI(3)`, SMA(100) filter, tight thresholds)
- Worst Sharpe: −15.24 (5-min, `RSI(2)`, no trend filter, `hold=3` —
  302,542 trades, fully spread-dominated churn)

Unlike `mr01_bollinger_band` (0 / 3,456 valid combos positive), MR-02 does
show a real in-sample statistical signal: nearly 1 in 5 valid combinations is
profitable, and the best full-history combination is attractive on paper
(Sharpe 0.85, PF 1.42, 848 trades). But the walk-forward evidence is the
decisive test, and it does not confirm a durable edge — the same,
consistently-selected configuration produces OOS Sharpe that trends from
positive to negative as the walk-forward window moves toward the present.
This is the classic signature of a pattern that worked reasonably well in
earlier, calmer EURUSD regimes and has been arbitraged away or regime-shifted
in the more recent 2019–2025 period.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min strongly outperforms 5-min (mean Sharpe −0.53 vs −3.26 across valid combos) — RSI(2)-style entries on 5-min bars overtrade and get eaten by spread |
| `trend_ema` (SMA filter) | Filter clearly helps: SMA(100) mean Sharpe −1.35, SMA(200) −1.48, vs −2.84 with no filter — trading with the higher-timeframe trend materially improves the reversion signal |
| `rsi_period` | Longer RSI periods are less bad on average (mean Sharpe: 2 → −3.71, 3 → −1.24, 4 → −0.70), though the single best full-history combo uses period 3 — the classic Connors RSI(2) is the noisiest variant here |
| `long_threshold` / `short_threshold` | More selective (extreme) thresholds are less bad on average (`long_threshold=2` mean −1.37 vs `15` mean −2.61; `short_threshold=98` mean −1.45 vs `85` mean −2.48) — looser entry criteria overtrade |
| `max_hold_bars` | Mid-range holds (10–15 bars) outperform short holds (3–5 bars): mean Sharpe −1.47 at 10 bars vs −2.50 at 3 bars — forcing exits too early cuts winners short |
| `exit_rsi_long` / `exit_rsi_short` | Weak effect in either direction (mean Sharpe range ≈ 0.12 across all 4 values of each) |

Direction of "least bad" / most promising: 15-min, `RSI(3)`, SMA(100 or 200)
trend filter, selective thresholds (`long<2..5`, `short>95..98`), holding
10–15 bars. Even at these settings, the edge is thin and does not survive the
walk-forward test in the second half of the sample.

---

## Recommendation

**Do not deploy MR-02 as implemented.** The full-history grid search finds a
statistically plausible signal (unlike MR-01's outright negative result), but
walk-forward validation — the actual test of whether the pattern generalises
— shows the edge fading to roughly breakeven-or-negative in the most recent
~7 years (2019–2025). Treat this as a "candidate that needs more work," not a
confirmed edge:

- The IS-selected family is *stable* (same `RSI(3)`/SMA(100)/15-min
  configuration across all 4 windows), which rules out pure noise in the
  selection process itself — the decay is a genuine regime effect, not
  overfitting to a shifting grid.
- A shorter, rolling (non-anchored) walk-forward, or restricting evaluation
  to the post-2019 regime specifically, would clarify whether the edge is
  merely dormant (e.g. low-volatility-regime-dependent) or permanently gone.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | MR-04 Z-Score Reversion | Statistically cleaner signal on log-returns instead of raw RSI oscillator |
| 2 | MR-14 StochRSI Reversion | Related oscillator family; compare decay pattern against MR-02 |
| 3 | MR-19 Connors RSI (3-Component) | Adds streak/rank components on top of RSI(2) — may filter out the regime-dependent false signals seen here |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 18,432 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
