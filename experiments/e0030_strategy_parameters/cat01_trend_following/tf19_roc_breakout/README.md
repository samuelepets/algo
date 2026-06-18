# TF-19 — Momentum (ROC) Breakout Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-19`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Rate of Change measures price velocity directly. When ROC exceeds a positive
threshold, price is accelerating upward — an early trend signal with less lag
than MA crossovers. A longer-period ROC filter ensures the entry is not against
a broader move.

## Indicator

```
ROC(n)[i] = ((Close[i] - Close[i-n]) / Close[i-n]) × 100
```

## Parameter Search Space

```
roc_period      : [3, 5, 10, 15, 20, 30]     — 6 values
threshold_pct   : [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]  — 6 values
long_roc_filter : [none, 30, 60]              — 3 values  (longer-period ROC > 0)
holding_bars    : [5, 10, 20, 30]             — 4 values  (fixed holding period)
timeframe       : [1min, 5min]                — 2 values
```

Approximate combinations: ~864.

> **Note:** `threshold_pct` must be calibrated per instrument. EURUSD 5-min bars
> typically move 0.03%–0.15% per bar. The search space above is appropriate for
> EURUSD; adjust for XAUUSD or Crypto separately.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
