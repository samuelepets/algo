# MR-11 — Double Bollinger Band System Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-11`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

Uses two Bollinger Band sets sharing the same SMA center: an inner band fixed
at 1σ and an outer band at a grid-searched `outer_sigma` (1.5–2.5). Entry is
a fade when Close crosses beyond the outer band; the target is either the
inner band or the center SMA.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Inner band (1σ) | Fixed at `1.0σ`, not grid-searched |
| Outer band | `outer_sigma` grid dimension (1.5/2.0/2.5) |
| Exit: inner band or center SMA | `target` grid dimension |
| ADX filter | `adx_filter` grid dimension (0 = none, matching mr01 convention) |
| Stop | `atr_stop_mult × ATR(14)` from entry |
| Max holding period (not specified) | Forced exit at 50 bars (documented safety net) |

## Parameter Search Space

```
bb_period        : [14, 20, 30]
outer_sigma      : [1.5, 2.0, 2.5]
target           : ["inner_band", "center_sma"]
adx_filter       : [None, 20, 25]
atr_stop_mult    : [0.5, 1.0, 1.5]
timeframe        : [5min, 15min]
```

Total combinations: **324** (162 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (17)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 324 combos) + walk-forward | **3.4 s** end-to-end |

## Result (research)

**No edge found.** 0 / 324 combinations that clear the `≥ 50` trades filter
have positive Sharpe or PF > 1.0. Best: Sharpe −0.273 (PF 0.965, 6,350
trades) at `bb30/2.5σ`, `center_sma` target, `adx<20`, 15-min. Wider outer
bands help (avg Sharpe −2.15 at 2.5σ vs −5.92 at 1.5σ), and `center_sma` as
the target beats `inner_band` (avg −3.38 vs −4.57) — targeting the inner band
adds extra path risk without added edge. 15-min beats 5-min (avg −2.00 vs
−5.95). Walk-forward selects essentially the full-history-best region in
every window but is OOS-negative in all 4 (−0.29 to −0.56). See
[`RESULTS.md`](./RESULTS.md) for details.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (17 tests) and
`uv run ruff check` pass.
