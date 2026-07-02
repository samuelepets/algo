# MR-07 — Williams %R Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-07`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`tf01_ema_crossover_python/`](../../cat01_trend_following/tf01_ema_crossover_python/)
performance conventions and using the shared `algo_shared` library.

## Strategy Summary

Williams %R measures where the close sits within the N-bar high-low range,
expressed as a negative percentage (0 = at the N-period high, −100 = at the
N-period low). Long entry fires when %R crosses below `oversold_thresh`
(deeply oversold); short entry fires when %R crosses above `overbought_thresh`
(deeply overbought). Exit on a cross back through the midline `exit_level`, an
ATR-based stop, or a bar-count timeout — whichever comes first.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Williams %R(n) | `(HH[n] − Close) / (HH[n] − LL[n]) × −100`, NaN when the n-bar range is ~0 |
| Long entry: %R crosses below `oversold_thresh` | Cross detection using `wr[i-1]` / `wr[i]` |
| Short entry: %R crosses above `overbought_thresh` | Mirror cross detection |
| Exit: %R crosses back through `exit_level` | Same `exit_level` value used for both the long (cross-above) and short (cross-below) exit |
| Exit: `max_hold_bars` timeout | Forced exit at bar close if reached first |
| Stop | `atr_stop_mult × ATR(14)` from entry (fixed 14-period ATR, independent of `wr_period`), checked before the %R/timeout exit within the same bar (stop priority) |
| Spread cost | `0.00008` (0.8 pip round-trip), consistent with MR-01 |

## Parameter Search Space

```
wr_period        : [5, 10, 14, 20]              — 4 values
oversold_thresh  : [-80, -85, -90]               — 3 values
overbought_thresh: [-20, -15, -10]               — 3 values
exit_level       : [-50, -40, -60]               — 3 values
atr_stop_mult    : [0.75, 1.0, 1.5]              — 3 values
max_hold_bars    : [5, 10, 15]                   — 3 values
timeframe        : [1min, 5min]                  — 2 values
```

Total combinations: **1,944** (972 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests (16: 10 indicator + 6 backtest)
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost; compiled kernels
are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip it.

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Load 8,490,235 1-min bars | 2.2 s |
| Resample + cache indicators (both TFs) | 1.0 s |
| Full grid, 1-min (972 combos) | 8.6 s |
| Full grid, 5-min (972 combos) | 1.5 s |
| Walk-forward (4 windows) | included |
| **End-to-end** | **36.4 s** |

## Result (research)

**No edge found.** All 1,944 combinations clear the `≥ 50` trades filter, and
**none has a positive Sharpe ratio or profit factor above 1.0**. The best
combination (`wr20`, oversold −90 / overbought −10, exit −50, stop 1.5×,
hold 15, 5-min) still has Sharpe −3.72 and PF 0.88, with 100,272 trades over
23 years — the extreme-threshold, wide-exit-band configurations that fire the
fewest (but still large) trade counts are the "least bad". The 1-min timeframe
is dramatically worse than 5-min (mean Sharpe −59.40 vs −8.85) because %R
crosses at 1-min resolution fire on nearly every noisy tick, generating trade
counts in the tens of thousands per combination and letting the fixed 0.8-pip
spread dominate. Walk-forward confirms the pattern: the IS-selected
configuration in all 4 windows is deeply OOS-negative (Sharpe −5.42 to
−8.44, PF 0.78–0.85). See [`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (16 tests) and
`uv run ruff check` pass.
