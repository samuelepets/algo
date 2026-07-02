# RESULTS — MR-07 Williams %R Reversion

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr07_williams_r` |
| Strategy | Williams %R Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-07` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 1-min (native) and 5-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 36 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `wr_period` | 5, 10, 14, 20 (4 values) |
| `oversold_thresh` | −80, −85, −90 (3 values) |
| `overbought_thresh` | −20, −15, −10 (3 values) |
| `exit_level` | −50, −40, −60 (3 values) |
| `atr_stop_mult` | 0.75, 1.0, 1.5 (3 values) |
| `max_hold_bars` | 5, 10, 15 (3 values) |
| `tf_min` | 1, 5 (2 values) |
| **Total combinations** | **1,944** (972 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `wr_period` | 20 |
| `oversold_thresh` | −90 |
| `overbought_thresh` | −10 |
| `exit_level` | −50 |
| `atr_stop_mult` | 1.5 |
| `max_hold_bars` | 15 |
| `tf_min` | 5 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−3.7217** |
| Profit Factor | 0.8839 |
| Max Drawdown (R, absolute) | 6,482.07 |
| Total Return (R) | −6,265.86 |
| Number of Trades | 100,272 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | wr14 os−90/ob−10 exit−60 stop1.5x hold15 5m | −0.717 | −5.423 | 0.851 | 22,569 |
| 2 | 2003–2016 | 2017–2020 | wr14 os−90/ob−10 exit−60 stop1.5x hold15 5m | −1.285 | −8.439 | 0.778 | 22,637 |
| 3 | 2003–2018 | 2019–2022 | wr20 os−90/ob−10 exit−50 stop1.5x hold15 5m | −1.909 | −6.161 | 0.824 | 19,320 |
| 4 | 2003–2020 | 2021–2025 | wr20 os−90/ob−10 exit−40 stop1.5x hold15 5m | −2.506 | −7.672 | 0.785 | 24,424 |

All 4 windows are IS-negative already, and OOS performance is materially
worse in every window — no sign of a stable, exploitable edge at any point in
the 23-year sample.

---

## Key Finding

**No edge found.** Of all 1,944 combinations (all clear the `≥ 50` trades
filter given the strategy fires very frequently):

- 0 / 1,944 with Sharpe > 0
- 0 / 1,944 with Profit Factor > 1.0
- Best Sharpe: −3.7217 (5-min, wr20, deepest thresholds −90/−10, wide 1.5×
  stop, longest 15-bar hold)
- Worst Sharpe: −126.89 (1-min, tight thresholds, short hold — extreme
  overtrading)

Williams %R fires on essentially every short-term high/low touch, producing
trade counts from tens of thousands (5-min) to hundreds of thousands (1-min)
per combination. At that frequency the fixed 0.8-pip round-trip spread
dominates the tiny mean-reversion edge, if any exists, and every single
tested configuration is net-losing.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 5-min is far less bad than 1-min (mean Sharpe −8.85 vs −59.40) — 1-min %R crosses are almost pure noise relative to the spread cost |
| `wr_period` | Longer lookback is less bad (mean Sharpe −46.13 at 5 → −25.86 at 20) — shorter windows fire more often on noise |
| `atr_stop_mult` | Wider stops reduce loss (mean −38.18 at 0.75× → −29.80 at 1.5×) |
| `max_hold_bars` | Longer holds slightly less bad (−37.61 at 5 bars → −31.83 at 15 bars) |
| `oversold_thresh` / `overbought_thresh` | More extreme thresholds (−90/−10) are marginally less bad than shallower ones (−80/−20) (mean −32.98 vs −35.49) — but the effect is small relative to the timeframe and period effects |

Direction of "least bad": 5-min timeframe, longest `wr_period` (20), most
extreme thresholds, widest stop, longest hold. Even at these settings
expectancy stays deeply negative — parameter tuning narrows the loss by an
order of magnitude but never approaches breakeven.

---

## Recommendation

**Do not implement MR-07 standalone.**

Raw Williams %R crossing signals fire far too frequently at both 1-min and
5-min resolution on EURUSD; every one of the 1,944 tested configurations is
net-losing after the fixed spread cost, and the walk-forward test confirms
this is not a full-history-only artifact — every OOS window is strongly
negative. A viable version of this idea would need either a much stronger
entry filter (e.g. only trade %R extremes that persist for several
consecutive bars, or add a trend/volatility regime gate) or a much less
frequent timeframe (15-min+) to bring trade count down and average edge per
trade up before the spread eats it.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | MR-09 EMA Rubber Band | ATR-normalised distance signal, naturally lower-frequency than raw %R crosses |
| 2 | MR-14 StochRSI Reversion | Double-smoothed oscillator (K/D), should fire less often than raw %R |
| 3 | MR-15 DeMarker Reversion | Rolling-mean based oscillator, structurally smoother than %R |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 1,944 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
