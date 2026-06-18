# TF-16 — Linear Regression Channel Trend Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-16`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Rolling OLS regression on close prices gives a trend line and residual standard
deviation σ. The channel (LinReg ± k×σ) defines where price is statistically
expensive or cheap. Trend-following entry: price bounces from the center line
upward (bull) or breaks above the upper channel (strong breakout).

## Indicator

```
For a window of n closes ending at bar i:
  slope, intercept = OLS fit
  LinReg[i]        = slope × (n-1) + intercept   (value at last bar)
  residuals        = close[j] - predicted[j]
  σ                = std(residuals)
  upper_band       = LinReg + k × σ
  lower_band       = LinReg - k × σ
```

## Parameter Search Space

```
linreg_period   : [30, 50, 75, 100, 150, 200]   — 6 values
channel_width_k : [1.0, 1.5, 2.0, 2.5]          — 4 values
entry_type      : [bounce_center, breakout_upper] — 2 values
atr_stop_mult   : [1.0, 1.5, 2.0]               — 3 values
timeframe       : [5min, 15min]                  — 2 values
```

Approximate combinations: ~288.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
