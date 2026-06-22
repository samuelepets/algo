# TF-04 — MACD + 200 EMA Trend Filter Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-04`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

The 200-period EMA defines the dominant trend (price above = bull regime).
MACD crossovers are only traded in the direction of the 200 EMA, eliminating
the majority of counter-trend false signals.

## Implementation Semantics

Same backtester conventions as TF-01/TF-02/TF-03 (one position at a time, entries at
bar close, stop checked before target intrabar, P&L in R units, spread `0.00008`).

| Spec (strategies doc) | This implementation |
|---|---|
| Trend filter | `EMA(trend_ema)` on the entry timeframe; long only if `close > trend`, short only if `close < trend` |
| MACD entry | MACD line crosses above its signal line (long); reversed for short |
| ATR stop | Static intrabar stop at `entry ∓ atr_mult × ATR(14)` |
| Target | Fixed 2:1 reward-to-risk (`RR_RATIO = 2.0`) |
| EMA(21/34) trailing exit | **Not implemented** — replaced by the opposite-MACD-crossover exit |

Valid combinations: **432** (216 per timeframe). The `~648` figure in the original
spec assumed a third timeframe (1 h); this experiment uses the two timeframes listed
in the grid below (5-min, 15-min). Min trades filter: `≥ 50`.

## Parameter Search Space

```
trend_ema    : [100, 150, 200, 250]    — 4 values
macd_fast    : [8, 10, 12]            — 3 values
macd_slow    : [21, 26, 30]           — 3 values
macd_signal  : [7, 9]                 — 2 values
atr_stop_mult: [1.0, 1.5, 2.0]       — 3 values
timeframe    : [5min, 15min]          — 2 values
```

Approximate combinations: ~648.

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
| **End-to-end** | **7.6 s** |

See console output from `uv run python main.py` for per-phase breakdown.

## Expected Result (research)

**No edge found on full history** — all 432 combinations are net-losing. Best Sharpe -2.35. All 4 OOS windows are negative.
See [`RESULTS.md`](./RESULTS.md) for the full analysis and cross-strategy
comparison card.

## Status

Complete. Run date: 2026-06-22. `uv run pytest` and `uv run ruff check` pass.
Full-history parameter search completed; outputs in `outputs/` (gitignored).
