# TF-01 — EMA Crossover Parameter Search (Python parity port)

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-01`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min bars → resampled to 5-min and 15-min)
**Implementation:** Pure Python (uv-managed), JIT-compiled hot loops via Numba
**Sibling experiment:** [`../tf01_ema_crossover`](../tf01_ema_crossover) (Rust reference)

## Purpose

This experiment is a **pure-Python re-implementation** of the Rust sibling
[`tf01_ema_crossover`](../tf01_ema_crossover). It deliberately reproduces the
*same* strategy, the *same* parameter grid, the *same* execution semantics, and
the *same* walk-forward protocol. It is **not** a new research idea — the edge
question was already answered by the Rust run (*no edge found*). Instead, it
answers an **engineering** question:

> Can idiomatic, well-engineered Python reach the **same order of magnitude** of
> end-to-end runtime as the Rust implementation (~12–15 s), so that future
> experiments in this repo can stay in Python without paying a 100×+ speed
> penalty for the convenience?

The deliverable is therefore twofold:

1. **Numerical parity** — the Python results (`outputs/results.csv`,
   `top_params.json`, `walkforward.csv`) must match the Rust outputs within a
   tight tolerance (see [Parity criteria](#parity-criteria)).
2. **Performance parity** — total wall-clock within the same order of magnitude
   as Rust (target **≤ ~60 s** end-to-end after JIT warm-up; stretch goal
   20–40 s), demonstrating the Python performance playbook documented in
   [`ROADMAP.md`](./ROADMAP.md).

It follows the Python construction conventions established in
[`../../../../experiments/e0010_first_ensemble`](../../../../experiments/e0010_first_ensemble):
uv-managed environment, pinned dependencies, a data layer separated from
strategy/backtest logic, `data/` treated as read-only, unit tests, and `ruff`
linting. All committed artifacts are in English.

## Strategy Summary

Identical to the Rust sibling. A fast EMA crosses above/below a slow EMA to
signal a directional regime change. Entry is confirmed when both EMAs slope in
the same direction as the cross. Exits, whichever triggers first: a **fixed ATR
stop** set at entry (`entry ∓ atr_stop_mult × ATR(14)`, never moved afterward),
a fixed R:R target (`rr_ratio ×` the stop distance), or an opposite EMA
crossover (closed at bar close). The stop is static for the life of the trade
(no trailing logic). Intrabar exits assume the **stop is checked before the
target** within a bar, matching the Rust engine.

## Parameter Search Space

```
fast_ema     : [3, 5, 7, 8, 9, 10, 12, 13]          — 8 values
slow_ema     : [18, 20, 21, 25, 26, 30, 34, 50]      — 8 values
constraint   : slow_ema > fast_ema + 5
atr_stop_mult: [0.5, 1.0, 1.5, 2.0, 2.5]            — 5 values
rr_ratio     : [1.0, 1.5, 2.0, 2.5, 3.0]            — 5 values
timeframe    : [5min, 15min]                          — 2 values
```

Total combinations after the constraint: **3,150** (1,575 per timeframe).
Spread cost: `0.00008` (0.8 pip round-trip). Min trades filter: `≥ 50`.

## Expected Outputs

Byte-comparable (modulo float formatting) with the Rust sibling:

- `outputs/results.csv` — full grid: `fast_ema, slow_ema, atr_stop_mult, rr_ratio, tf_min, sharpe, profit_factor, max_drawdown_r, total_return, n_trades`
- `outputs/top_params.json` — top-10 by Sharpe
- `outputs/walkforward.csv` — per-window IS-selected params and IS/OOS metrics (`max_drawdown_r` in absolute R)

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit + parity tests
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost (~1–3 s); compiled
kernels are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs
skip it.

## Performance Target

| Stage | Rust reference | Python (measured) |
|---|---|---|
| Load 8.49 M 1-min bars | ~3.6 s | **2.3 s** |
| Resample + cache indicators | included | **0.34 s** |
| Full grid (3,150 combos) | ~3 s | **3.7 s** |
| Walk-forward (4 windows) | included | included |
| **End-to-end** | **~12–15 s** | **12.7 s** |

Parity with Rust is confirmed: all 3,150 combinations, top-10, and walk-forward
selections match within tolerance. See [`PERFORMANCE.md`](./PERFORMANCE.md) for
the full benchmark report.

## Parity Criteria

**Status: PASSED** (2026-06-17). `uv run pytest tests/test_parity.py` confirms:

- For every parameter combination, Python vs. Rust `n_trades` are **identical**,
  and `sharpe`, `profit_factor`, `total_return`, `max_drawdown_r` agree to
  **≤ 1e-6** relative tolerance.
- `top_params.json` lists the **same 10 combinations** in the same order.
- All 4 walk-forward windows select the **same IS-optimal parameters** and
  report matching IS/OOS metrics within tolerance.

## Expected Result (research)

Unchanged from the Rust sibling — **no edge found**. Pure EMA crossover with an
ATR stop and fixed R:R target is net-losing across all 3,150 combinations on
EURUSD; best full-history Sharpe ≈ −0.56 (15-min, slow MAs, wide stop, high
R:R), and all four IS-only walk-forward OOS windows are negative. This port's
research conclusion is inherited and verified by parity, not re-derived. See the
Rust sibling's [`RESULTS.md`](../tf01_ema_crossover/RESULTS.md) for the full
analysis.
