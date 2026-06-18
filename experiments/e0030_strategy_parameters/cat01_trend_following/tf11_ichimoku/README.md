# TF-11 — Ichimoku Cloud System Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-11`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 15-min and 1-h)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Complete trend system based on five lines. Full signal requires: TK bullish cross,
price above the cloud, Chikou Span above past price, and a bullish (green) cloud.
A simplified variant uses only the TK cross direction + price vs. cloud.

## Indicator Components

- **Tenkan-sen:** `(max_high(n1) + min_low(n1)) / 2`
- **Kijun-sen:** `(max_high(n2) + min_low(n2)) / 2`
- **Senkou Span A:** `(Tenkan + Kijun) / 2` displaced `n2` bars forward
- **Senkou Span B:** `(max_high(n3) + min_low(n3)) / 2` displaced `n2` bars forward
- **Chikou Span:** current close displaced `n2` bars backward

## Parameter Search Space

```
tenkan      : [7, 9, 10, 13]                        — 4 values
kijun       : [20, 22, 26, 30]                      — 4 values
senkou_b    : [44, 52, 60]                           — 3 values
signal_type : [full_signal, tk_cross, cloud_break]   — 3 values
timeframe   : [15min, 1h]                            — 2 values
```

Approximate combinations: ~288 (constraint: senkou_b ≈ 2×kijun preferred).

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
