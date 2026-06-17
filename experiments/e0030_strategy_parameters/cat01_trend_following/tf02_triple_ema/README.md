# TF-02 — Triple EMA Alignment Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-02`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

Three EMAs (fast, mid, slow) must be fully aligned in ascending order with positive
slopes. Entries are taken on pullbacks to EMA(mid) or EMA(slow), confirmed by the
first rejection bar closing back beyond the pullback EMA.

## Parameter Search Space

```
fast_ema     : [3, 5, 8, 9]                 — 4 values
mid_ema      : [13, 20, 21, 34]             — 4 values
slow_ema     : [34, 50, 55, 89]             — 4 values
constraint   : fast < mid < slow
pullback_ema : [mid, slow]                  — 2 values
atr_stop_mult: [1.0, 1.5, 2.0]             — 3 values
timeframe    : [5min, 15min]                — 2 values
```

Approximate valid combinations (after constraint): ~384.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
