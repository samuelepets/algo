# PERFORMANCE — TF-01 EMA Crossover (Python parity port)

Benchmark and parity report for the Python re-implementation vs. the Rust sibling
[`../tf01_ema_crossover`](../tf01_ema_crossover).

**Run date:** 2026-06-17
**Environment:** WSL2 Linux, Python 3.12, Numba 0.65, NumPy 2.4, Polars 1.41

---

## End-to-end timing

| Stage | Rust reference | Python (this run) |
|---|---|---|
| Load 8,490,235 1-min bars | ~3.6 s | **2.3 s** |
| Resample 5-min + cache indicators | included | **0.27 s** |
| Resample 15-min + cache indicators | included | **0.07 s** |
| Full grid 5-min (1,575 combos) | ~2.5 s | **3.05 s** |
| Full grid 15-min (1,575 combos) | ~0.5 s | **0.63 s** |
| Walk-forward (4 windows) | included | included in total |
| **End-to-end** | **~12–15 s** | **12.7 s** |

**Speed ratio:** ~1.0× (Python matches Rust, within measurement noise).

The Python port achieves the performance goal on the first implementation pass:
same order of magnitude, no 5× penalty, no need for Rust on this workload.

---

## Techniques that made the difference

1. **Numba `@njit(cache=True)`** on the backtest state machine — the path-dependent
   intrabar stop/target loop runs as native LLVM code.
2. **`numba.prange` (`parallel=True`)** over the 3,150-combo grid — direct analogue
   of Rust `rayon::par_iter`, GIL released, zero IPC overhead.
3. **Struct-of-arrays NumPy buffers** — no pandas in hot loops; contiguous
   `float64`/`int64` arrays passed straight into Numba.
4. **Precomputed indicator cache** — all 8 EMA periods + ATR(14) computed once
   per timeframe, reused by grid search and walk-forward slices.
5. **Polars columnar IO** — multithreaded gzip CSV parsing at ~3.7 M rows/s.
6. **Numba resample kernel** — single-pass bucket aggregation matching Rust
   bucket boundaries exactly.
7. **JIT cache on disk** (`.numba_cache/`) — compilation cost amortized after the
   first run.

---

## Numerical parity

All parity tests pass (`tests/test_parity.py`):

| Check | Result |
|---|---|
| Row count | 3,150 / 3,150 |
| `n_trades` per combo | **identical** to Rust |
| `sharpe`, `profit_factor`, `max_drawdown_r`, `total_return` | within **1e-6** |
| Top-10 by Sharpe | **same 10 combos, same order** |
| Walk-forward selections (4 windows) | **same params, same OOS metrics** |

Best combo (both implementations): fast=13, slow=50, atr_m=2.5, rr=3.0, tf=15min,
Sharpe = −0.5631, 8,294 trades.

---

## Conclusion

The Python playbook documented in [`ROADMAP.md`](./ROADMAP.md) is validated on
real data: **idiomatic, well-engineered Python with Numba reaches Rust-class
throughput** for this event-driven backtest + embarrassingly parallel grid search.
Future experiments in this repo can stay in Python for workloads of this shape
without a mandatory Rust rewrite.
