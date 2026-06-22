# RESULTS — TF-14 Hull Moving Average (HMA) Trend

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat01_trend_following / tf14_hma` |
| Strategy | Hull Moving Average (HMA) Trend |
| Category | Trend-Following |
| Reference | `strategies/01_TREND_FOLLOWING.md` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled per grid |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — 5-min grid only ≈ 7 s (`main.py` crashes on 1-min, exit 138) |
| Run date | 2026-06-22 |
| **Run scope** | **5-min timeframe only (102/204 combos)** — 1-min kernel aborts |

---

## Implementation Notes

Same backtester conventions as the rest of the family (entries at bar close, stop
checked first intrabar, P&L in R units, spread `0.00008`). The smoothing length uses
`round(sqrt(n))`. The 1-min backtest kernel aborts (exit 138) on this machine; this
run covers the **5-min** grid only. See [`README.md`](./README.md#implementation-semantics).

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `hma_fast` | [6, 9, 12, 16, 20]          — 5 values |
| `hma_slow` | [20, 25, 36, 49]            — 4 values  (crossover variant) |
| `mode` | [slope, crossover]           — 2 values |
| `slope_bars` | [1, 2, 3]                   — 3 values  (confirmation bars) |
| `atr_stop_mult` | [1.0, 1.5, 2.0]            — 3 values |
| `timeframe` | [1min, 5min]                — 2 values |

| **Total combinations** | **102** (5-min only; 1-min not run — see Run scope) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination

| Parameter | Value |
|---|---|
| `hma_fast` | 20 |
| `hma_slow` | 49 |
| `mode` | crossover |
| `slope_bars` |  |
| `atr_stop_mult` | 2.00 |
| `tf_min` | 5 |


### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **-6.3566** |
| Profit Factor | 0.7596 |
| Max Drawdown (R, absolute) | 8,320.11 |
| Total Return (R) | -8,296.04 |
| Number of Trades | 67,085 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. Selected params are logged.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | hma_fast=20, hma_slow=49, mode=crossover, atr_mult=2.00, tf=5 | -4.439 | -6.502 | 0.761 | 1577.9 | 12165 |
| 2 | 2003–2016 | 2017–2020 | hma_fast=20, hma_slow=49, mode=crossover, atr_mult=2.00, tf=5 | -4.656 | -9.029 | 0.688 | 2172.7 | 12266 |
| 3 | 2003–2018 | 2019–2022 | hma_fast=20, hma_slow=49, mode=crossover, atr_mult=2.00, tf=5 | -5.000 | -9.255 | 0.683 | 2262.8 | 12361 |
| 4 | 2003–2020 | 2021–2025 | hma_fast=20, hma_slow=49, mode=crossover, atr_mult=2.00, tf=5 | -5.700 | -8.515 | 0.704 | 2610.7 | 15353 |

All 4 oos windows are negative. IS-only selection details in `outputs/walkforward.csv`.

---

## Key Finding

**No edge found on full history.** All 102 combinations produce negative Sharpe ratios and profit factors below 1.0.

- 0 / 102 combinations with Sharpe > 0
- 0 / 102 combinations with Profit Factor > 1.0
- Best Sharpe overall: -6.3566 (hma_fast=20, hma_slow=49, mode=crossover, slope_bars=, atr_stop_mult=2.00, 5m)
- Worst Sharpe: -35.8913 (hma_fast=6, hma_slow=, mode=slope, slope_bars=1, atr_stop_mult=1.00, 5m)

Compared to TF-01 (best Sharpe -0.56), TF-02 (best Sharpe -0.17), and TF-03 (best Sharpe -2.10), this strategy is **materially worse** on EURUSD full history (best Sharpe -6.3566).

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | Best mean Sharpe on 5-min; all: 5-min (mean -16.91) |
| `atr_stop_mult` | Wider stops less bad (2.00× mean -14.43 vs 1.00× mean -20.34) |
| `hma_slow` | Best level 49 (mean Sharpe -9.94) |
| `mode` | Best level crossover (mean Sharpe -11.75) |
| `slope_bars` | Best level  (mean Sharpe -11.75) |


---

## Recommendation

**Do not implement TF-14 standalone.**

No expectancy edge on EURUSD under this grid.

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 102 combinations (not committed) |
| `outputs/top_params.json` | Top-10 by Sharpe (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `data.py`, `indicators.py` | Python implementation |
