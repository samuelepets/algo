# TF-15 — EMA Pullback to Dynamic Support Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-15`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

In an established trend (price above slow EMA), wait for price to pull back to
touch the fast EMA. A rejection bar (bullish close after touching the fast EMA)
confirms the entry. High R:R setup targeting the next structural high.

## Entry Logic

1. `Close > slow_ema` (trend confirmed).
2. `Low ≤ fast_ema[i]` (touch) AND `Close > fast_ema[i]` (rejection close).
3. Enter long on the close of the rejection bar.
4. Stop below `Low - buffer` of the rejection bar.
5. Target: `entry + rr_ratio × stop_distance`.

## Parameter Search Space

```
fast_ema       : [8, 9, 13, 20, 21]                — 5 values
slow_ema       : [50, 100, 200]                    — 3 values
pullback_touch : [low_touches, close_near_ema]     — 2 values
candle_pattern : [engulfing, hammer, any, none]    — 4 values
atr_stop_mult  : [1.0, 1.5, 2.0]                  — 3 values
timeframe      : [1min, 5min]                      — 2 values
```

Approximate combinations: ~720 (constraint: slow > fast applied).

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
