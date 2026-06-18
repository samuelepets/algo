# TF-14 — Hull Moving Average (HMA) Trend Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-14`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

HMA = `WMA(2×WMA(n/2) − WMA(n), sqrt(n))`. Its reduced lag compared to EMA/SMA
makes it suitable for 1-min bar trading. Signal is based on HMA slope change
(two consecutive bars of same slope) or HMA crossover with a slower HMA.

## Indicator

```
WMA(values, period) = Σ(w_i × v_i) / Σ(w_i)  where w_i = i (linear weights)
HMA(n) = WMA(2×WMA(n/2) − WMA(n),  floor(sqrt(n)))
```

## Parameter Search Space

```
hma_fast     : [6, 9, 12, 16, 20]          — 5 values
hma_slow     : [20, 25, 36, 49]            — 4 values  (crossover variant)
mode         : [slope, crossover]           — 2 values
slope_bars   : [1, 2, 3]                   — 3 values  (confirmation bars)
atr_stop_mult: [1.0, 1.5, 2.0]            — 3 values
timeframe    : [1min, 5min]                — 2 values
```

Approximate combinations: ~360 (slope mode uses only `hma_fast`; crossover uses both).

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
