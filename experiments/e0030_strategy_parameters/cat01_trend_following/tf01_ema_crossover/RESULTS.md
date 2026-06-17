# RESULTS — TF-01 EMA Crossover

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf01_ema_crossover` |
| Strategy | EMA Crossover (Fast/Slow) |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-01` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Rust — `cargo run --release` ≈ 8.5 s |
| Run date | 2026-06-17 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `fast_ema` | 3, 5, 7, 8, 9, 10, 12, 13 (8 values) |
| `slow_ema` | 18, 20, 21, 25, 26, 30, 34, 50 (8 values) |
| `atr_stop_mult` | 0.5, 1.0, 1.5, 2.0, 2.5 (5 values) |
| `rr_ratio` | 1.0, 1.5, 2.0, 2.5, 3.0 (5 values) |
| `tf_min` | 5, 15 (2 values) |
| Constraint | `slow_ema > fast_ema + 5` |
| **Total combinations** | **3,150** |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `fast_ema` | 13 |
| `slow_ema` | 50 |
| `atr_stop_mult` | 2.5 |
| `rr_ratio` | 3.0 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.5631** |
| Profit Factor | 0.9274 |
| Max Drawdown (R, absolute) | 394.82 |
| Total Return (R) | −335.30 |
| Number of Trades | 8,294 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. Selected params are logged.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | 13/50, 2.5×, rr2.5, 15m | −0.133 | −0.202 | 0.974 | 71.1 | 1,426 |
| 2 | 2003–2016 | 2017–2020 | 12/34, 2.5×, rr3.0, 15m | −0.110 | −0.700 | 0.920 | 112.7 | 1,834 |
| 3 | 2003–2018 | 2019–2022 | 13/50, 2.5×, rr3.0, 15m | −0.089 | −1.799 | 0.795 | 194.8 | 1,540 |
| 4 | 2003–2020 | 2021–2025 | 13/50, 2.5×, rr3.0, 15m | −0.227 | −1.730 | 0.800 | 251.0 | 1,916 |

All four OOS windows are negative. Under proper IS-only selection the
2015–2018 window is **−0.202** (not the +0.092 reported under the earlier leaky
protocol). Windows 2–4 degrade further.

---

## Key Finding

**No edge found.** All 3,150 combinations produce negative Sharpe ratios.

- 0 / 3,150 combinations with Sharpe > 0
- 0 / 3,150 combinations with Profit Factor > 1.0
- Best Sharpe overall: −0.5631 (15-min, large stops, high R:R)
- Worst Sharpe: −43.1 (5-min, tiny stops, low R:R = overtrades)

The strategy loses net even before accounting for any slippage beyond the
0.8-pip spread. The losses are not driven by transaction costs — they reflect
the inherent noise of raw EMA crossovers producing more losing than winning
signals on EURUSD at this granularity.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min strongly outperforms 5-min (mean Sharpe −3.34 vs −11.41) |
| `rr_ratio` | Higher R:R improves Sharpe monotonically (−9.61 at rr=1.0 → −5.96 at rr=3.0) |
| `atr_stop_mult` | Wider stops dramatically reduce loss (−15.99 at 0.5× → −3.83 at 2.5×) |
| `fast_ema` | Slower fast EMAs (12, 13) slightly better than very fast (3, 5) |
| `slow_ema` | Larger slow EMA (50) slightly better than smaller (18-21) |

Direction of "least bad": slow MA, wide stop, high R:R, longer TF. This
pattern suggests the strategy can be partially rescued by (a) eliminating
low-quality crossovers with a regime filter and (b) staying in winners longer.

---

## Recommendation

**Do not implement TF-01 standalone.**

Proceed to filtered variants that address the core weakness (too many false
crossovers):

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | TF-06 ADX + EMA | ADX > 25 regime filter eliminates low-quality crossovers |
| 2 | TF-05 EMA + RSI | RSI > 55 momentum gate |
| 3 | TF-07 SuperTrend | ATR-based adaptive band reduces whipsaw |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 3,150 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `PERFORMANCE.md` | Full parameter breakdown and distribution analysis |
| `src/` | Rust implementation |
