# TF-01 — EMA Crossover Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-01`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min bars → resampled to 5-min and 15-min)
**Implementation:** Legacy Rust binary (historical reference). New work in this
repo uses the Python stack — see [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/).

## Strategy Summary

A fast EMA crosses above/below a slow EMA to signal a directional regime change.
Entry is confirmed when both EMAs slope in the same direction as the cross.
Exits, whichever triggers first: a **fixed ATR stop** set at entry
(`entry ∓ atr_stop_mult × ATR(14)`, never moved afterward), a fixed R:R target
(`rr_ratio ×` the stop distance), or an opposite EMA crossover (closed at bar
close). There is no trailing-stop logic — the stop is static for the life of
the trade. A trailing-stop variant is left for a future experiment.

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

- `outputs/results.csv` — full grid: `fast_ema, slow_ema, atr_stop_mult, rr_ratio, tf_min, sharpe, profit_factor, max_drawdown_r, total_return, n_trades`
- `outputs/top_params.json` — top-10 by Sharpe
- `outputs/walkforward.csv` — per-window IS-selected params and IS/OOS metrics (`max_drawdown_r` in absolute R)

## How to Run

```bash
cargo run --release
# Run from this directory; data path ../../../../data/bars/EURUSD/ must exist.
```

Typical runtime: **~12–15 seconds** end-to-end on a modern multi-core CPU
(~3.5 s data load + full-sample grid of 3,150 combinations + per-window IS-only
re-optimisation for the 4 walk-forward windows, all rayon-parallel). Exact
timing depends on CPU core count and filesystem/page caching.

## Results (EURUSD 2003–2025)

| Metric | Value |
|---|---|
| Combinations tested | 3,150 (1,575 × 5-min + 1,575 × 15-min) |
| Valid results (≥50 trades) | 3,150 |
| Best Sharpe (full history) | −0.5631 |
| Best combo | fast=13, slow=50, atr_m=2.5, rr=3.0, tf=15min |
| Conclusion | **No edge found** — all combinations are net losing |

Walk-forward (IS-only parameter selection per window) OOS Sharpe:
−0.20, −0.70, −1.80, −1.73 (windows 1–4) — all negative. The earlier
"+0.09" on window 1 was an artifact of selecting parameters on the full
history; honest IS-only selection removes it.

**Finding:** Raw EMA crossover without additional regime/session filters
has no statistically significant edge on EURUSD. Spread cost (0.8 pip)
alone does not explain the losses — the crossover signals themselves
generate net negative returns across all parameter combinations.

Recommend advancing to filtered variants (TF-05 EMA+RSI, TF-06 ADX+EMA,
TF-07 SuperTrend) which may suppress the high rate of false crossovers.
