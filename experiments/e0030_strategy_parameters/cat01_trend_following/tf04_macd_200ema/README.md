# TF-04 — MACD + 200 EMA Trend Filter Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-04`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

The 200-period EMA defines the dominant trend (price above = bull regime).
MACD crossovers are only traded in the direction of the 200 EMA, eliminating
the majority of counter-trend false signals.

## Parameter Search Space

```
trend_ema    : [100, 150, 200, 250]    — 4 values
macd_fast    : [8, 10, 12]            — 3 values
macd_slow    : [21, 26, 30]           — 3 values
macd_signal  : [7, 9]                 — 2 values
atr_stop_mult: [1.0, 1.5, 2.0]       — 3 values
timeframe    : [5min, 15min]          — 2 values
```

Approximate combinations: ~648.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
