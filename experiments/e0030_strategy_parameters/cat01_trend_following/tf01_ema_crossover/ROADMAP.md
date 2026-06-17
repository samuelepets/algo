# Roadmap — TF-01 EMA Crossover

## Phase 0 — Rust project setup
- [x] `cargo init --name tf01_ema_crossover` in this directory.
- [x] Add dependencies to `Cargo.toml`: `csv`, `flate2`, `chrono`, `serde`, `serde_json`, `rayon`.
- [x] `cargo build --release` succeeds with zero warnings.
- [x] `outputs/` added to `.gitignore`.

## Phase 1 — Data loading
- [x] `src/data.rs`: `load_eurusd()` loads all `EURUSD_<YEAR>.csv.gz` from
      `../../../../data/bars/EURUSD/`. 8,490,235 bars loaded (23.4 years). [3.6s]
- [x] Parses `;`-delimited format, EET timestamps (`%Y.%m.%d %H:%M:%S`).
- [x] Stores as `Vec<Bar>` (`ts: i64, open, high, low, close, volume: f64`).

## Phase 2 — Resampling
- [x] `resample(&bars, minutes)`: OHLCV bucket aggregation.
      5-min → 1,698,048 bars; 15-min → 566,016 bars.

## Phase 3 — Indicators
- [x] `src/indicators.rs`: `ema(period)` with SMA seed + EMA recurrence.
- [x] `atr(period)` with Wilder's smoothing.
- [x] 5 unit tests pass (`cargo test`).

## Phase 4 — Backtest engine
- [x] `src/backtest.rs`: `backtest()` with slope-confirmed crossover entry,
      ATR stop, fixed R:R target, opposite-crossover exit.
- [x] Spread cost: 0.00008 (0.8 pip) per round-trip.
- [x] Returns `Metrics { sharpe, profit_factor, max_drawdown, total_return, n_trades }`.

## Phase 5 — Parameter grid search
- [x] 3,150 combinations (1,575 per TF); `rayon::par_iter` parallelism.
- [x] Run time: 5-min TF 3.54s, 15-min TF 0.66s, total 8.4s.
- [x] `outputs/results.csv` written (3,150 rows).

## Phase 6 — Walk-forward validation
- [x] 4 anchored windows (IS always starts 2003; OOS steps 2 years).
- [x] `outputs/walkforward.csv` written.

## Phase 7 — Output reporting
- [x] `outputs/top_params.json` with top-10 by Sharpe.
- [x] Human-readable table printed to stdout.

---

## Results (EURUSD 2003–2025)

> All Sharpe ratios are negative across all 3,150 parameter combinations.
> The best combination (fast=13, slow=50, atr_m=2.5, rr=3.0, tf=15min)
> achieved Sharpe = −0.56.

**Key finding:** Pure EMA crossover with ATR stop + fixed R:R target has
**no edge** on EURUSD over this 22-year sample. All strategies are net
losing after the 0.8-pip spread cost, regardless of parameter choice.

The walk-forward confirms the degradation: even the marginal outperformer
on IS delivers negative OOS Sharpe in 3 of 4 windows.

**Conclusion:** TF-01 is **not** a candidate for implementation. The strategy
requires additional filters (ADX regime, MTF trend, session filter) to be viable.
See `strategies/01_TREND_FOLLOWING.md § TF-05`, `TF-06`, `TF-07` for
filtered variants that may perform better.
