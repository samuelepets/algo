# TF-08 — SuperTrend + VWAP + ADX Combo Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-08`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

Triple-confirmation trend entry: SuperTrend (direction), VWAP (institutional
price anchor), and ADX (trend strength). All three must agree before entering.
Highest-conviction filter among the trend-following family.

## Entry Conditions

- **Long:** SuperTrend = bullish AND close > VWAP AND close > EMA(trend_ema) AND ADX > adx_threshold
- **Short:** SuperTrend = bearish AND close < VWAP AND close < EMA(trend_ema) AND ADX > adx_threshold

## Parameter Search Space

```
st_atr        : [7, 10, 14]               — 3 values
st_mult       : [2.0, 2.5, 3.0, 3.5]     — 4 values
adx_period    : [10, 14]                  — 2 values
adx_threshold : [20, 25, 30]             — 3 values
trend_ema     : [20, 21, 50]             — 3 values
atr_target    : [1.5, 2.0, 2.5, 3.0]    — 4 values
timeframe     : [5min, 15min]            — 2 values
```

Approximate combinations: ~576.

> **Note:** VWAP requires volume > 0. Validate EURUSD volume data coverage
> before trusting VWAP-dependent results.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
