# TF-13 — EMA Ribbon Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-13`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

A ribbon of N EMAs with geometrically-spaced periods. Full alignment (all EMAs in
ascending order) + ribbon expanding (inter-EMA spacing increasing) signals a
strong trend. Entry on pullback to the fastest EMA.

## Alignment Score

`alignment = count of consecutive in-order pairs / (N-1)` — must meet threshold.

## Implementation Semantics

Same backtester conventions as the rest of the family (entries at bar close, stop
checked first intrabar, P&L in R units, spread `0.00008`).

| Spec (strategies doc) | This implementation |
|---|---|
| Ribbon periods | `round(ema_start · ema_ratio**k)` for `k = 0…count−1`, forced strictly increasing |
| Alignment | Fraction of adjacent pairs in order (bull: faster > slower) ≥ `alignment_pct` |
| Expansion | Fast−slow spacing wider than `expansion_bars` ago (bull) |
| Long entry | Aligned + expanding + pullback to fastest EMA (`low ≤ fastEMA` and `close > fastEMA`); short reversed |
| Stop | Fixed `entry ∓ 1.5 × ATR(14)` (this grid has no ATR-stop parameter) |
| Target | Fixed 2:1 reward-to-risk (`RR_RATIO = 2.0`) |
| Exit | Stop, target, or loss of ribbon alignment (spacing crosses zero) |

Valid combinations: **486** (243 per timeframe). Min trades filter: `≥ 50`.

## Parameter Search Space

```
ema_start      : [3, 5, 8]           — 3 values  (period of fastest EMA)
ema_ratio      : [1.5, 1.618, 2.0]   — 3 values  (multiplicative step)
ema_count      : [4, 5, 6]           — 3 values  (total EMAs)
alignment_pct  : [0.8, 0.9, 1.0]     — 3 values  (min fraction in-order)
expansion_bars : [2, 3, 5]           — 3 values  (confirmation window)
timeframe      : [5min, 15min]        — 2 values
```

Approximate combinations: ~486.

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
| **End-to-end** | **7.2 s** |

## Expected Result (research)

**No edge found on full history** — all 486 combinations net-losing. Best Sharpe -1.56. All 4 oos windows negative.
See [`RESULTS.md`](./RESULTS.md) for the full analysis and cross-strategy comparison card.

## Status

Complete. Run date: 2026-06-22. `uv run pytest` and `uv run ruff check` pass.
Full-history parameter search completed; outputs in `outputs/` (gitignored).
