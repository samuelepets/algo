# TF-02 — Triple EMA Alignment Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-02`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Three EMAs (fast, mid, slow) must be fully aligned in ascending order with positive
slopes. Entries are taken on pullbacks to EMA(mid) or EMA(slow), confirmed by the
first rejection bar closing back beyond the pullback EMA.

## Implementation Semantics

This experiment maps the strategy prose to a concrete, testable engine aligned
with the TF-01 Python backtester conventions:

| Spec (strategies doc) | This implementation |
|---|---|
| Pullback to mid or slow EMA | `low ≤ pb_ema` and `close > pb_ema` (long); reversed for short |
| ATR stop | Intrabar static stop at entry (`entry ∓ atr_mult × ATR(14)`) |
| Fixed R:R target | 2:1 reward-to-risk (`RR_RATIO = 2.0`, not grid-searched) |
| Alignment break exit | `fast` crosses `slow` (closed at bar close) |
| Two consecutive closes below fast EMA | **Not implemented** — replaced by alignment-break exit above |
| Stop checked before target intrabar | Yes (same priority as TF-01) |

## Parameter Search Space

```
fast_ema     : [3, 5, 8, 9]                 — 4 values
mid_ema      : [13, 20, 21, 34]             — 4 values
slow_ema     : [34, 50, 55, 89]             — 4 values
constraint   : fast < mid < slow
pullback_ema : [mid, slow]                  — 2 values
atr_stop_mult: [1.0, 1.5, 2.0]             — 3 values
timeframe    : [5min, 15min]                — 2 values
```

Total valid combinations: **720** (360 per timeframe).
Spread cost: `0.00008` (0.8 pip round-trip). Min trades filter: `≥ 50`.

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

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost (~1–2 s); compiled
kernels are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs
skip it.

## Performance Target

| Stage | Measured (2026-06-18) |
|---|---|
| Load 8.49 M 1-min bars | **2.6 s** |
| Resample + cache indicators (both TFs) | **1.1 s** |
| Full grid (720 combos) | **2.9 s** |
| Walk-forward (4 windows) | included |
| **End-to-end** | **10.0 s** |

See [`PERFORMANCE.md`](./PERFORMANCE.md) for the full benchmark report.

## Expected Result (research)

**No edge found on full history** — all 720 combinations are net-losing, though
TF-02 is materially less bad than TF-01 (best Sharpe −0.17 vs −0.56). One
IS-selected OOS window (2015–2018) is mildly positive (+0.60 Sharpe) but three
of four OOS windows are negative. See [`RESULTS.md`](./RESULTS.md) for the full
analysis and cross-strategy comparison card.

## Status

Complete. Run date: 2026-06-18. `uv run pytest` (11 tests) and `uv run ruff check`
pass.
