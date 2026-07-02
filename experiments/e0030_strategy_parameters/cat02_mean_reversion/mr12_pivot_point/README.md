# MR-12 — Pivot Point Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-12`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

Classic pivot points (`P`, `R1`/`R2`, `S1`/`S2`) computed from the prior
day's or week's High/Low/Close, broadcast forward to every bar of the
following period. Fade the approach to S1/R1 (or the extended S2/R2),
targeting the central pivot P or the midpoint between the fade level and P.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Pivot period | `daily` = prior calendar day's H/L/C (epoch-day aligned); `weekly` = prior contiguous 7-day window's H/L/C, anchored to the Unix epoch — **not** calendar ISO weeks (documented simplification) |
| Touch definition | `close ≤ S1/S2 + touch_atr_thresh × ATR(14)` (long) / `close ≥ R1/R2 − touch_atr_thresh × ATR(14)` (short) |
| Target | `P` = central pivot; `mid_SR1_P` = midpoint between the fade level and P |
| Stop: "beyond S2/R2 + ATR buffer" | **Simplified** to `atr_stop_mult × ATR(14)` from entry — the same fixed-ATR-stop-from-entry convention used by every other MR strategy in this category, to keep the grid tractable and comparable. A stop pinned to the next pivot level out would vary wildly in distance depending on how wide that day's/week's range was, which would make `atr_stop_mult` mean something different at every entry — this simplification keeps risk normalization consistent |
| Max holding period (not specified) | Forced exit at 100 bars |

## Parameter Search Space

```
pivot_period     : ["daily", "weekly"]
fade_level       : ["S1/R1", "S2/R2"]
touch_atr_thresh : [0.25, 0.5, 0.75, 1.0]
target           : ["P", "mid_SR1_P"]
atr_stop_mult    : [0.5, 1.0, 1.5]
timeframe        : [5min, 15min]
```

Total combinations: **192** (96 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (12)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-02)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 192 combos) + walk-forward | **4.9 s** end-to-end |

## Result (research)

**No edge found, but the second-closest-to-breakeven result in this
category** (after MR-13's −0.012). 0 / 192 combinations that clear the `≥
50` trades filter have positive Sharpe or PF > 1.0. Best: Sharpe −0.013 (PF
0.996, 1,917 trades) at `weekly` pivots, `S2/R2` fade, `touch=0.25`,
`mid_SR1_P` target, `atr_stop=1.5×`, 15-min. Weekly pivots clearly beat
daily (avg Sharpe −0.87 vs −1.87); the extended `S2/R2` levels beat `S1/R1`
(avg −1.05 vs −1.69) — consistent with the instrument-suitability note in
the strategy doc favoring institutional-participation levels, since weekly
levels persist longer and are more widely watched; wider ATR stops help
(avg −0.83 at 1.5× vs −2.13 at 0.5×). Walk-forward is genuinely mixed:
windows 1–3 select a `weekly S2/R2` combo consistent with the full-history
best and are OOS-negative, but **window 4 is OOS-positive** (+0.559, PF
1.20, 362 trades). See [`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-07-02. `uv run pytest` (12 tests) and
`uv run ruff check` pass.
