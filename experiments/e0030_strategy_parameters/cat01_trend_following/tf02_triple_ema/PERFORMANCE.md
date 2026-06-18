# PERFORMANCE — TF-02 Triple EMA Alignment

Benchmark report for the Python implementation of TF-02 on EURUSD 2003–2025.

**Run date:** 2026-06-18
**Environment:** WSL2 Linux, Python 3.13, Numba 0.65, NumPy 2.4, Polars 1.41

---

## End-to-end timing

| Stage | Duration |
|---|---|
| Load 8,490,235 1-min bars | **2.6 s** |
| Resample 5-min + cache indicators | **1.06 s** |
| Resample 15-min + cache indicators | **0.07 s** |
| Full grid 5-min (360 combos) | **2.57 s** |
| Full grid 15-min (360 combos) | **0.29 s** |
| Walk-forward (4 windows, IS-only re-opt) | included in total |
| **End-to-end** | **10.0 s** |

First run includes one-time Numba JIT compilation (~1–2 s); subsequent runs
reuse kernels from `.numba_cache/`.

---

## Grid scale

| Item | Value |
|---|---|
| Valid EMA triples per timeframe | 60 |
| Pullback options | 2 |
| ATR multipliers | 3 |
| Combinations per TF | 360 |
| Timeframes | 2 (5-min, 15-min) |
| **Total combinations** | **720** |
| 5-min resampled bars | 1,698,048 |
| 15-min resampled bars | 566,016 |

---

## Techniques applied

Same Python performance playbook as
[`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/):

1. **Polars** multithreaded CSV load → NumPy struct-of-arrays (no DataFrames in hot loops).
2. **Numba `@njit`** resampling and indicator kernels (`cache=True`).
3. **Precomputed EMA cache** — all unique periods (3, 5, 8, 9, 13, 20, 21, 34, 50, 55, 89)
   in one 2-D matrix per timeframe.
4. **`@njit(parallel=True)` + `prange`** over the 360-combo grid per timeframe.
5. **Walk-forward slicing** via `np.searchsorted` on cached arrays (no per-window
   indicator recomputation).

---

## Comparison to TF-01 Python

| Metric | TF-01 | TF-02 |
|---|---|---|
| Grid size | 3,150 | 720 |
| End-to-end | 12.7 s | **10.0 s** |
| Backtest kernel | 2-EMA crossover | 3-EMA alignment + pullback |

TF-02 is faster end-to-end despite a more complex per-bar state machine because
the grid is ~4× smaller.

---

## Distribution snapshot (full history)

| Statistic | Value |
|---|---|
| Combinations with Sharpe > 0 | 0 / 720 |
| Combinations with PF > 1.0 | 0 / 720 |
| Best Sharpe | −0.1705 |
| Worst Sharpe | −15.4692 |
| Mean Sharpe (5-min) | −7.14 |
| Mean Sharpe (15-min) | −1.83 |
| Mean Sharpe (pullback=mid) | −5.55 |
| Mean Sharpe (pullback=slow) | −3.42 |

See [`RESULTS.md`](./RESULTS.md) for the full research conclusion.
