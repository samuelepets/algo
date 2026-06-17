# TF-07 — SuperTrend Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-07`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min, 5-min, 15-min)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

SuperTrend is an ATR-based trailing support/resistance line. When price closes
above the upper band, the indicator flips to bullish (green) — a long entry.
When price closes below the lower band, it flips to bearish — a short entry.
The active band serves as the trailing stop.

## Indicator

```
upper_band = HL2 - multiplier × ATR(atr_period)
lower_band = HL2 + multiplier × ATR(atr_period)
SuperTrend = upper_band when bullish; lower_band when bearish
```

Flip to bullish: `close[i] > lower_band[i-1]`
Flip to bearish: `close[i] < upper_band[i-1]`

## Parameter Search Space

```
atr_period    : [5, 7, 10, 12, 14]       — 5 values
multiplier    : [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]  — 6 values
htf_filter    : [none, 15min, 1h]         — 3 values
atr_target    : [1.0, 1.5, 2.0]          — 3 values (ATR multiple for fixed target)
timeframe     : [1min, 5min, 15min]       — 3 values
```

Approximate combinations: ~810.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
