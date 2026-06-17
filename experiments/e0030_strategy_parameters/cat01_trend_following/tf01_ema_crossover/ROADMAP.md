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
- [x] Returns `Metrics { sharpe, profit_factor, max_drawdown_r, total_return, n_trades }`
      (`max_drawdown_r` = peak-to-trough decline of cumulative-R equity, absolute R).

## Phase 5 — Parameter grid search
- [x] 3,150 combinations (1,575 per TF); `rayon::par_iter` parallelism.
- [x] Full-sample grid search ~3s (5-min TF ~2.5s, 15-min TF ~0.5s); full
      end-to-end run (load + grid + walk-forward) ~12–15s.
- [x] `outputs/results.csv` written (3,150 rows).

## Phase 6 — Walk-forward validation
- [x] 4 anchored windows (IS always starts 2003; OOS steps 2 years).
- [x] **IS-only parameter selection**: full grid re-optimised on each IS slice,
      best set evaluated unchanged on OOS (no full-history selection leak).
- [x] Selected params logged per window in `outputs/walkforward.csv`.

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

The walk-forward (with honest IS-only parameter selection) confirms the
degradation: the IS-optimal set delivers negative OOS Sharpe in **all 4 of 4
windows** (−0.20, −0.70, −1.80, −1.73).

**Conclusion:** TF-01 is **not** a candidate for implementation. The strategy
requires additional filters (ADX regime, MTF trend, session filter) to be viable.
See `strategies/01_TREND_FOLLOWING.md § TF-05`, `TF-06`, `TF-07` for
filtered variants that may perform better.
