# Roadmap — TF-01 EMA Crossover (Python parity port)

Ordered, incremental plan to re-implement the Rust sibling
[`../tf01_ema_crossover`](../tf01_ema_crossover) in **pure Python** while hitting
the **same order of magnitude** of runtime (~12–15 s in Rust; target ≤ ~60 s
end-to-end, goal 20–40 s). Each phase must leave the experiment runnable,
committable, and lint/test-clean. All code is Python, managed with uv.

The guiding principle throughout: **vectorize the wide work, JIT-compile the
path-dependent loops, parallelize across the grid, and never touch pandas/Python
objects inside a hot loop.** See [Performance engineering](#performance-engineering-the-python-playbook)
for the full rationale.

## Phase 0 — Python project setup (uv)

- [x] `uv init --python 3.12` in this directory; pin Python version.
- [x] `uv add numpy numba polars` (core compute + columnar IO).
- [x] `uv add --dev pytest ruff`.
- [x] `.gitignore` already covers `.venv/`, caches, and `outputs/`.
- [x] Configure `pyproject.toml`: `[tool.pytest.ini_options] pythonpath=["."]`,
      `testpaths=["tests"]`; `[tool.ruff] target-version="py312"`.
- [x] Set `NUMBA_CACHE_DIR=.numba_cache` (env or in `main.py`) so compiled
      kernels persist between runs and JIT cost is paid once.
- [x] Sanity: `uv run ruff check` and `uv run pytest` succeed (empty suite ok).

## Phase 1 — Data loading (`data.py`)

Goal: parity with the Rust loader, in **≤ ~10 s**, returning
**struct-of-arrays** NumPy buffers (not a DataFrame) so downstream kernels get
contiguous `float64`/`int64` arrays with zero per-row Python overhead.

- [x] `load_eurusd()` reads every `EURUSD_<YEAR>.csv.gz` (2003–2025) from
      `../../../../data/bars/EURUSD/`, path resolved relative to the repo root
      (no absolute paths), corpus strictly read-only. [2.3s]
- [x] Parse the `;`-delimited format with a **columnar reader** (Polars
      `read_csv`) — not row-by-row Python CSV.
- [x] **Timestamp policy parity:** parse the naive `%Y.%m.%d %H:%M:%S` label and
      convert to epoch seconds *as if UTC* (no real EET offset), exactly as the
      Rust `Bar` docs describe, so walk-forward year boundaries line up bit-for-bit.
- [x] Return arrays: `ts: int64`, `open/high/low/close/volume: float64`, sorted
      ascending by `ts`, duplicates dropped (first kept). **8,490,235** bars loaded.
- [x] `year_start_ts(year)` and `ts_range(ts, start, end)` helpers mirroring the
      Rust binary-search slice (`np.searchsorted` on the sorted `ts`).

## Phase 2 — Resampling (`data.py`)

- [x] `resample(arrays, minutes)`: OHLCV bucket aggregation
      (O=first, H=max, L=min, C=last, V=sum), bucket = `ts // (minutes*60) * (minutes*60)`.
- [x] Implemented as a single **Numba `@njit`** pass over the sorted arrays.
- [x] Validated counts vs. Rust: 5-min → **1,698,048** bars; 15-min → **566,016**.

## Phase 3 — Indicators (`indicators.py`)

Pure Numba `@njit` kernels operating on `float64` close/high/low arrays; bitwise
algorithmic parity with the Rust versions.

- [x] `ema(close, period)`: SMA seed at index `period-1`, EMA recurrence with
      `k = 2/(period+1)`; warm-up filled with `NaN`.
- [x] `atr(high, low, close, period)`: True Range + **Wilder smoothing**
      (`k = 1/period`), SMA seed at index `period-1`.
- [x] **Precompute & cache** every required EMA period once per timeframe into a
      2-D array `ema_matrix[period_idx, bar_idx]` (contiguous), plus a `period ->
      row` index map. Cache the single ATR(14) array.
- [x] Unit tests reproduce the Rust indicator tests (SMA-seed equality, EMA
      recurrence, flat-bars ATR ≈ 0).

## Phase 4 — Backtest engine (`backtest.py`)

The hot path. A path-dependent state machine **cannot** be naively vectorized
(intrabar stop/target checks + position state), so it is the prime Numba target.

- [x] `backtest_core(...)` as a single `@njit(cache=True)` function returning
      `(sharpe, profit_factor, max_drawdown_r, total_return, n_trades)`.
- [x] Reproduce Rust semantics exactly (warm-up, slope-confirmed entry, exit
      priority stop → target → opposite crossover, spread 0.00008, R-multiples).
- [x] Metrics parity: Sharpe annualized by trade frequency; profit factor;
      `max_drawdown_r` as absolute peak-to-trough of cumulative-R curve.
- [x] Preallocated trade scratch buffer (`MAX_TRADES = 200_000`).
- [x] Parity test: flat bars → 0 trades (`tests/test_backtest.py`).

## Phase 5 — Parameter grid search (`main.py`)

- [x] `build_grid(tf_min)` applies `slow_ema > fast_ema + 5` → 1,575 combos/TF.
- [x] Grid represented as NumPy int/float arrays + EMA row indices.
- [x] `search_range(...)`: `@njit(parallel=True)` with `numba.prange`.
- [x] Full 3,150-combo grid in **~3.7 s** (5-min ~3.05s, 15-min ~0.63s).

## Phase 6 — Walk-forward validation (`main.py`)

- [x] 4 anchored windows (IS starts 2003; OOS steps 2 years).
- [x] **IS-only selection:** full grid re-optimised per IS slice; best set
      evaluated unchanged on OOS. Selected params logged per window.

## Phase 7 — Output reporting & parity check

- [x] `outputs/results.csv`, `outputs/top_params.json`, `outputs/walkforward.csv`
      written with same columns and ordering as Rust.
- [x] Human-readable top-10 and walk-forward tables printed to stdout.
- [x] `tests/test_parity.py`: all 4 parity tests pass vs. Rust sibling outputs.
- [x] Timing recorded in [`PERFORMANCE.md`](./PERFORMANCE.md): **12.7 s**
      end-to-end (~1.0× Rust).

---

## Performance engineering — the Python playbook

The whole point of this experiment is to document **how** to get Rust-class
throughput from Python. The techniques, in priority order:

1. **JIT-compile the path-dependent hot loop (Numba `@njit`).** The backtest is
   inherently sequential (intrabar stop/target, carried position state), so a
   pure-Python `for` loop over ~0.5–1.7 M bars × 3,150 combos would be
   ~100–1000× too slow. Numba lowers the loop to LLVM native code, typically
   within ~1–3× of hand-written Rust for tight scalar arithmetic. Use
   `cache=True` to persist compiled kernels and `fastmath=True` only where it
   does not break parity.

2. **Parallelize across the grid (`numba.prange`, `parallel=True`).** The 3,150
   combinations are embarrassingly parallel and share read-only indicator
   buffers. `prange` is the direct analogue of Rust's `rayon::par_iter`, scales
   across all cores, and releases the GIL — no pickling/IPC overhead (unlike
   `multiprocessing`, which would have to ship the multi-hundred-MB arrays to
   each worker).

3. **Struct-of-arrays NumPy buffers, never DataFrames in the loop.** Keep
   `open/high/low/close/ts` as separate contiguous `float64`/`int64` arrays.
   This is cache-friendly, lets Numba type everything statically, and avoids
   per-access pandas/Python boxing. pandas/Polars are used only at the IO and
   reporting edges.

4. **Precompute and cache indicators once.** All EMAs (8 unique periods) and the
   single ATR(14) are computed once per timeframe and reused by both the full
   grid and every walk-forward window — exactly as the Rust `ema_cache` does.
   Pack EMAs into one 2-D matrix so the kernel indexes by row, avoiding dict
   lookups in the hot path.

5. **Columnar, multithreaded IO.** Loading 8.49 M rows across 23 gzipped CSVs
   dominates if done with Python's `csv` module. Use Polars `read_csv` (or
   PyArrow) for multithreaded parsing and fast string→datetime conversion, then
   hand raw NumPy arrays to the compute layer.

