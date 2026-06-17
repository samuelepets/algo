# Roadmap — TF-01 EMA Crossover

## Phase 0 — Rust project setup
- [ ] `cargo init --name tf01_ema_crossover` in this directory.
- [ ] Add dependencies to `Cargo.toml`: `csv`, `flate2` (gzip), `chrono`, `serde`, `rayon` (parallel search).
- [ ] Verify `cargo build` succeeds.
- [ ] Add `outputs/` to `.gitignore`.

## Phase 1 — Data loading
- [ ] Implement a loader that reads all `EURUSD_<YEAR>.csv.gz` files from
      `../../../../data/bars/EURUSD/`, resolved relative to the repo root.
- [ ] Parse `;`-delimited format: `Time (EET);Open;High;Low;Close;Volume`.
- [ ] Parse timestamps with format `%Y.%m.%d %H:%M:%S`.
- [ ] Store bars in a contiguous `Vec<Bar>` struct `{ ts: i64, open, high, low, close, volume: f64 }`.
- [ ] Assert loaded bar count is in the expected range (≥ 5 M for full history).

## Phase 2 — Resampling
- [ ] Implement `resample(bars: &[Bar], minutes: u32) -> Vec<Bar>`:
      group by `floor(ts / (minutes × 60))`, aggregate OHLCV (O=first, H=max, L=min, C=last, V=sum).
- [ ] Produce both 5-min and 15-min bar vectors from the 1-min source.

## Phase 3 — Indicator: EMA
- [ ] Implement `ema(bars: &[Bar], period: usize) -> Vec<f64>` using the standard
      multiplier `k = 2 / (period + 1)`.
- [ ] Warm-up: first value = SMA of the first `period` closes; then EMA recurrence.
- [ ] Unit test: verify EMA(9) on a known sequence matches a reference calculator.

## Phase 4 — Backtest engine
- [ ] Implement `backtest(bars: &[Bar], fast: &[f64], slow: &[f64], atr: &[f64], params: &Params) -> Metrics`.
- [ ] Signal: long on `fast[i-1] < slow[i-1] && fast[i] > slow[i]`; short on inverse.
      Both EMAs must slope in crossover direction (slope = `ema[i] > ema[i-1]`).
- [ ] Position: one unit at a time; no pyramiding.
- [ ] Stop: placed at `entry_price ± atr_stop_mult × ATR(14)` at entry.
- [ ] Target: placed at `entry_price ± rr_ratio × stop_distance`.
- [ ] Exit: stop hit, target hit, or opposite crossover — whichever comes first.
- [ ] Track: equity curve, trade list `(entry_ts, exit_ts, pnl, exit_reason)`.
- [ ] Compute `Metrics { sharpe, profit_factor, max_drawdown, total_return, n_trades }`.
- [ ] Include a fixed spread cost of 0.00008 (0.8 pip) per trade round-trip.

## Phase 5 — Parameter grid search
- [ ] Build the full parameter grid (respecting `slow > fast + 5` constraint).
- [ ] Use `rayon::par_iter` to parallelise across CPU cores.
- [ ] Write all rows to `outputs/results.csv` as they complete.

## Phase 6 — Walk-forward validation
- [ ] Split history into 12 rolling windows: 18-year in-sample → 4-year out-of-sample.
- [ ] For each window: run the top combination from the full-history search.
- [ ] Write per-window metrics to `outputs/walkforward.csv`.

## Phase 7 — Output reporting
- [ ] Sort `results.csv` by Sharpe descending; extract top-10 into `outputs/top_params.json`.
- [ ] Print a human-readable summary to stdout when the binary completes.
