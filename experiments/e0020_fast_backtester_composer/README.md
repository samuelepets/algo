# e0020_fast_backtester_composer

High-performance **Rust** backtester for 1-minute OHLCV bars in this repository.

> **Note:** This is a **legacy** experiment. New work in this repo uses **Python**
> (see [`AGENTS.md`](../../AGENTS.md) and
> [`e0030_strategy_parameters/cat01_trend_following/tf01_ema_crossover_python/`](../e0030_strategy_parameters/cat01_trend_following/tf01_ema_crossover_python/)).
> This folder is retained for reference and performance comparison only.

This experiment is **self-contained** (see [`../README.md`](../README.md)). Its
only external dependency is the root [`data/`](../../data) corpus, which is
**read-only**.

- **Reference test strategy:** see [`STRATEGY.md`](./STRATEGY.md).
- **Reference results:** see [`RESULTS.md`](./RESULTS.md).

## Goal

Build a fast backtester implementation and a fixed reference workload so future
implementations (other languages, engines, or architectures) can be compared on
the same data, strategy, and execution rules.

This is a **performance and correctness fixture**, not a search for a trading
edge.

## Tech stack

- **Language:** Rust (library + CLI binary)
- **Build:** Cargo
- **I/O:** `flate2` + `csv` for gzipped semicolon-delimited bar files
- **Time:** `chrono` (EET timestamps from the corpus)

## Build & run

```bash
# From this experiment directory: experiments/e0020_fast_backtester_composer/

cargo build --release
cargo test
cargo run --release --bin fast-backtester -- EURUSD 2024
cargo run --release --bin benchmark-sma-crossover
cargo bench --bench sma_crossover
```

Commit `Cargo.toml` and `Cargo.lock`. Never commit `target/` or generated outputs.

## Execution convention

A strategy emits a target position `signal[t]` in `[-1, 1]` using information
up to and including `Close(t)`. The position held over `[Open(t), Open(t+1))`
is `signal[t-1]`. Per-bar return is open-to-open: `Open(t+1) / Open(t) - 1`.

Full rules and reference metrics are in [`STRATEGY.md`](./STRATEGY.md).

## Data access

Bar files are resolved relative to the repo root:

`data/bars/<SYMBOL>/<SYMBOL>_<YEAR>.csv.gz`

Never write into `data/`.

## Layout

```
src/
├── lib.rs
├── bar.rs        # OHLCV bar type
├── data.rs       # corpus loader
├── backtest.rs   # vectorized engine
├── metrics.rs    # performance statistics
├── indicators.rs # SMA and other indicators
├── strategy.rs   # DualSmaCrossover strategy
└── bin/
    ├── fast_backtester.rs
    └── benchmark_sma_crossover.rs
```

## Outputs

Generated artifacts go under `outputs/` (gitignored). Only commit code and findings.

## Status

- [x] Rust project scaffold
- [x] Corpus loader for gzipped CSV bars
- [x] Vectorized backtest core + metrics
- [x] Reference strategy on full EURUSD continuous stream
- [x] Criterion benchmark (`benches/sma_crossover.rs`)
- [ ] Compare against future backtester implementations
