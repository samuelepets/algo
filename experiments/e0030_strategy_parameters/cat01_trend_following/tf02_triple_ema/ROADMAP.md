# Roadmap — TF-02 Triple EMA Alignment

Follow the Python performance playbook in
[`../tf01_ema_crossover_python/ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md)
(Performance engineering section). Phases below mirror that template.

## Phase 0 — Python project setup (uv)
- [x] `uv init --python 3.12` in this directory; pin Python version.
- [x] `uv add numpy numba polars` (core compute + columnar IO).
- [x] `uv add --dev pytest ruff`.
- [x] `.gitignore` covers `.venv/`, `.numba_cache/`, and `outputs/`.
- [x] Configure `pyproject.toml`: `[tool.pytest.ini_options] pythonpath=["."]`,
      `testpaths=["tests"]`; `[tool.ruff] target-version="py312"`.
- [x] Set `NUMBA_CACHE_DIR=.numba_cache` so compiled kernels persist between runs.
- [x] Sanity: `uv run ruff check` and `uv run pytest` succeed (11 tests pass).
- [x] Copy/adapt modules from [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/)
      (`data.py`, resampling, grid driver patterns) — never cross-import at runtime.


## Phase 1 — Data loading
- [x] Load all `EURUSD_<YEAR>.csv.gz` from `../../../../data/bars/EURUSD/`.
- [x] Parse `;`-delimited format with EET timestamps (`%Y.%m.%d %H:%M:%S`).
- [x] Return struct-of-arrays NumPy buffers (`ts: int64`, OHLCV `float64`), sorted
      ascending, duplicates dropped. Use Polars for CSV parsing; see `data.py`.

## Phase 2 — Resampling
- [x] Implement `resample(bars, minutes)` → aggregate 1-min to 5-min, 15-min.

## Phase 3 — Indicator(s): EMA(fast), EMA(mid), EMA(slow) alignment + slope check
- [x] Implement each indicator as Numba `@njit` kernels over `float64` arrays.
- [x] Unit test against known reference values.

## Phase 4 — Backtest engine
- [x] Signal logic: bull/bear triple alignment (fast/mid/slow all ordered + positive/negative
      slopes); pullback rejection bar entry (low≤pb_ema AND close>pb_ema for longs; reversed
      for shorts); exit on ATR stop, 2:1 R:R target, or alignment break.
- [x] One position at a time; ATR-based stop; fixed 2:1 R:R target.
- [x] Include spread cost: 0.00008 (0.8 pip) per round-trip.
- [x] Return `(sharpe, profit_factor, max_drawdown_r, total_return, n_trades)` from
      Numba `@njit(cache=True)` `backtest_core(...)`.

## Phase 5 — Parameter grid search
- [x] Build full parameter grid from `README.md` search space (720 combinations).
- [x] Parallelise grid search with `@njit(parallel=True)` and `numba.prange`.
- [x] Write all rows to `outputs/results.csv`.

## Phase 6 — Walk-forward validation
- [x] Anchored windows from 2003: 12-year IS → 4-year OOS (same 4 windows as tf01).
- [x] IS-only grid re-optimisation per window; selected params evaluated on OOS.
- [x] Write `outputs/walkforward.csv`.

## Phase 7 — Output reporting
- [x] Extract top-10 by Sharpe into `outputs/top_params.json`.
- [x] Print summary to stdout.
- [x] Write [`RESULTS.md`](./RESULTS.md) and [`PERFORMANCE.md`](./PERFORMANCE.md).
