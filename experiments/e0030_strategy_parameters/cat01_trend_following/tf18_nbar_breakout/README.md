# TF-18 — N-Period High/Low Breakout Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-18`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

Price exceeding the highest high of the last N bars signals renewed momentum.
Simpler than Donchian (no separate exit channel). Exit is either a fixed
ATR-based stop or a fixed R:R target. Optional volume confirmation filter.

## Entry Logic

Long: `Close[i] > max(High[i-N .. i-1])` (confirmation mode: close only).
Short: `Close[i] < min(Low[i-N .. i-1])`.

## Parameter Search Space

```
breakout_n    : [5, 10, 15, 20, 30, 40, 50]   — 7 values
confirmation  : [close, tick]                  — 2 values
volume_filter : [true, false]                  — 2 values
atr_stop_mult : [1.0, 1.5, 2.0, 2.5]         — 4 values
rr_ratio      : [1.0, 1.5, 2.0]              — 3 values
timeframe     : [5min, 15min]                 — 2 values
```

Approximate combinations: ~672.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
