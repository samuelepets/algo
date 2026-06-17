# TF-01 — EMA Crossover Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-01`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min bars → resampled to 5-min and 15-min)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

A fast EMA crosses above/below a slow EMA to signal a directional regime change.
Entry is confirmed when both EMAs slope in the same direction as the cross.
Exit on opposite crossover or ATR-based trailing stop.

## Parameter Search Space

```
fast_ema     : [3, 5, 7, 8, 9, 10, 12, 13]          — 8 values
slow_ema     : [18, 20, 21, 25, 26, 30, 34, 50]      — 8 values
constraint   : slow_ema > fast_ema + 5
atr_stop_mult: [0.5, 1.0, 1.5, 2.0, 2.5]            — 5 values
rr_ratio     : [1.0, 1.5, 2.0, 2.5, 3.0]            — 5 values
timeframe    : [5min, 15min]                          — 2 values
```

Approximate valid combinations (after constraint): ~1,500.

## Expected Outputs

- `outputs/results.csv` — full grid: `fast_ema, slow_ema, atr_stop_mult, rr_ratio, tf, sharpe, profit_factor, max_dd, total_return, n_trades`
- `outputs/top_params.json` — top-10 by Sharpe
- `outputs/walkforward.csv` — walk-forward metrics for the top combination

## How to Run

```bash
cargo run --release
# Run from this directory; data path ../../../../data/bars/EURUSD/ must exist.
```

Typical runtime: **~8.5 seconds** on a modern CPU (3,150 combinations, rayon parallel).

## Results (EURUSD 2003–2025)

| Metric | Value |
|---|---|
| Combinations tested | 3,150 (1,575 × 5-min + 1,575 × 15-min) |
| Valid results (≥50 trades) | 3,150 |
| Best Sharpe (full history) | −0.5631 |
| Best combo | fast=13, slow=50, atr_m=2.5, rr=3.0, tf=15min |
| Conclusion | **No edge found** — all combinations are net losing |

Walk-forward OOS Sharpe (best combo): −0.54, −1.80, −1.73 (windows 2–4).
Window 1 (OOS 2015–2018) marginally positive at +0.09 — not robust.

**Finding:** Raw EMA crossover without additional regime/session filters
has no statistically significant edge on EURUSD. Spread cost (0.8 pip)
alone does not explain the losses — the crossover signals themselves
generate net negative returns across all parameter combinations.

Recommend advancing to filtered variants (TF-05 EMA+RSI, TF-06 ADX+EMA,
TF-07 SuperTrend) which may suppress the high rate of false crossovers.
