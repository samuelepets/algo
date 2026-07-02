# MR-09 — Price/EMA Distance (Rubber Band) Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-09`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min, 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`tf01_ema_crossover_python/`](../../cat01_trend_following/tf01_ema_crossover_python/)
performance conventions and using the shared `algo_shared` library.

## Strategy Summary

When price deviates from an EMA by more than `distance_thresh` ATR units, the
strategy fades the move back toward the EMA. `Distance = (Close - EMA) /
ATR(atr_period)`; long when `Distance < -distance_thresh`, short when
`Distance > +distance_thresh`. Two exit-target variants: `ema` (the
dynamically-updated EMA value) and `half_distance` (a fixed price level, half
the entry-bar distance back toward the EMA). An optional ADX filter restricts
entries to non-trending regimes.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Distance signal | `(Close - EMA) / ATR(atr_period)`, same `atr_period` reused for signal and stop as specified |
| `exit_target="ema"` | Dynamically-updated EMA value each bar (spec explicitly allows this simpler variant) |
| `exit_target="half_distance"` | Fixed target computed at entry: `entry_price - dist_price_at_entry / 2` |
| No `max_hold_bars` in grid | Fixed forced-exit safety net, `FORCED_EXIT_BARS = 100`, applied uniformly across all 3 timeframes (documented deviation from the "100 for 1/5min, 50 for 15min" suggestion — one constant is simpler and still generous relative to bar count at 15-min) |
| ADX < 20/25 filter | `adx_filter` grid dimension (0 = no filter), fixed `ADX(14)` |
| Stop | `atr_stop_mult × ATR(atr_period)` from entry, checked before the target/timeout exit within the same bar (stop priority) |
| Spread cost | `0.00008` (0.8 pip round-trip), consistent with MR-01/MR-07 |
| **ATR floor (deviation)** | EURUSD 1-min ATR can decay to near-zero (down to ~1e-37) during illiquid, fully-flat stretches (Wilder-smoothed run of zero true-range bars). Dividing by such a degenerate ATR — for both the distance signal and the stop distance — produced pathological R-multiples (Sharpe/PF/total-return outliers orders of magnitude off). Added `ATR_FLOOR = 1e-5` (≈0.1 pip): any bar with `ATR < ATR_FLOOR` is treated as no-signal/no-entry. Documented in `indicators.py`. |

## Parameter Search Space

```
ema_period       : [10, 20, 50, 100]                 — 4 values
atr_period       : [10, 14]                           — 2 values
distance_thresh  : [1.0, 1.5, 2.0, 2.5, 3.0]          — 5 values
exit_target      : [ema, half_distance]                — 2 values
adx_filter       : [none, <20, <25]                    — 3 values
atr_stop_mult    : [1.0, 1.5, 2.0]                     — 3 values
timeframe        : [1min, 5min, 15min]                 — 3 values
```

Total combinations: **2,160** (720 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests (19: 12 indicator + 7 backtest)
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost; compiled kernels
are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip it.

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Load 8,490,235 1-min bars | 2.7 s |
| Resample + cache indicators (all 3 TFs) | 2.3 s |
| Full grid, 1-min (720 combos) | 5.0 s |
| Full grid, 5-min (720 combos) | 0.8 s |
| Full grid, 15-min (720 combos) | 0.3 s |
| Walk-forward (4 windows) | included |
| **End-to-end** | **24.5 s** |

## Result (research)

**No edge found — only 4 of 2,160 combinations (0.2%) clear Sharpe > 0**, and
the best is marginal: `ema50/atr14 d2.5 exit=ema adx<20 stop1.5x` on 15-min,
Sharpe **0.1236**, profit factor **1.0196**, 4,265 trades over 23 years — a
breakeven-plus-fees result, not a real edge. The 1-min and 5-min timeframes
are strongly negative on average (mean Sharpe −23.6 and −2.9), and even
15-min averages negative (−0.98); only the least-frequent, widest-distance,
longest-EMA corner of the grid approaches breakeven. Walk-forward is
inconsistent: 2 of 4 windows are OOS-positive (Sharpe +0.24, +0.49) and 2 are
OOS-negative (−0.64, −0.69) using the same selected configuration — not a
stable, reproducible edge. See [`RESULTS.md`](./RESULTS.md) for the full
analysis, including the ATR-floor data-quality fix applied during
development.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (19 tests) and
`uv run ruff check` pass.
