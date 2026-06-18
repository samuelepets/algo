# TF-20 — Elder Impulse System Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-20`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Each bar is color-coded: Green (EMA rising AND MACD histogram rising), Red (both
falling), Neutral (mixed). Enter long on first Green bar after a Neutral sequence;
enter short on first Red bar after Neutral. High selectivity — only trades on
bars with dual directional confirmation.

## Bar Color Logic

```
ema_rising  = EMA[i] > EMA[i-1]
hist_rising = MACD_Histogram[i] > MACD_Histogram[i-1]

color = Green   if ema_rising  && hist_rising
color = Red     if !ema_rising && !hist_rising
color = Neutral otherwise
```

## Parameter Search Space

```
ema_period      : [10, 13, 20, 26]               — 4 values
macd_fast       : [8, 10, 12]                    — 3 values
macd_slow       : [21, 24, 26]                   — 3 values
macd_signal     : [7, 9]                         — 2 values
entry_condition : [first_colored, any_colored]   — 2 values
exit_condition  : [first_neutral, opposite_color] — 2 values
atr_stop_mult   : [1.0, 1.5, 2.0]               — 3 values
timeframe       : [5min, 15min]                  — 2 values
```

Approximate combinations: ~1,728.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
