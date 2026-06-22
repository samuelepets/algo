# TF-07 — SuperTrend Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-07`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min, 5-min, 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

SuperTrend is an ATR-based trailing support/resistance line. When price closes
above the upper band, the indicator flips to bullish (green) — a long entry.
When price closes below the lower band, it flips to bearish — a short entry.
The active band serves as the trailing stop.

## Indicator

```
upper_band = HL2 - multiplier × ATR(atr_period)
lower_band = HL2 + multiplier × ATR(atr_period)
SuperTrend = upper_band when bullish; lower_band when bearish
```

Flip to bullish: `close[i] > lower_band[i-1]`
Flip to bearish: `close[i] < upper_band[i-1]`

## Implementation Semantics

Same backtester conventions as the rest of the family (one position at a time,
entries at bar close, stop checked before target intrabar, P&L in R units, spread
`0.00008`). SuperTrend belongs to the family whose **stop is the indicator itself**.

| Spec (strategies doc) | This implementation |
|---|---|
| Entry | On a SuperTrend flip (red→green long, green→red short) at the bar close |
| Trailing stop | The SuperTrend line, re-read each bar; intrabar exit when price touches it |
| Initial risk (R) | `|entry − SuperTrend line at entry|` (used to normalise P&L) |
| Target | `entry ± atr_target × ATR(atr_period)` (fixed ATR-multiple profit exit) |
| `htf_filter` | EMA(200) trend of the **last completed** higher-TF bar (15-min or 1 h), base-aligned; longs require the htf trend to be up, shorts down. `none` disables it |
| Exit | Stop touched, target reached, or a SuperTrend flip to the opposite side |

The SuperTrend is recomputed inside the Numba kernel from a per-`atr_period` ATR
cache (5 arrays) rather than materialising one array per grid cell — this keeps
the 1-min run (8.5 M bars × 810 cells) memory-light. Valid combinations: **810**
(270 per timeframe). Min trades filter: `≥ 50`.

> Note: the indicator block above quotes the spec's band labels verbatim; the code
> uses the conventional definition (`lower = HL2 − mult·ATR` as support in uptrends,
> `upper = HL2 + mult·ATR` as resistance in downtrends).

## Parameter Search Space

```
atr_period    : [5, 7, 10, 12, 14]       — 5 values
multiplier    : [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]  — 6 values
htf_filter    : [none, 15min, 1h]         — 3 values
atr_target    : [1.0, 1.5, 2.0]          — 3 values (ATR multiple for fixed target)
timeframe     : [1min, 5min, 15min]       — 3 values
```

Approximate combinations: ~810.

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The first
invocation pays a one-time Numba JIT compilation cost; compiled kernels are cached
on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip it.

## Performance (2026-06-22 run)

| Phase | Time |
|---|---|
| **End-to-end** | **33.7 s** |

## Expected Result (research)

**Mixed:** 615/810 Sharpe > 0. 4 of 4 oos windows positive.
See [`RESULTS.md`](./RESULTS.md) for the full analysis and cross-strategy comparison card.

## Status

Complete. Run date: 2026-06-22. `uv run pytest` and `uv run ruff check` pass.
Full-history parameter search completed; outputs in `outputs/` (gitignored).
