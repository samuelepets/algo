# TF-03 — MACD Line/Signal Crossover Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-03`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

MACD line (EMA_fast − EMA_slow) crossing above its signal line (EMA of MACD)
signals bullish momentum acceleration. Optional zero-line filter: only take
longs when MACD > 0, shorts when MACD < 0.

## Implementation Semantics

Maps the strategy prose to a concrete, testable engine aligned with the TF-01/TF-02
Python backtester conventions (one position at a time, entries at bar close, stop
checked before target intrabar, P&L in R units, spread `0.00008`).

| Spec (strategies doc) | This implementation |
|---|---|
| MACD line | `EMA(fast) − EMA(slow)`, computed from a shared EMA cache |
| Signal line | `EMA(macd_line, signal)`, seeded by SMA of the first `signal` valid MACD values |
| Long entry | MACD crosses above signal (`macd[i-1] ≤ signal[i-1]` and `macd[i] > signal[i]`); short reversed |
| Zero-line filter | If on, long requires `macd > 0`, short requires `macd < 0` |
| ATR stop | Static intrabar stop at `entry ∓ atr_mult × ATR(14)` |
| Fixed R:R target | 2:1 reward-to-risk (`RR_RATIO = 2.0`, not grid-searched) |
| Opposite-crossover exit | Closed at bar close when the MACD/signal cross reverses |
| Histogram-shrink exit | **Not implemented** — replaced by the opposite-crossover exit above |

Total valid combinations: **720** (360 per timeframe; `slow_ema > fast_ema` always
holds for these ranges). Min trades filter: `≥ 50`.

## Parameter Search Space

```
fast_ema    : [5, 8, 10, 12]          — 4 values
slow_ema    : [21, 24, 26, 30, 35]    — 5 values
signal      : [7, 9, 12]              — 3 values
zero_filter : [true, false]           — 2 values
atr_stop_mult: [1.0, 1.5, 2.0]       — 3 values
timeframe   : [5min, 15min]           — 2 values
```

Approximate combinations: ~720.

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
