# TF-05 — EMA Crossover + RSI Momentum Filter Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-05`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

EMA fast/slow crossover as primary signal, gated by an RSI threshold filter:
long only when RSI > threshold (e.g. > 55), short only when RSI < inverse
threshold. Eliminates crossovers that occur during low-momentum conditions.

## Implementation Semantics

Same backtester conventions as TF-01/TF-02 (one position at a time, entries at bar
close, stop checked before target intrabar, P&L in R units, spread `0.00008`).

| Spec (strategies doc) | This implementation |
|---|---|
| EMA crossover | `EMA(fast)` strictly crosses `EMA(slow)` (long up-cross; short down-cross) |
| RSI filter | Wilder RSI(`rsi_period`); long requires `rsi > rsi_long`, short `rsi < rsi_short` |
| RSI thresholds | Searched as symmetric pairs `(long, short)`: (50,50), (52,48), (55,45), (57,43) |
| ATR stop | Static intrabar stop at `entry ∓ atr_mult × ATR(14)` |
| Target | Fixed 2:1 reward-to-risk (`RR_RATIO = 2.0`) |
| Exit | Stop, target, or the opposite EMA crossover |

Pairing the RSI thresholds (rather than the full 4×4 product) yields the **1,536**
combinations cited below (768 per timeframe; `slow_ema > fast_ema` always holds for
these ranges). Min trades filter: `≥ 50`.

## Parameter Search Space

```
fast_ema         : [5, 7, 9, 12]          — 4 values
slow_ema         : [18, 20, 21, 26]        — 4 values
rsi_period       : [7, 10, 14]            — 3 values
rsi_long_thresh  : [50, 52, 55, 57]       — 4 values
rsi_short_thresh : [50, 48, 45, 43]       — 4 values
atr_stop_mult    : [0.75, 1.0, 1.5, 2.0] — 4 values
timeframe        : [1min, 5min]           — 2 values
```

Approximate combinations: ~1,536.

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
| **End-to-end** | **118 s** (sequential grid — parallel search OOM on 1-min bars) |

> `uv run python main.py` crashes (exit 138) during the 1-min parallel grid; the
> validation run used sequential `_eval_single` over all 1,536 combinations plus
> walk-forward. Re-run with a sequential driver if needed.

## Expected Result (research)

**No edge found on full history** — all 1,536 combinations are net-losing. Best
Sharpe −4.00. All four walk-forward OOS windows are negative. See
[`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-06-22. `uv run pytest` and `uv run ruff check` pass.
Full-history parameter search completed; outputs in `outputs/` (gitignored).
