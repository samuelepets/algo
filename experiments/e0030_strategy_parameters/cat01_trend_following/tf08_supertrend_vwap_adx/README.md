# TF-08 — SuperTrend + VWAP + ADX Combo Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-08`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Triple-confirmation trend entry: SuperTrend (direction), VWAP (institutional
price anchor), and ADX (trend strength). All three must agree before entering.
Highest-conviction filter among the trend-following family.

## Entry Conditions

- **Long:** SuperTrend = bullish AND close > VWAP AND close > EMA(trend_ema) AND ADX > adx_threshold
- **Short:** SuperTrend = bearish AND close < VWAP AND close < EMA(trend_ema) AND ADX > adx_threshold

## Implementation Semantics

Same backtester conventions as the rest of the family (one position at a time,
entries at bar close, stop checked before target intrabar, P&L in R units, spread
`0.00008`). Stop is the SuperTrend line (indicator-as-stop family).

| Spec (strategies doc) | This implementation |
|---|---|
| Entry | First bar where the four conditions above are all true and no position is open |
| VWAP | Session VWAP with a daily (UTC-midnight) reset; falls back to typical price when volume is 0 |
| SuperTrend | Computed inside the kernel from a per-`st_atr` ATR cache |
| Trailing stop / initial risk R | The SuperTrend line; `R = |entry − line at entry|` |
| Target | `entry ± atr_target × ATR(st_atr)` |
| Exit | Stop touched, target reached, or a SuperTrend flip |

Valid combinations: **1,728** (864 per timeframe) — the full product of the value
sets below. (The `~576` figure in the original stub underestimated the product.)
Min trades filter: `≥ 50`.

> **Note:** VWAP requires volume > 0; bars with zero volume fall back to the typical
> price so the cumulative VWAP stays defined. EURUSD tick-volume coverage is broadly
> consistent across 2003–2025, but interpret VWAP-dependent results with this caveat.

## Parameter Search Space

```
st_atr        : [7, 10, 14]               — 3 values
st_mult       : [2.0, 2.5, 3.0, 3.5]     — 4 values
adx_period    : [10, 14]                  — 2 values
adx_threshold : [20, 25, 30]             — 3 values
trend_ema     : [20, 21, 50]             — 3 values
atr_target    : [1.5, 2.0, 2.5, 3.0]    — 4 values
timeframe     : [5min, 15min]            — 2 values
```

Approximate combinations: ~576.

> **Note:** VWAP requires volume > 0. Validate EURUSD volume data coverage
> before trusting VWAP-dependent results.

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
