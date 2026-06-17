# TF-09 — VWAP Trend Bias Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-09`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

VWAP acts as a dynamic support/resistance level. In trend-following mode:
enter long when price pulls back to VWAP from above and bounces; trail the
stop just below VWAP. Exit when price closes below VWAP on two consecutive bars.

## Parameter Search Space

```
vwap_reset       : [daily, session]           — 2 values
entry_type       : [vwap_bounce, above_vwap]  — 2 values
band_width_sigma : [1.0, 1.5, 2.0]           — 3 values
atr_stop_mult    : [0.75, 1.0, 1.5]          — 3 values
timeframe        : [1min, 5min]               — 2 values
```

Approximate combinations: ~120.

> **Note:** VWAP is meaningful only when tick-volume is consistent.
> Include a data-quality check: skip bars/sessions where volume = 0.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
