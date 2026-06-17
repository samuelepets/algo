# TF-17 — Donchian Channel Breakout Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-17`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min, 15-min, and 1-h)
**Implementation:** Rust binary (`cargo init`)

## Strategy Summary

Turtle-system heritage: enter long when price closes above the N-bar highest
high (entry channel); exit when price closes below the M-bar lowest low (exit
channel, M < N). A breakout above the entry channel signals sustained momentum.

## Indicator

```
upper_band[i] = max(High[i-entry_channel .. i-1])
lower_band[i] = min(Low[i-entry_channel .. i-1])
exit_upper[i] = max(High[i-exit_channel .. i-1])
exit_lower[i] = min(Low[i-exit_channel .. i-1])
```

Long entry: `Close > upper_band` (+ optional buffer × ATR).
Long exit: `Close < exit_lower`.

## Parameter Search Space

```
entry_channel : [10, 15, 20, 30, 40, 55]   — 6 values
exit_channel  : [5, 8, 10, 15, 20]          — 5 values
constraint    : exit_channel < entry_channel
buffer_atr    : [0.0, 0.1, 0.2]             — 3 values
timeframe     : [5min, 15min, 1h]           — 3 values
```

Approximate valid combinations: ~270.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## Status

Structure defined. Implementation pending.
