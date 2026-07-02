# MR-08 — Keltner Channel Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-08`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

Fade price when it moves outside an ATR-based Keltner Channel (`EMA ± k ×
ATR`), targeting the EMA center line. Two entry variants: `close_outside`
(bar closes beyond the band) and `wick_touch` (intrabar high/low touches the
band even if the close doesn't).

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Entry: close outside band | `entry_type="close_outside"`: `close[i]` beyond band |
| Entry: (not in doc, added dimension) | `entry_type="wick_touch"`: `high[i]`/`low[i]` beyond band |
| Exit: return to EMA center | Dynamically-updated EMA target |
| Stop | `atr_stop_mult × ATR(atr_period)` from entry |
| Max holding period (not specified) | Forced exit at 100 bars (documented safety net) |

## Parameter Search Space

```
ema_period      : [10, 20, 30]
atr_period      : [10, 14]
k_mult          : [1.0, 1.5, 2.0, 2.5, 3.0]
entry_type      : ["close_outside", "wick_touch"]
atr_stop_mult   : [0.5, 1.0, 1.5]
timeframe       : [5min, 15min]
```

Total combinations: **360** (180 per timeframe). Spread cost: `0.00008`
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
| Full grid (both TFs, 360 combos) + walk-forward | **3.1 s** end-to-end |

## Result (research)

**Weak full-history signal that does not survive walk-forward.** Unlike most
of this category, MR-08 has a real cluster of positive combinations: 41 / 360
combos clear PF > 1.0 with positive Sharpe, concentrated at `ema_period=30`,
`atr_period=10`, wide `k_mult` (2.5–3.0), `entry_type="close_outside"`,
15-min. Best: Sharpe **+0.201**, PF **2.12**, 15,697 trades over 23 years.
However, walk-forward IS-only selection picks a *different* region each
window (short `ema_period=10`, tight `k_mult=3.0`, 5-min) with negative IS
Sharpe from the start, and OOS is negative in all 4 windows. The full-history
"best" region is not stable/selectable from partial history — it looks like
a full-sample artifact rather than a genuine, exploitable edge. See
[`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (18 tests) and
`uv run ruff check` pass.
