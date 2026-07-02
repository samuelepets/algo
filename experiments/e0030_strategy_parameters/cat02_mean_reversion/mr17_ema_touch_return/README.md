# MR-17 — EMA Touch Return Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-17`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

In a non-trending regime (ADX below `adx_max`), enter toward the EMA when
price has moved more than `distance_thresh_atr` ATR units away and the
current bar shows a one-bar reversal back toward the EMA relative to the
prior close.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| "Reversal candle" (undefined in doc) | One-bar confirmation: `close[i] > close[i-1]` (long setup) / `close[i] < close[i-1]` (short setup), while the prior bar was beyond `distance_thresh_atr` ATR from EMA |
| Regime condition | ADX < `adx_max`, always active (no "None" option, unlike mr01's optional filter) |
| Exit: `ema_touch` | Dynamically-updated EMA target |
| Exit: `half_distance` | Entry price ± half the ATR-distance toward EMA |
| Stop | `atr_stop_mult × ATR(14)` from entry (ATR(14) fixed, not grid-searched) |
| Max holding period (not specified) | Forced exit at 100 bars (documented safety net) |

## Parameter Search Space

```
ema_period         : [10, 20, 50]
distance_thresh_atr: [0.5, 1.0, 1.5, 2.0]
adx_max            : [15, 20, 25]
atr_stop_mult      : [0.5, 1.0, 1.5]
exit_type          : ["ema_touch", "half_distance"]
timeframe          : [5min, 15min]
```

Total combinations: **432** (216 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (18)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 432 combos) + walk-forward | **3.3 s** end-to-end |

## Result (research)

**No edge found.** 0 / 432 combinations that clear the `≥ 50` trades filter
have positive Sharpe or PF > 1.0. Best: Sharpe −0.209 (PF 0.785, only 80
trades — near the trade-count floor) at `ema10`, `distance_thresh=2.0`,
`adx_max=15`, `atr_stop=1.0×`, `ema_touch` target, 15-min. Wider distance
thresholds are much less bad (avg Sharpe −2.18 at 2.0 ATR vs −9.93 at 0.5
ATR) and tighter ADX regime gates help (avg −3.73 at `adx_max=15` vs −7.10 at
25). Walk-forward IS Sharpe is close to zero in windows 1–3 (best +0.036 in
window 3, with only 52 trades) but every OOS window is negative, and trade
counts collapse to 14–24 in the later OOS windows — too few to draw
conclusions either way. See [`RESULTS.md`](./RESULTS.md) for details.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (18 tests) and
`uv run ruff check` pass.
