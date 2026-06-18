# TF-12 — Williams Alligator Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-12`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Three Smoothed Moving Averages (SMMA) with Fibonacci periods and forward offsets
model the "sleeping" (ranging) vs "awake" (trending) state. When Lips > Teeth >
Jaw (all fanning up) and price is above all lines, enter long on the awakening.

## Indicator Components

- **Jaw:** SMMA(jaw_period) shifted `jaw_shift` bars forward
- **Teeth:** SMMA(teeth_period) shifted `teeth_shift` bars forward
- **Lips:** SMMA(lips_period) shifted `lips_shift` bars forward

## Parameter Search Space

A global scale factor is applied to the canonical Fibonacci set
(periods: 5, 8, 13; shifts: 3, 5, 8):

```
scale_factor : [0.7, 0.85, 1.0, 1.15, 1.3]   — 5 values
               → periods = round([5,8,13] × scale)
               → shifts  = round([3,5,8]  × scale)
atr_stop_mult: [1.0, 1.5, 2.0]                — 3 values
timeframe    : [5min, 15min]                   — 2 values
```

Total combinations: ~30. Also test raw grid:

```
jaw_period   : [10, 13, 15]    teeth_period : [6, 8, 10]    lips_period : [3, 5, 7]
jaw_shift    : [6, 8, 10]      teeth_shift  : [4, 5, 6]     lips_shift  : [2, 3, 4]
```

Approximate total: ~150.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
