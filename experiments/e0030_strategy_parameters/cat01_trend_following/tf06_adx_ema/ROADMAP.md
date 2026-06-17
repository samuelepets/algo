# Roadmap — TF-06 ADX + EMA

## Phase 0 — Rust project setup
- [ ] `cargo init --name tf06_adx_ema` in this directory.
- [ ] Add dependencies to `Cargo.toml`: `csv`, `flate2`, `chrono`, `serde`, `rayon`.
- [ ] Verify `cargo build` succeeds.
- [ ] Add `outputs/` to `.gitignore`.

## Phase 1 — Data loading
- [ ] Load all `EURUSD_<YEAR>.csv.gz` from `../../../../data/bars/EURUSD/`.
- [ ] Parse ;`-delimited format with EET timestamps (`%Y.%m.%d %H:%M:%S`).
- [ ] Store in contiguous `Vec<Bar>` (`ts: i64, open, high, low, close, volume: f64`).

## Phase 2 — Resampling
- [ ] Implement `resample(bars, minutes)` → aggregate 1-min to 5-min, 15-min.

## Phase 3 — Indicator(s): ADX(14) trend strength + directional EMAs (+DI/-DI)
- [ ] Implement each indicator as a pure function over `&[Bar]` or `&[f64]`.
- [ ] Unit test against known reference values.

## Phase 4 — Backtest engine
- [ ] Signal logic specific to TF-06 ADX + EMA.
- [ ] One position at a time; ATR-based stop; fixed R:R target or indicator-based exit.
- [ ] Include spread cost: 0.00008 (0.8 pip) per round-trip.
- [ ] Compute `Metrics { sharpe, profit_factor, max_drawdown, total_return, n_trades }`.

## Phase 5 — Parameter grid search
- [ ] Build full parameter grid from `README.md` search space.
- [ ] Parallelise with `rayon::par_iter`.
- [ ] Write all rows to `outputs/results.csv`.

## Phase 6 — Walk-forward validation
- [ ] Rolling windows: 18-year in-sample → 4-year out-of-sample.
- [ ] Run top combination from Phase 5 on each window.
- [ ] Write `outputs/walkforward.csv`.

## Phase 7 — Output reporting
- [ ] Extract top-10 by Sharpe into `outputs/top_params.json`.
- [ ] Print summary to stdout.
