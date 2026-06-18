# TF-03 — MACD Line/Signal Crossover Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-03`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

MACD line (EMA_fast − EMA_slow) crossing above its signal line (EMA of MACD)
signals bullish momentum acceleration. Optional zero-line filter: only take
longs when MACD > 0, shorts when MACD < 0.

## Parameter Search Space

```
fast_ema    : [5, 8, 10, 12]          — 4 values
slow_ema    : [21, 24, 26, 30, 35]    — 5 values
signal      : [7, 9, 12]              — 3 values
zero_filter : [true, false]           — 2 values
atr_stop_mult: [1.0, 1.5, 2.0]       — 3 values
timeframe   : [5min, 15min]           — 2 values
```

Approximate combinations: ~720.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
