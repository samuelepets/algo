# TF-13 — EMA Ribbon Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-13`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

A ribbon of N EMAs with geometrically-spaced periods. Full alignment (all EMAs in
ascending order) + ribbon expanding (inter-EMA spacing increasing) signals a
strong trend. Entry on pullback to the fastest EMA.

## Alignment Score

`alignment = count of consecutive in-order pairs / (N-1)` — must meet threshold.

## Parameter Search Space

```
ema_start      : [3, 5, 8]           — 3 values  (period of fastest EMA)
ema_ratio      : [1.5, 1.618, 2.0]   — 3 values  (multiplicative step)
ema_count      : [4, 5, 6]           — 3 values  (total EMAs)
alignment_pct  : [0.8, 0.9, 1.0]     — 3 values  (min fraction in-order)
expansion_bars : [2, 3, 5]           — 3 values  (confirmation window)
timeframe      : [5min, 15min]        — 2 values
```

Approximate combinations: ~486.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
