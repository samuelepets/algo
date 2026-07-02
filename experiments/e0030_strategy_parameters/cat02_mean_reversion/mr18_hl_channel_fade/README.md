# MR-18 — High-Low Channel Fade Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-18`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

Fade the edges of a rolling High/Low range, confirmed by a tight ATR/range-
width ratio (range-bound filter). Long entry near the range low, short entry
near the range high; target the range center or the opposite side.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Range high/low | `max(High, n)` / `min(Low, n)` over the `n` bars **before** the current bar (no lookahead) |
| Entry trigger | Long: `close ≤ center − entry_pct×(width/2)`; short: `close ≥ center + entry_pct×(width/2)` |
| Range filter | Only trade when `ATR(14)/width ≤ atr_range_ratio` |
| Stop | `atr_stop_mult × ATR(14)` from entry, gated by a realistic `ATR_FLOOR = 1e-6` |
| Target | `center` = range midpoint; `opposite_side` = opposite range boundary |
| Max holding period (not specified) | Forced exit at 100 bars |

## Parameter Search Space

```
range_period     : [20, 30, 50, 100]
entry_pct        : [0.80, 0.85, 0.90, 0.95]
atr_range_ratio  : [0.20, 0.30, 0.40]
target           : ["center", "opposite_side"]
atr_stop_mult    : [0.5, 1.0]
timeframe        : [5min, 15min]
```

Total combinations: **384** (192 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (13)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-02)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 384 combos) + walk-forward | **6.5 s** end-to-end |

## Result (research)

**No edge found.** 0 / 384 combinations that clear the `≥ 50` trades filter
have positive Sharpe or PF > 1.0. Best: Sharpe −0.246 (PF 0.963, 15,928
trades) at `range_period=100`, `entry_pct=0.95`, `atr_range_ratio=0.20`,
`opposite_side` target, `atr_stop=0.5×`, 15-min. `opposite_side` targeting
beats `center` (avg Sharpe −1.91 vs −3.00) — the full retrace captures more
of the move when it works; longer range periods are less bad (avg −1.25 at
100 vs −3.15 at 20); tighter entry (closer to the edge, `entry_pct=0.95`) is
less bad (avg −1.88 vs −2.97 at 0.80); 15-min beats 5-min (avg −1.33 vs
−3.57). Walk-forward IS Sharpe is mildly positive in windows 1–2 (+0.06 to
+0.19) but OOS is negative in all 4 windows. See [`RESULTS.md`](./RESULTS.md)
for details.

## Status

Complete. Run date: 2026-07-02. `uv run pytest` (13 tests) and
`uv run ruff check` pass.
