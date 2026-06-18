# TF-10 — Parabolic SAR Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-10`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Parabolic SAR is an always-in stop-and-reverse system. A dot below price = bull
trend; above price = bear trend. Flip of dot position triggers entry and acts as
the trailing stop. Tested both as a standalone system and as an exit-only
mechanism for EMA-entry signals.

## Indicator

```
SAR[n] = SAR[n-1] + AF × (EP - SAR[n-1])
AF starts at af_start, increments by af_step on each new extreme, capped at af_max
```

## Parameter Search Space

```
af_start : [0.01, 0.02, 0.03, 0.05]     — 4 values
af_step  : [0.01, 0.02, 0.03]           — 3 values
af_max   : [0.10, 0.15, 0.20, 0.30]    — 4 values
mode     : [standalone, exit_only]      — 2 values
timeframe: [5min, 15min]               — 2 values
```

Approximate combinations: ~240.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
