# TF-09 — VWAP Trend Bias Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-09`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

VWAP acts as a dynamic support/resistance level. In trend-following mode:
enter long when price pulls back to VWAP from above and bounces; trail the
stop just below VWAP. Exit when price closes below VWAP on two consecutive bars.

## Implementation Semantics

Same backtester conventions as the rest of the family (one position at a time,
entries at bar close, stop checked first intrabar, P&L in R units, spread `0.00008`).

| Spec (strategies doc) | This implementation |
|---|---|
| VWAP | Anchored VWAP with volume-weighted std band (`VWAP ± sigma·std`) |
| `vwap_reset = daily` | Cumulative sums reset at UTC midnight |
| `vwap_reset = session` | Reset shifted to ~07:00 (London open, in the EET-labelled timestamps) |
| `entry_type = vwap_bounce` | Long: `low ≤ lower_band` and `close > lower_band` (bounce back toward VWAP); short reversed |
| `entry_type = above_vwap` | Long: `close` crosses up through `upper_band` (continuation); short reversed |
| Stop / initial risk R | `entry ∓ atr_stop_mult × ATR(14)` |
| Exit | ATR stop, or two consecutive closes back across VWAP (no fixed R:R target) |
| Zero-volume bars | VWAP falls back to typical price; near-flat sessions get zero band width |

Valid combinations: **72** (36 per timeframe) — the full product of the value sets
below. (The `~120` figure in the original stub was a rough overestimate.) Min trades
filter: `≥ 50`.

> **Note:** VWAP is meaningful only when tick-volume is consistent; bars with zero
> volume fall back to the typical price. EURUSD volume coverage is broadly consistent
> across 2003–2025 — interpret VWAP-dependent results with this caveat.

## Parameter Search Space

```
vwap_reset       : [daily, session]           — 2 values
entry_type       : [vwap_bounce, above_vwap]  — 2 values
band_width_sigma : [1.0, 1.5, 2.0]           — 3 values
atr_stop_mult    : [0.75, 1.0, 1.5]          — 3 values
timeframe        : [1min, 5min]               — 2 values
```

Approximate combinations: ~120.

> **Note:** VWAP is meaningful only when tick-volume is consistent.
> Include a data-quality check: skip bars/sessions where volume = 0.

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

## Status

Code complete: `data.py`, `indicators.py`, `backtest.py`, `main.py` and unit tests
implemented following the TF-02 Python template. `uv run ruff check` and
`uv run pytest` pass. The full-history parameter search (`uv run python main.py`,
which writes `outputs/`) has not yet been run — pending.