6. **Allocation discipline.** Preallocate the per-combo trade scratch buffer and
   the grid output columns; avoid Python `list.append` growth and per-iteration
   temporaries inside `@njit` functions.

7. **Slice, don't copy.** Walk-forward windows operate on `[s:e]` views of the
   cached arrays (`np.searchsorted` for boundaries), mirroring Rust's
   `partition_point` slicing — no per-window recomputation of indicators.

8. **Pay JIT warm-up once.** First call compiles; `cache=True` + a fixed
   `NUMBA_CACHE_DIR` amortize it across runs. Report timings *after* warm-up so
   the comparison to Rust is apples-to-apples.

### Fallbacks / contingencies

- If `prange` parallelism underperforms (e.g. oversubscription), fall back to a
  process pool over grid *shards* with arrays passed via shared memory
  (`multiprocessing.shared_memory`) — still zero-copy.
- If Numba proves awkward for any kernel, **Cython** or a small **`numpy`
  vectorized partial** (e.g. precomputing crossover/slope boolean masks outside
  the loop, leaving only the stop/target state machine sequential) are the next
  levers.
- If pure-Python tooling still misses the order-of-magnitude target after the
  above, document the gap in `PERFORMANCE.md` and profile before adding complexity.
  New experiments in this repo stay on Python; legacy Rust folders are not extended.

## Acceptance criteria

- **Numerical parity** with Rust met (see [README](./README.md#parity-criteria)).
- **Performance:** end-to-end within ~5× of the Rust ~12–15 s (target ≤ ~60 s,
  goal 20–40 s), measured after JIT warm-up, reported in the README.
- `uv run pytest` (incl. parity tests) and `uv run ruff check` are clean.

## Out of scope

- New strategy ideas, filters, or instruments (this is a faithful port).
- Re-litigating the research conclusion — *no edge* is inherited from the Rust
  sibling and confirmed via parity, not re-derived.
- Sharing code with other experiments (copy in, never import across experiments).
