# TF-05 — EMA Crossover + RSI Momentum Filter Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-05`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

EMA fast/slow crossover as primary signal, gated by an RSI threshold filter:
long only when RSI > threshold (e.g. > 55), short only when RSI < inverse
threshold. Eliminates crossovers that occur during low-momentum conditions.

## Parameter Search Space

```
fast_ema         : [5, 7, 9, 12]          — 4 values
slow_ema         : [18, 20, 21, 26]        — 4 values
rsi_period       : [7, 10, 14]            — 3 values
rsi_long_thresh  : [50, 52, 55, 57]       — 4 values
rsi_short_thresh : [50, 48, 45, 43]       — 4 values
atr_stop_mult    : [0.75, 1.0, 1.5, 2.0] — 4 values
timeframe        : [1min, 5min]           — 2 values
```

Approximate combinations: ~1,536.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
