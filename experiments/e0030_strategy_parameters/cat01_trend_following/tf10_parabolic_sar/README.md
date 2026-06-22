# TF-10 — Parabolic SAR Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-10`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Parabolic SAR is an always-in stop-and-reverse system. A dot below price = bull
trend; above price = bear trend. Flip of dot position triggers entry and acts as
the trailing stop. Tested both as a standalone system and as an exit-only
mechanism for EMA-entry signals.

## Indicator

```
SAR[n] = SAR[n-1] + AF × (EP - SAR[n-1])
AF starts at af_start, increments by af_step on each new extreme, capped at af_max
```

## Implementation Semantics

Same backtester conventions as the rest of the family (entries at bar close, stop
checked first intrabar, P&L in R units, spread `0.00008`). SAR is the trailing stop
(indicator-as-stop family); P&L is normalised by the initial SAR distance.

| Spec (strategies doc) | This implementation |
|---|---|
| `mode = standalone` | Enter on a SAR flip (red→green long, green→red short) at bar close |
| `mode = exit_only` | Enter on an EMA(9/21) crossover, **only** when the SAR already supports the direction (so the trailing stop is valid) |
| Trailing stop / initial risk R | The SAR dot; `R = |entry − SAR at entry|` |
| Exit | SAR touched intrabar, or a SAR flip against the position |
| `filter` mode (spec) | **Not implemented** — the stub grid lists only `standalone` and `exit_only` |

Valid combinations: **192** (96 per timeframe) — the full product of the value sets
below. (The `~240` figure in the original stub was a rough estimate.) Min trades
filter: `≥ 50`.

## Parameter Search Space

```
af_start : [0.01, 0.02, 0.03, 0.05]     — 4 values
af_step  : [0.01, 0.02, 0.03]           — 3 values
af_max   : [0.10, 0.15, 0.20, 0.30]    — 4 values
mode     : [standalone, exit_only]      — 2 values
timeframe: [5min, 15min]               — 2 values
```

Approximate combinations: ~240.

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
