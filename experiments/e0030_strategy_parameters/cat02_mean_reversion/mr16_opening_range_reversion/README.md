# MR-16 — Opening Range Mean Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-16`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

Fades failed breakouts of the session opening range: if price closes beyond
the opening-range high/low and then closes back inside the range within
`reversal_bars`, enter toward the opposite side of the range.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Session anchor | `london` = [08:00, 08:00+OR) EET; `ny` = [13:00, 13:00+OR) EET |
| Breakout + failure | Close beyond ORH/ORL, then close back inside within `reversal_bars` bars |
| Entry price | Close of the reversal-confirmation bar |
| Stop | `atr_stop_mult × ATR(14)` beyond the breakout bar's extreme |
| Target | `opposite_band` = opposite range boundary; `mid_range` = range midpoint |
| Max holding period (not specified) | Forced exit at end of trading day |
| Setups per day | One qualifying breakout+reversal per session per day; new signals ignored while in a position |

## Parameter Search Space

```
or_duration_min  : [5, 10, 15, 30]
reversal_bars    : [1, 2, 3]
target           : ["mid_range", "opposite_band"]
atr_stop_mult    : [0.5, 1.0, 1.5]
session          : ["london", "ny"]
timeframe        : [1min, 5min]
```

Total combinations: **288** (144 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (20)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). All
timestamps are EET per corpus convention (see AGENTS.md).

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 288 combos) + walk-forward | **8.8 s** end-to-end |

## Result (research)

**No edge found.** 0 / 288 combinations that clear the `≥ 50` trades filter
have positive Sharpe or PF > 1.0. Best: Sharpe −0.368 (PF 0.911, 1,779 trades)
at `or15m`, `reversal_bars=1`, `opposite_band` target, `atr_stop=1.0×`, NY
session, 5-min. NY session clearly beats London (avg Sharpe −1.58 vs −2.64);
`opposite_band` beats `mid_range` targeting (avg −1.55 vs −2.67); longer
opening ranges (30 min) are less bad than short ones (avg −1.52 at 30min vs
−2.81 at 5min); faster reversal confirmation (1 bar) beats waiting longer
(avg −1.81 at 1 bar vs −2.38 at 3 bars). Walk-forward is unstable — the
selected combo changes every window and only window 3's OOS is positive
(+0.244, PF 1.06). See [`RESULTS.md`](./RESULTS.md) for details.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (20 tests) and
`uv run ruff check` pass.
