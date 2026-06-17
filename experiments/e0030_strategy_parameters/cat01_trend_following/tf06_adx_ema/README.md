# TF-06 — ADX + EMA Directional System Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-06`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

ADX > threshold confirms a trending market (avoids ranging conditions). The
directional indicators +DI and −DI, combined with price vs. EMA, determine
direction. Only enter when ADX confirms trend strength.

## Parameter Search Space

```
adx_period    : [10, 14, 20]               — 3 values
adx_threshold : [15, 20, 25, 30]           — 4 values
trend_ema     : [20, 50, 100]              — 3 values
di_cross      : [true, false]              — 2 values
atr_stop_mult : [1.0, 1.5, 2.0]           — 3 values
timeframe     : [5min, 15min]              — 2 values
```

Approximate combinations: ~432.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
