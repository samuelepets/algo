# MR-01 — Bollinger Band Mean Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-01`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`tf01_ema_crossover_python/`](../../cat01_trend_following/tf01_ema_crossover_python/)
performance conventions and using the shared `algo_shared` library.

## Strategy Summary

Fade price when it closes outside a Bollinger Band (`SMA(period) ± mult × σ`),
targeting the middle SMA. An optional ADX filter restricts entries to
non-trending regimes. Two entry variants: `close_outside` (enter on the bar
that closes beyond the band) and `reentry` (enter on the first bar that closes
back inside the band after being outside).

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Entry: close outside band, or re-entry | Both variants implemented as `entry_type` grid dimension |
| ADX < 20/25 filter | `adx_filter` grid dimension (0 = no filter) |
| Exit: middle band (SMA) | Intrabar target at the SMA for the active period |
| Stop: prior extreme + 0.5× ATR | Static stop at entry, `atr_stop_mult × ATR(14)` |
| Max holding period | `max_hold_bars`, forced exit at bar close |
| Spread cost | `0.00008` (0.8 pip round-trip), consistent with cat01 |

## Parameter Search Space

```
bb_period      : [10, 14, 20, 30, 50]        — 5 values
bb_mult        : [1.0, 1.5, 2.0, 2.5, 3.0]   — 5 values
entry_type     : [close_outside, reentry]     — 2 values
adx_filter     : [none, <20, <25]             — 3 values
atr_stop_mult  : [0.5, 1.0, 1.5]              — 3 values
max_hold_bars  : [5, 10, 20, 30]              — 4 values
timeframe      : [5min, 15min]                — 2 values
```

Total combinations: **3,600** (1,800 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests (15)
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost; compiled kernels
are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip it.

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Load 8,490,235 1-min bars | 2.4 s |
| Resample + cache indicators (both TFs) | 1.2 s |
| Full grid, 5-min (1,800 combos) | 4.1 s |
| Full grid, 15-min (1,800 combos) | 0.8 s |
| Walk-forward (4 windows) | included |
| **End-to-end** | **17.2 s** |

## Result (research)

**No edge found.** Of the 3,456 combinations that clear the `≥ 50` trades
filter, **none has a positive Sharpe ratio** — the best is −0.153 (profit
factor 0.96). Only 6-trade outlier combinations (below the trade-count
threshold, statistically meaningless) show positive Sharpe/PF. The 5-min
timeframe is materially worse than 15-min (avg Sharpe −8.05 vs −2.61 across
valid combos) — high-frequency reversion trading is dominated by the fixed
0.8-pip spread cost. Walk-forward confirms the pattern: the IS-selected
configuration (`bb30/3.0x reentry adx<20 stop1.5x hold20 15m`) is OOS-negative
in all 4 windows (Sharpe −0.09 to −0.34). See [`RESULTS.md`](./RESULTS.md) for
the full analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (15 tests) and
`uv run ruff check` pass.
