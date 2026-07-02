# MR-15 — DeMarker Oscillator Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-15`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

DeMarker compares bar-to-bar High/Low deltas to measure demand vs. supply on
a `[0, 1]` scale. Fades extremes: long when DeMarker crosses below
`oversold_thresh`, short when it crosses above `overbought_thresh`, exiting
when DeMarker crosses back through `exit_level` (0.50).

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| DeMarker formula | `DeMax/(DeMax+DeMin)`, rolling means over `period` bars, as specified |
| Exit: DeMarker crosses back through `exit_level` | Implemented as specified |
| Stop | `atr_stop_mult × ATR(14)` from entry, gated by a realistic `ATR_FLOOR = 1e-6` (see mr09/mr14/mr20 for why) |
| Max holding period (not specified) | Forced exit at 100 bars |

## Parameter Search Space

```
demarker_period   : [5, 10, 14, 20]
oversold_thresh   : [0.05, 0.10, 0.15, 0.20]
overbought_thresh : [0.95, 0.90, 0.85, 0.80]
exit_level        : [0.50]
atr_stop_mult     : [0.75, 1.0, 1.5]
timeframe         : [5min, 15min]
```

Total combinations: **384** (192 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (16)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-02)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 384 combos) + walk-forward | **5.2 s** end-to-end |

## Result (research)

**A small, real full-history cluster; walk-forward IS is strongly positive
but OOS still fails.** 6 / 384 combinations clear positive Sharpe and PF >
1.0 (sanity-checked clean — no numerical artifacts), all at the longest
period (`demarker=20`), extreme thresholds (0.05/0.95 or 0.10/0.95), 15-min.
Best: Sharpe **+0.184**, PF **1.21**, 218 trades. Longer periods are
consistently less bad (avg Sharpe −0.85 at period 20 vs −7.00 at period 5);
15-min beats 5-min heavily (avg −1.36 vs −4.84). Walk-forward selects the
same `dem20/os0.05/ob0.95` family in all 4 windows with **strongly positive
IS Sharpe** (+0.25 to +0.44) — the best IS Sharpe found in this category so
far — but OOS is negative in all 4 windows (−0.09 to −1.02), and OOS trade
counts are thin (35–164). See [`RESULTS.md`](./RESULTS.md) for the full
analysis.

## Status

Complete. Run date: 2026-07-02. `uv run pytest` (16 tests) and
`uv run ruff check` pass.
