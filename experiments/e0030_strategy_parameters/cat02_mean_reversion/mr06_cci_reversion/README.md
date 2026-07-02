# MR-06 — CCI Extreme Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-06`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`tf01_ema_crossover_python/`](../../cat01_trend_following/tf01_ema_crossover_python/)
performance conventions and using the shared `algo_shared` library.

## Strategy Summary

The Commodity Channel Index (CCI) measures how far the typical price
`(H+L+C)/3` deviates from its own rolling mean, scaled by the mean absolute
deviation (MAD) of that window. Readings beyond `+/- entry_threshold`
(100/125/150/200) mark statistically large deviations that are hypothesised to
revert on short intraday timeframes: `CCI < -entry_threshold` → go long;
`CCI > +entry_threshold` → go short, targeting a return of CCI toward zero
(`abs(CCI) <= exit_threshold`). An optional ADX filter restricts entries to
non-trending regimes.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| `CCI(n) = (TP - SMA(TP,n)) / (0.015 * MAD(n))` | Implemented exactly; `MAD(n)` at index `i` is computed against `SMA(TP,n)[i]` (that window's own mean) for every point in the same trailing window — the standard CCI convention, not a per-point rolling reference |
| Entry: `CCI > +threshold` → short, `CCI < -threshold` → long | `entry_threshold` grid dimension (100/125/150/200) |
| Exit: CCI returns to 0 | `exit_threshold` grid dimension (0/25/50); exits when `abs(CCI) <= exit_threshold` |
| Stop: CCI extends to +/-300 in adverse direction | Not used — the doc itself flags an ATR stop as a safer alternative, so risk is sized off `atr_stop_mult * ATR(14)` at entry (static stop), consistent with the other `cat02_mean_reversion` experiments |
| ADX < 20/25 filter | `adx_filter` grid dimension (0 = no filter, applied before entry-signal checks) |
| Max holding period | Not part of the published spec's grid. A fixed, non-grid-searched `MAX_HOLD_SAFETY = 100` bars forces an exit at close if neither the stop nor the CCI target has fired — a defensive cap on worst-case exposure, not a tunable parameter |
| Spread cost | `0.00008` (0.8 pip round-trip), consistent with the other cat02 experiments |

## Parameter Search Space

```
cci_period       : [10, 14, 20, 30]        — 4 values
entry_threshold  : [100, 125, 150, 200]    — 4 values
exit_threshold   : [0, 25, 50]             — 3 values
adx_filter       : [none, <20, <25]        — 3 values
atr_stop_mult    : [1.0, 1.5, 2.0]         — 3 values
timeframe        : [5min, 15min]           — 2 values
```

Total combinations: **864** (432 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `>= 50`.

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests (19)
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost; compiled kernels
are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip it.

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Load 8,490,235 1-min bars | 2.3 s |
| Resample + cache indicators, 5-min | 1.06 s |
| Resample + cache indicators, 15-min | 0.12 s |
| Full grid, 5-min (432 combos) | 1.63 s |
| Full grid, 15-min (432 combos) | 0.16 s |
| Walk-forward (4 windows, IS search + OOS eval) | included |
| **End-to-end (script-internal timer)** | **7.1 s** |
| Wall-clock (`time uv run python main.py`, incl. interpreter/uv startup) | 9.3 s |

## Result (research)

**No robust edge.** Of the 864 full-history combinations (all clear the
`>= 50` trades filter — the strategy trades frequently at these thresholds),
72 have a positive Sharpe ratio and the same 72 have profit factor > 1.0. The
best full-history combination (`cci_period=10, entry=200, exit=0, no ADX
filter, atr_stop=1.5x, 15-min`) reaches Sharpe **+0.5554**, PF **1.0935**,
over 9,013 trades — a real but modest positive number.

Walk-forward does not confirm it. Every one of the 4 windows shows a strong
**in-sample** Sharpe (0.73–0.90, PF 1.11–1.16 on the IS-selected combo), but
**out-of-sample** Sharpe is negative in 3 of 4 windows (−0.61, −0.13, −0.46)
and only marginally positive in the fourth (+0.07, PF 1.008 — statistically
indistinguishable from breakeven despite 2,661 trades). The mean OOS Sharpe
across all 4 windows is **−0.28**. This IS-strong / OOS-weak-or-negative
pattern is the textbook signature of in-sample overfitting rather than a
genuine, exploitable edge. The 15-min timeframe is clearly better than 5-min
(mean Sharpe −0.92 vs −3.87 across all 864 combos) — as with other
mean-reversion experiments in this category, 5-min trading is dominated by
the fixed 0.8-pip spread cost. See [`RESULTS.md`](./RESULTS.md) for the full
analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (19 tests) and
`uv run ruff check` pass.
