# RESULTS — MR-01 Bollinger Band Mean Reversion

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr01_bollinger_band` |
| Strategy | Bollinger Band Mean Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-01` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 17 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `bb_period` | 10, 14, 20, 30, 50 (5 values) |
| `bb_mult` | 1.0, 1.5, 2.0, 2.5, 3.0 (5 values) |
| `entry_type` | close_outside, reentry (2 values) |
| `adx_filter` | none, <20, <25 (3 values) |
| `atr_stop_mult` | 0.5, 1.0, 1.5 (3 values) |
| `max_hold_bars` | 5, 10, 20, 30 (4 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **3,600** (1,800 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `bb_period` | 30 |
| `bb_mult` | 3.0 |
| `entry_type` | reentry |
| `adx_filter` | <20 |
| `atr_stop_mult` | 1.5 |
| `max_hold_bars` | 20 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.1533** |
| Profit Factor | 0.9636 |
| Max Drawdown (R, absolute) | 58.69 |
| Total Return (R) | −37.51 |
| Number of Trades | 1,846 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. The same configuration
(`bb30/3.0x reentry adx<20 stop1.5x hold20 15m`) was selected in all 4 windows.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | bb30/3.0x reentry adx<20 stop1.5x hold20 15m | +0.019 | −0.085 | 0.979 | 317 |
| 2 | 2003–2016 | 2017–2020 | bb30/3.0x reentry adx<20 stop1.5x hold20 15m | −0.026 | −0.341 | 0.916 | 294 |
| 3 | 2003–2018 | 2019–2022 | bb30/3.0x reentry adx<20 stop1.5x hold20 15m | −0.008 | −0.113 | 0.971 | 278 |
| 4 | 2003–2020 | 2021–2025 | bb30/3.0x reentry adx<20 stop1.5x hold20 15m | −0.099 | −0.339 | 0.921 | 392 |

All 4 OOS windows are negative — no window produced positive out-of-sample
Sharpe, and IS Sharpe is already close to zero (best +0.019).

---

## Key Finding

**No edge found.** Of the 3,456 combinations that clear the `≥ 50` trades
filter:

- 0 / 3,456 with Sharpe > 0
- 0 / 3,456 with Profit Factor > 1.0
- Best Sharpe: −0.1533 (15-min, wide band 30/3.0σ, reentry, ADX<20)
- Worst Sharpe: −36.05 (5-min, tight band 10/1.0σ, reentry, tight 0.5× stop —
  298,488 trades, fully spread-dominated)

Only 38 combinations (out of the full 3,600) show positive Sharpe/PF at all,
and every one of them has fewer than 50 trades (down to 6 trades) — noise, not
signal. Naive Bollinger Band fading has no exploitable edge on EURUSD across
the full 23-year history, at either timeframe tested.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min clearly outperforms 5-min (mean Sharpe −2.61 vs −8.05) — 5-min reversion trading is dominated by the fixed 0.8-pip spread |
| `bb_mult` | Wider bands are less bad (mean −9.81 at 1.0σ → −1.57 at 3.0σ) — fading shallow deviations overtrades |
| `entry_type` | `close_outside` beats `reentry` on average (mean −4.06 vs −6.59), though the single best combo uses `reentry` |
| `atr_stop_mult` | Wider stops reduce loss (mean −7.46 at 0.5× → −3.73 at 1.5×) |
| `bb_period` | Longer SMA periods are less bad (mean −7.19 at 10 → −4.02 at 50) |
| `max_hold_bars` | Weak effect; longer holds slightly less bad (−6.03 at 5 bars → −4.98 at 30 bars) |

Direction of "least bad": 15-min, wide band (period 30–50, mult 2.5–3.0),
wider ATR stop (1.5×). Even at these settings expectancy stays negative — the
regime/parameter search narrows the loss, it does not flip it positive.

---

## Recommendation

**Do not implement MR-01 standalone.**

Plain Bollinger Band fading, even with an ADX non-trending filter, is
net-losing on EURUSD across the full grid and every walk-forward window. The
ADX filter (`<20`/`<25`) does not meaningfully change average Sharpe versus no
filter (mean PF 0.754 / 0.769 / 0.785 for `<20` / `<25` / none respectively),
suggesting the regime gate as implemented is too weak to isolate genuinely
range-bound conditions.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | MR-04 Z-Score Reversion | Statistically cleaner signal on log-returns instead of raw price bands |
| 2 | MR-03 VWAP Deviation | Session-anchored institutional reference, not a rolling SMA |
| 3 | MR-09 EMA Rubber Band | Simpler distance-based signal; compare against MR-01's band-touch trigger |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 3,600 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
