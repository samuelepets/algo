# TF-14 — Hull Moving Average (HMA) Trend Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-14`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 1-min and 5-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

HMA = `WMA(2×WMA(n/2) − WMA(n), sqrt(n))`. Its reduced lag compared to EMA/SMA
makes it suitable for 1-min bar trading. Signal is based on HMA slope change
(two consecutive bars of same slope) or HMA crossover with a slower HMA.

## Indicator

```
WMA(values, period) = Σ(w_i × v_i) / Σ(w_i)  where w_i = i (linear weights)
HMA(n) = WMA(2×WMA(n/2) − WMA(n),  floor(sqrt(n)))
```

## Implementation Semantics

Same backtester conventions as the rest of the family (entries at bar close, stop
checked first intrabar, P&L in R units, spread `0.00008`). The smoothing length uses
`round(sqrt(n))`.

| Spec (strategies doc) | This implementation |
|---|---|
| `mode = slope` | Long when HMA(fast) rises for `slope_bars` consecutive bars and `close > HMA`; exit when the slope turns down |
| `mode = crossover` | Long on HMA(fast) crossing above HMA(slow); exit on the opposite cross |
| ATR stop | Static intrabar stop at `entry ∓ atr_stop_mult × ATR(14)` |
| Target | Fixed 2:1 reward-to-risk (`RR_RATIO = 2.0`) |

The grid is **de-duplicated by mode**: `slope` ignores `hma_slow`, `crossover`
ignores `slope_bars` and requires `hma_slow > hma_fast`. Valid combinations:
**204** (102 per timeframe; 45 slope + 57 crossover). The `~360` figure in the stub
counted the modes' parameters jointly. Min trades filter: `≥ 50`.

## Parameter Search Space

```
hma_fast     : [6, 9, 12, 16, 20]          — 5 values
hma_slow     : [20, 25, 36, 49]            — 4 values  (crossover variant)
mode         : [slope, crossover]           — 2 values
slope_bars   : [1, 2, 3]                   — 3 values  (confirmation bars)
atr_stop_mult: [1.0, 1.5, 2.0]            — 3 values
timeframe    : [1min, 5min]                — 2 values
```

Approximate combinations: ~360 (slope mode uses only `hma_fast`; crossover uses both).

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
| **5-min grid + walk-forward** | **≈ 7 s** |

> `uv run python main.py` and the 1-min `_eval_single` path abort (exit 138).
> Validation used sequential evaluation on the **5-min** grid only (102 combos).

## Expected Result (research)

**No edge on the 5-min grid** — best Sharpe −6.36, all 102 combos net-losing.
1-min timeframe not validated (kernel crash). See [`RESULTS.md`](./RESULTS.md).

## Status

Complete (5-min scope). Run date: 2026-06-22. `uv run pytest` and `uv run ruff check`
pass. Outputs in `outputs/` (gitignored).
