# Roadmap — TF-11 Ichimoku Cloud

Follow the Python performance playbook in
[`../tf01_ema_crossover_python/ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md)
(Performance engineering section). Phases below mirror that template.

## Phase 0 — Python project setup (uv)
- [ ] `uv init --python 3.12` in this directory; pin Python version.
- [ ] `uv add numpy numba polars` (core compute + columnar IO).
- [ ] `uv add --dev pytest ruff`.
- [ ] `.gitignore` covers `.venv/`, `.numba_cache/`, and `outputs/`.
- [ ] Configure `pyproject.toml`: `[tool.pytest.ini_options] pythonpath=["."]`,
      `testpaths=["tests"]`; `[tool.ruff] target-version="py312"`.
- [ ] Set `NUMBA_CACHE_DIR=.numba_cache` so compiled kernels persist between runs.
- [ ] Sanity: `uv run ruff check` and `uv run pytest` succeed (empty suite ok).
- [ ] Copy/adapt modules from [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/)
      (`data.py`, resampling, grid driver patterns) — never cross-import at runtime.


## Phase 1 — Data loading
- [ ] Load all `EURUSD_<YEAR>.csv.gz` from `../../../../data/bars/EURUSD/`.
- [ ] Parse `;`-delimited format with EET timestamps (`%Y.%m.%d %H:%M:%S`).
- [ ] Return struct-of-arrays NumPy buffers (`ts: int64`, OHLCV `float64`), sorted
      ascending, duplicates dropped. Use Polars for CSV parsing; see
      [`../tf01_ema_crossover_python/data.py`](../tf01_ema_crossover_python/data.py).

## Phase 2 — Resampling
- [ ] Implement `resample(bars, minutes)` → aggregate 1-min to 15-min, 1-h.

## Phase 3 — Indicator(s): Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span
- [ ] Implement each indicator as Numba `@njit` kernels over `float64` arrays.
- [ ] Unit test against known reference values.

## Phase 4 — Backtest engine
- [ ] Signal logic specific to TF-11 Ichimoku Cloud.
- [ ] One position at a time; ATR-based stop; fixed R:R target or indicator-based exit.
- [ ] Include spread cost: 0.00008 (0.8 pip) per round-trip.
- [ ] Return `(sharpe, profit_factor, max_drawdown_r, total_return, n_trades)` from a
      Numba `@njit(cache=True)` `backtest_core(...)`.

## Phase 5 — Parameter grid search
- [ ] Build full parameter grid from `README.md` search space.
- [ ] Parallelise grid search with `@njit(parallel=True)` and `numba.prange`.
- [ ] Write all rows to `outputs/results.csv`.

## Phase 6 — Walk-forward validation
- [ ] Rolling windows: 18-year in-sample → 4-year out-of-sample.
- [ ] Run top combination from Phase 5 on each window.
- [ ] Write `outputs/walkforward.csv`.

## Phase 7 — Output reporting
- [ ] Extract top-10 by Sharpe into `outputs/top_params.json`.
- [ ] Print summary to stdout.
