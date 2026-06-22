# TF-06 — ADX + EMA Directional System Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-06`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

ADX > threshold confirms a trending market (avoids ranging conditions). The
directional indicators +DI and −DI, combined with price vs. EMA, determine
direction. Only enter when ADX confirms trend strength.

## Implementation Semantics

Same backtester conventions as TF-01/TF-02 (one position at a time, entries at bar
close, stop checked before target intrabar, P&L in R units, spread `0.00008`).

| Spec (strategies doc) | This implementation |
|---|---|
| ADX / +DI / -DI | Wilder DMI (`adx_dmi`); +DI/-DI valid from `period`, ADX from `2·period−1` |
| Long entry | `ADX > threshold` AND direction AND `close > EMA(trend)`; short reversed |
| `di_cross = false` | Direction = level test (`+DI > -DI`) |
| `di_cross = true` | Direction = a fresh +DI/-DI cross on the current bar |
| ATR stop | Static intrabar stop at `entry ∓ atr_mult × ATR(14)` |
| Target | Fixed 2:1 reward-to-risk (`RR_RATIO = 2.0`) |
| Exit | Stop, target, or a directional flip (-DI rises above +DI for longs) |

Valid combinations: **432** (216 per timeframe). Min trades filter: `≥ 50`.

## Parameter Search Space

```
adx_period    : [10, 14, 20]               — 3 values
adx_threshold : [15, 20, 25, 30]           — 4 values
trend_ema     : [20, 50, 100]              — 3 values
di_cross      : [true, false]              — 2 values
atr_stop_mult : [1.0, 1.5, 2.0]           — 3 values
timeframe     : [5min, 15min]              — 2 values
```

Approximate combinations: ~432.

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
| **End-to-end** | **4.6 s** |

## Expected Result (research)

**No edge found on full history** — all 432 combinations net-losing. Best Sharpe -0.27. All 4 oos windows negative.
See [`RESULTS.md`](./RESULTS.md) for the full analysis and cross-strategy comparison card.

## Status

Complete. Run date: 2026-06-22. `uv run pytest` and `uv run ruff check` pass.
Full-history parameter search completed; outputs in `outputs/` (gitignored).
