# e0030 — Strategy Parameter Search

## Hypothesis

Every trading strategy documented in `strategies/` has a set of free parameters
(EMA periods, ATR multipliers, thresholds, etc.) whose optimal values are
instrument- and regime-dependent. This experiment systematically searches for
the parameter combinations that maximise risk-adjusted returns on EURUSD over
the full available history (2003–2025), using **brute-force grid search**
implemented in **Python** (Numba-compiled hot loops) for performance.

## Objective

For each strategy documented in `strategies/CATEGORIES.md`:

1. Enumerate the complete parameter grid defined in the corresponding strategy
   research document.
2. Run a full backtest for every parameter combination over EURUSD 1-min bars
   (resampled to the target timeframe per strategy).
3. Rank combinations by Sharpe Ratio (primary), Profit Factor, and Max Drawdown.
4. Validate the top-N combinations via walk-forward analysis to detect overfitting.
5. Report the best robust parameter set per strategy as a candidate for
   live/paper trading experiments.

## Structure

```
e0030_strategy_parameters/
├── README.md                       # this file
├── ROADMAP.md                      # top-level progress tracker
├── .gitignore
└── cat01_trend_following/          # one sub-experiment per CATEGORIES.md category
    ├── README.md
    ├── ROADMAP.md
    ├── tf01_ema_crossover/         # one sub-sub-experiment per strategy
    │   ├── README.md               # strategy spec, search space, results summary
    │   ├── ROADMAP.md              # implementation phases
    │   ├── data.py                 # Polars loader → NumPy struct-of-arrays
    │   ├── indicators.py           # Numba indicator kernels
    │   ├── backtest.py             # Numba backtest engine
    │   └── main.py                 # grid search + walk-forward driver
    ├── tf02_triple_ema/
    │   └── ...
    └── ... (tf03 – tf20)
```

Future categories (cat02 through cat09) will be added as the corresponding
strategy research documents in `strategies/` are completed.

## Technology

All **new** sub-sub-experiments are independent **Python** projects managed with
[**uv**](https://docs.astral.sh/uv/). Follow the conventions validated in
[`cat01_trend_following/tf01_ema_crossover_python/`](./cat01_trend_following/tf01_ema_crossover_python/):

- **Performance:** Polars for IO; Numba `@njit` for resampling, indicators, and
  the path-dependent backtest; `numba.prange` for parallel grid search. The TF-01
  parity port proved this stack matches legacy Rust end-to-end runtime (~12 s on
  8.5 M bars × 3,150 combos) without sacrificing numerical fidelity.
- **Reproducibility:** Pinned `uv.lock`, deterministic algorithms, unit tests.
- **Self-contained:** Each strategy folder is its own uv project; copy patterns
  from the reference — never import across experiments.

**Legacy Rust:** `tf01_ema_crossover/` (completed) remains as a historical
reference implementation. Do not add new Rust strategy folders.

## Instrument

Primary instrument: **EURUSD** (2003–2025, 22 years of 1-min bars).
Path: `data/bars/EURUSD/EURUSD_<YEAR>.csv.gz` (read-only).

Secondary instruments (future): XAUUSD, BTCUSD.

## Evaluation Metrics

| Metric | Target |
|---|---|
| Sharpe Ratio (annualised) | > 1.0 out-of-sample |
| Profit Factor | > 1.3 |
| Max Drawdown | < 20% |
| Min trades (OOS window) | ≥ 50 |

## Outputs

Each sub-sub-experiment writes its results to `outputs/` (gitignored):

- `results.csv` — full grid search results (one row per parameter combination).
- `top_params.json` — top-10 combinations by Sharpe.
- `walkforward.csv` — walk-forward window metrics for the top combination.

## Status

| Category | Status |
|---|---|
| Cat 1 — Trend-Following (20 strategies) | TF-01 complete (Rust + Python); TF-02 complete (Python); TF-03–20 pending |
| Cat 2–9 | Pending strategy research documents |
