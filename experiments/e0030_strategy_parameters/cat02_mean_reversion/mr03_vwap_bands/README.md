# MR-03 — VWAP Standard Deviation Bands Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-03`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`tf01_ema_crossover_python/`](../../cat01_trend_following/tf01_ema_crossover_python/)
performance conventions and using the shared `algo_shared` library.

## Strategy Summary

VWAP is the institutional session price anchor. This strategy computes a
session-anchored, volume-weighted VWAP plus a running (cumulative,
within-session) population standard deviation of `TypicalPrice - VWAP`, and
fades price when it closes beyond `entry_sigma` standard deviations from
VWAP, targeting either VWAP itself or a tighter `exit_sigma` band on the same
side (closer to VWAP).

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| VWAP reset: daily / London / NY session | `vwap_reset` grid dimension: `"daily"` resets at 00:00 EET, `"session_london"` at 08:00 EET, `"session_ny"` at 13:00 EET. Corpus timestamps are already EET-labelled naive epoch seconds (see `algo_shared.data`), so `(ts - anchor_offset) // 86400` gives a numba-friendly integer session-bucket id with no timezone conversion. |
| VWAP bands: `VWAP ± Nσ` of `(TypicalPrice − VWAP)` | Running/cumulative population std computed bar-by-bar within the session — at bar `i`, `dev[j] = TypicalPrice[j] - VWAP[j]` for all `j` in the current session up to and including `i`, accumulated via running sum/sum-of-squares (not a fixed-window rolling std). |
| Entry: first close beyond `Nσ` band | Implemented as "close beyond the band while flat" (only evaluated when no position is open), which is functionally the first qualifying close of any excursion since a new entry can only be considered after the prior trade has exited. |
| Exit: VWAP line or `±0.5σ` | `exit_sigma=0.0` → target is VWAP exactly. `exit_sigma>0` → target is the `±exit_sigma` band **on the same side as entry, closer to VWAP** (e.g. a long entered below the lower band targets `VWAP - exit_sigma·σ`, not the opposite/upper band) — a partial-retracement exit, per the task's dynamic "side toward VWAP" instruction. |
| Stop: price extends `0.5×ATR` beyond entry band | Stop is anchored to the **entry band level**, not the entry price: `stop = entry_band ∓ atr_stop_mult · ATR(14)`. Because the fill can already be slightly beyond the band when it triggers, the entry-to-stop distance is a small residual (`atr_stop_mult·ATR − overshoot`) rather than a fixed multiple of ATR; a `MIN_STOP_DIST = 1e-5` (~0.1 pip) floor rejects near-zero-risk trades that would otherwise blow up the R-multiple. |
| Volume caveat | EURUSD volume in this corpus is a synthetic tick-count-like series (not real traded volume), but is present, non-zero, and internally consistent — used directly for VWAP weighting, as instructed. |
| Forced-exit safety net | Not specified in the strategy doc; `MAX_HOLD_BARS = 500` (fixed, not a grid dimension) bounds worst-case holding time for pathological non-reverting excursions. |

## Parameter Search Space

```
vwap_reset       : [daily, session_london, session_ny]   — 3 values
entry_sigma      : [1.0, 1.5, 2.0, 2.5, 3.0]              — 5 values
exit_sigma       : [0.0, 0.5, 1.0]                        — 3 values
atr_stop_mult    : [0.5, 1.0, 1.5]                        — 3 values
timeframe        : [1min, 5min]                           — 2 values
```

Total combinations: **270** (135 per timeframe). VWAP + band caches are
precomputed once per `(timeframe, vwap_reset)` pair (6 caches total) and
reused across the `entry_sigma × exit_sigma × atr_stop_mult` sub-grid, same
caching pattern as mr01's `bb_period` cache. Spread cost: `0.00008` (0.8 pip
round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests (17)
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost; compiled kernels
are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip
it.

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Load 8,490,235 1-min bars | 2.9 s |
| Prepare caches (1-min + 5-min, 3 VWAP resets each) | ~1.0 s |
| Full grid, 1-min (135 combos) | 2.0 s |
| Full grid, 5-min (135 combos) | 0.4 s |
| Walk-forward (4 windows) | included |
| **End-to-end** | **11.2 s** |

Note: the 1-min timeframe with tight `entry_sigma` (1.0) produces very high
trade counts (up to ~577,000 over the 23-year history); `MAX_TRADES` is set
to `1,000,000` in `backtest.py` to avoid a buffer overflow.

## Result (research)

**No edge found.** All 270 grid combinations clear the `≥ 50` trades filter
(smallest count is 47,766 trades), and **none has a positive Sharpe ratio**
— the best is −1.277 (profit factor 0.845, 47,766 trades: `session_ny`
reset, `entry_sigma=3.0`, `exit_sigma=0.0`, `atr_stop_mult=1.5`, 5-min). The
1-min timeframe is dramatically worse (mean Sharpe −24.0 vs −9.95 at 5-min)
— the running-VWAP-std bands are noisy at 1-min resolution and the fixed
0.8-pip spread dominates the tiny sigma bands. Walk-forward confirms the
pattern: the IS-selected configuration (`session_ny e3.0s x0.0s stop1.5x
5m`) is OOS-negative in all 4 windows (Sharpe −3.94 to −0.59). See
[`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (17 tests) and
`uv run ruff check` pass.
