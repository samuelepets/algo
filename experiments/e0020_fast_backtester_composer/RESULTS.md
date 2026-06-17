# Results — e0020_fast_backtester_composer

Reference outcomes for the canonical performance workload defined in
[`STRATEGY.md`](./STRATEGY.md).

When comparing backtester implementations, **trading metrics must match** the
values below (within float tolerance). **Wall-clock time** is reported separately
and is expected to differ by language, hardware, and build flags.

---

## Workload

| Item | Value |
| ---- | ----- |
| Instrument | EUR/USD |
| Data | Full continuous stream, 2003–2025 (all corpus years) |
| Input bars | 8,490,235 |
| Strategy | `DualSmaCrossover` |
| Fast SMA | 50 bars |
| Slow SMA | 200 bars |
| Hold period | 60 bars |
| Transaction cost | 0.0 |

Reproduce with:

```bash
cargo run --release --bin benchmark-sma-crossover
```

Strategy and execution rules: [`STRATEGY.md`](./STRATEGY.md).

---

## Trading results (implementation-independent)

These values are the **correctness baseline**. Any backtester port used in a
performance comparison must reproduce them before timing is meaningful.

| Metric | Value |
| ------ | ----- |
| `total_return` | −0.146512 |
| `ann_return` | −0.009766 |
| `ann_vol` | 0.066019 |
| `sharpe` | −0.1156 |
| `max_drawdown` | −0.324686 |
| `hit_rate` | 0.4674 |
| `ann_turnover` | 5369.1045 |
| `n_bars` (return bars) | 8,490,234 |

**Tolerance when verifying parity:**

- `total_return`, `max_drawdown`: within **1e-4** (absolute)
- `sharpe`: within **1e-3** (absolute)
- Other metrics: within **1e-4** (absolute) unless noted otherwise in `STRATEGY.md`

---

## Backtest runtime (performance comparison)

### What to measure

Report **`backtest_run_ms`**: time to run the full in-memory backtest pipeline
**after** bars are already loaded into memory.

**Measurement protocol:** load data once, then repeat signal generation + backtest
**10 times** and report the **arithmetic mean** of each phase.

Included:

1. Signal generation (`DualSmaCrossover::generate_signal`)
2. Backtest engine (`backtest`)

Excluded:

- Reading gzipped CSV files from disk
- Gzip decompression
- CSV parsing and bar construction

Data loading is timed once as `load_ms` for diagnostics; it is **not** part of
the performance score.

```
backtest_run_ms_avg = signal_ms_avg + backtest_ms_avg
```

### Rust reference (this experiment)

Recorded on **2026-06-16**, `cargo run --release --bin benchmark-sma-crossover`
(10 runs averaged, load once), macOS arm64, release build:

| Phase | ms |
| ----- | --: |
| `load_ms` (excluded, once) | 4015.1 |
| `signal_ms_avg` | 43.4 |
| `backtest_ms_avg` | 174.2 |
| **`backtest_run_ms_avg`** | **217.6** |

Re-run the benchmark locally and update the comparison table when adding a new
implementation.

### Comparison table

| Implementation | Date | `backtest_run_ms_avg` | Notes |
| -------------- | ---- | --------------------: | ----- |
| Rust (`e0020`) | 2026-06-16 | 217.6 | release, 10-run mean, load once |

---

## Related documents

- Strategy specification: [`STRATEGY.md`](./STRATEGY.md)
- Experiment overview: [`README.md`](./README.md)
