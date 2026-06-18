# RESULTS — TF-02 Triple EMA Alignment

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf02_triple_ema` |
| Strategy | Triple EMA Alignment (Pullback Rejection) |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md § TF-02` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 10 s end-to-end |
| Run date | 2026-06-18 |

---

## Implementation Notes

Exit logic follows the TF-01 Python engine pattern (intrabar ATR stop → fixed
2:1 R:R target → alignment break when `fast` crosses `slow`), not the prose
spec's “two consecutive closes below `EMA(fast)`”. See
[`README.md`](./README.md#implementation-semantics) for the full mapping.

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `fast_ema` | 3, 5, 8, 9 (4 values) |
| `mid_ema` | 13, 20, 21, 34 (4 values) |
| `slow_ema` | 34, 50, 55, 89 (4 values) |
| `pullback_ema` | mid, slow (2 values) |
| `atr_stop_mult` | 1.0, 1.5, 2.0 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| Constraint | `fast < mid < slow` |
| Fixed `rr_ratio` | 2.0 (not searched) |
| **Total combinations** | **720** (360 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `fast_ema` | 9 |
| `mid_ema` | 34 |
| `slow_ema` | 89 |
| `pullback_ema` | slow |
| `atr_stop_mult` | 1.5 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.1705** |
| Profit Factor | 0.9692 |
| Max Drawdown (R, absolute) | 107.03 |
| Total Return (R) | −61.96 |
| Number of Trades | 3,081 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. Selected params are logged.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | 8/34/89, pb=slow, 1.5×, 15m | −0.030 | **+0.603** | 1.118 | 39.9 | 530 |
| 2 | 2003–2016 | 2017–2020 | 8/34/89, pb=slow, 1.5×, 15m | +0.042 | −0.008 | 0.998 | 46.4 | 532 |
| 3 | 2003–2018 | 2019–2022 | 8/34/89, pb=slow, 1.5×, 15m | +0.135 | −0.604 | 0.897 | 46.7 | 554 |
| 4 | 2003–2020 | 2021–2025 | 9/34/89, pb=slow, 1.5×, 15m | +0.030 | −0.868 | 0.857 | 88.1 | 709 |

Window 1 OOS is mildly positive under IS-only selection, but three of four OOS
windows are negative and the full-history best combination is still net-losing.

---

## Key Finding

**No edge found on full history.** All 720 combinations produce negative Sharpe
ratios and profit factors below 1.0.

- 0 / 720 combinations with Sharpe > 0
- 0 / 720 combinations with Profit Factor > 1.0
- Best Sharpe overall: −0.1705 (15-min, slow pullback, wide slow EMA 89)
- Worst Sharpe: −15.47 (5-min, tight stops, fast EMAs)

Compared to TF-01 (best Sharpe −0.56), triple-EMA alignment with pullback
entries is **materially less bad** on EURUSD full history — the slope + alignment
filter and pullback gate reduce noise — but still net-losing before any slippage
beyond the 0.8-pip spread.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min strongly outperforms 5-min (mean Sharpe −1.83 vs −7.14) |
| `pullback_ema` | Slow-EMA pullbacks better than mid (mean −3.42 vs −5.55) |
| `slow_ema` | 89 dominates top-10; widest slow period filters weakest trends |
| `atr_stop_mult` | Wider stops reduce loss (−6.40 at 1.0× → −3.14 at 2.0×) |
| `fast_ema` | Slightly faster (8–9) in top ranks; very fast (3) overtrades on 5-min |

Direction of "least bad": 15-min, slow EMA 89, pullback to slow, moderate
stop (1.5× ATR). The pullback filter helps versus raw TF-01 crossovers but does
not flip expectancy positive.

---

## Recommendation

**Do not implement TF-02 standalone.**

The alignment + pullback filter improves on TF-01 but remains net-losing. A
single mildly positive IS-selected OOS window (2015–2018) is insufficient
evidence of edge without multiple consistent OOS confirmation.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | TF-06 ADX + EMA | ADX > 25 regime filter on top of EMA stack |
| 2 | TF-05 EMA + RSI | Momentum gate on pullback entries |
| 3 | TF-15 EMA Pullback | Dedicated pullback research with tighter regime filter |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 720 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `PERFORMANCE.md` | End-to-end benchmark report |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
