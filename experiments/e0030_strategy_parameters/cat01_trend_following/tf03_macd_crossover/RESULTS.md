# RESULTS — TF-03 MACD Line/Signal Crossover

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf03_macd_crossover` |
| Strategy | MACD Line/Signal Crossover |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-03` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 10 s end-to-end |
| Run date | 2026-06-22 |

---

## Implementation Notes

Exit logic follows the TF-01/TF-02 Python engine pattern (intrabar ATR stop → fixed
2:1 R:R target → opposite MACD/signal crossover at bar close). The prose spec's
histogram-shrink exit is **not** implemented. See
[`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `fast_ema` | 5, 8, 10, 12 (4 values) |
| `slow_ema` | 21, 24, 26, 30, 35 (5 values) |
| `signal` | 7, 9, 12 (3 values) |
| `zero_filter` | true, false (2 values) |
| `atr_stop_mult` | 1.0, 1.5, 2.0 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| Constraint | `fast_ema < slow_ema` |
| Fixed `rr_ratio` | 2.0 (not searched) |
| **Total combinations** | **720** (360 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `fast_ema` | 12 |
| `slow_ema` | 35 |
| `signal` | 12 |
| `zero_filter` | true |
| `atr_stop_mult` | 2.0 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−2.1039** |
| Profit Factor | 0.8042 |
| Max Drawdown (R, absolute) | 1,103.98 |
| Total Return (R) | −1,100.50 |
| Number of Trades | 13,233 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. Selected params are logged.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | 10/35/12, z=false, 2.0×, 15m | −1.715 | −2.508 | 0.830 | 367.7 | 4,088 |
| 2 | 2003–2016 | 2017–2020 | 10/35/12, z=false, 2.0×, 15m | −1.771 | −3.014 | 0.801 | 422.2 | 4,132 |
| 3 | 2003–2018 | 2019–2022 | 10/35/12, z=false, 2.0×, 15m | −1.924 | −2.797 | 0.815 | 391.6 | 4,156 |
| 4 | 2003–2020 | 2021–2025 | 12/35/12, z=true, 2.0×, 15m | −1.929 | −2.727 | 0.756 | 333.7 | 2,847 |

All four OOS windows are strongly negative. IS-only selection converges on slow
MACD settings (10/35 or 12/35, signal 12, wide ATR stop) but none generalise.

---

## Key Finding

**No edge found on full history.** All 720 combinations produce negative Sharpe
ratios and profit factors below 1.0.

- 0 / 720 combinations with Sharpe > 0
- 0 / 720 combinations with Profit Factor > 1.0
- Best Sharpe overall: −2.1039 (15-min, zero filter on, slow EMA 35, wide stop)
- Worst Sharpe: −17.52 (5-min, tight stops, fast EMAs)

Compared to TF-01 (best Sharpe −0.56) and TF-02 (best Sharpe −0.17), raw MACD
line/signal crossovers are **substantially worse** on EURUSD full history — the
signal overtrades and lacks a trend-regime filter.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min strongly outperforms 5-min (mean Sharpe −3.34 vs −11.25) |
| `zero_filter` | Slightly less bad with filter on (mean −7.19 vs −7.40) |
| `slow_ema` | Wider slow periods dominate top-10; slow 35 best on average |
| `signal` | Longer signal (12) reduces noise (mean −6.75 vs −7.85 for signal 7) |
| `atr_stop_mult` | Wider stops reduce loss (−8.89 at 1.0× → −6.14 at 2.0×) |
| `fast_ema` | Slower fast EMA (10–12) in top ranks; fast 5 overtrades on 5-min |

Direction of "least bad": 15-min, slow MACD (12/35), signal 12, zero filter on,
wide stop (2.0× ATR). Even this best case remains deeply net-losing.

---

## Recommendation

**Do not implement TF-03 standalone.**

MACD crossover alone shows no expectancy edge on EURUSD. All walk-forward OOS
windows are negative with no single positive period.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | TF-04 MACD + 200 EMA | Long-term trend filter on MACD entries |
| 2 | TF-06 ADX + EMA | Regime filter for trending markets only |
| 3 | TF-05 EMA + RSI | Momentum gate to reduce whipsaw entries |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 720 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
