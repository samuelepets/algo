# TF-12 — Williams Alligator Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-12`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Three Smoothed Moving Averages (SMMA) with Fibonacci periods and forward offsets
model the "sleeping" (ranging) vs "awake" (trending) state. When Lips > Teeth >
Jaw (all fanning up) and price is above all lines, enter long on the awakening.

## Indicator Components

- **Jaw:** SMMA(jaw_period) shifted `jaw_shift` bars forward
- **Teeth:** SMMA(teeth_period) shifted `teeth_shift` bars forward
- **Lips:** SMMA(lips_period) shifted `lips_shift` bars forward

## Implementation Semantics

Same backtester conventions as the rest of the family (entries at bar close, stop
checked first intrabar, P&L in R units, spread `0.00008`). SMMA lines are computed
on the **median price** `(high + low) / 2` and shifted forward.

| Spec (strategies doc) | This implementation |
|---|---|
| Lines | `Jaw = SMMA(13·s)` shift `8·s`; `Teeth = SMMA(8·s)` shift `5·s`; `Lips = SMMA(5·s)` shift `3·s` (`s` = scale factor, values rounded) |
| Long entry | Lips crosses above Teeth AND Teeth > Jaw AND `close > Lips` (alligator awakens, fanned up); short reversed |
| ATR stop | Static intrabar stop at `entry ∓ atr_stop_mult × ATR(14)` |
| Target | Fixed 2:1 reward-to-risk (`RR_RATIO = 2.0`) |
| Exit | Stop, target, or an opposite Lips/Teeth cross (alligator falling asleep) |

This experiment implements the **scale-factor** parametrisation that the spec
recommends as the practical approach ("fix the ratios and search over a global
scaling factor"). Valid combinations: **30** (15 per timeframe). The alternative
raw period/shift grid (the `~150` figure) is not enumerated. Min trades: `≥ 50`.

## Parameter Search Space

A global scale factor is applied to the canonical Fibonacci set
(periods: 5, 8, 13; shifts: 3, 5, 8):

```
scale_factor : [0.7, 0.85, 1.0, 1.15, 1.3]   — 5 values
               → periods = round([5,8,13] × scale)
               → shifts  = round([3,5,8]  × scale)
atr_stop_mult: [1.0, 1.5, 2.0]                — 3 values
timeframe    : [5min, 15min]                   — 2 values
```

Total combinations: ~30. Also test raw grid:

```
jaw_period   : [10, 13, 15]    teeth_period : [6, 8, 10]    lips_period : [3, 5, 7]
jaw_shift    : [6, 8, 10]      teeth_shift  : [4, 5, 6]     lips_shift  : [2, 3, 4]
```

Approximate total: ~150.

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
