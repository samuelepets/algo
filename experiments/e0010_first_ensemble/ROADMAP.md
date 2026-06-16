# Roadmap — e0010_first_ensemble

Ordered, incremental plan to implement the experiment described in
[`RATIONALE.md`](./RATIONALE.md). Each phase should leave the experiment in a
runnable, committable state. All code is Python, managed with uv.

## Phase 0 — Environment setup (uv)

- [x] `uv init --python 3.12` in this directory to create `pyproject.toml` and pin
      the Python version.
- [x] `uv add pandas numpy` (core), `uv add --dev pytest ruff` (tooling).
- [x] Confirm `.venv/` is gitignored and that `pyproject.toml` + `uv.lock` are
      committed.
- [x] Add a `uv run ruff check` / `uv run pytest` sanity check.

## Phase 1 — Data access layer

- [x] Implement a loader that reads gzipped CSV bars from `../../data/bars/`,
      resolving the path relative to the repo root (no absolute paths). →
      `data.load_bars()` in `data.py`.
- [x] Parse the format correctly: `;` separator, `Time (EET)` timestamps
      (`%Y.%m.%d %H:%M:%S`), columns `Open/High/Low/Close/Volume`.
- [x] Provide helpers to select instrument(s) + year range and to resample
      1-minute bars to a coarser timeframe (e.g. 1h / 1d). →
      `available_years()`, `load_bars(years=/start_year=/end_year=)`, `resample()`.
- [x] Treat data strictly as read-only (loader never writes into `data/`).
      Caching derived frames under `outputs/` deferred until a consumer needs it.

## Phase 2 — Backtest harness

- [x] Define a minimal strategy interface (input: bars → output: target
      position / signal in [-1, 1]). → `Strategy` protocol in `backtest.py`.
- [x] Implement a vectorized backtester: signal → positions → returns → equity.
      Close(t) signal, Open(t+1) execution via `signal.shift(1)` and open-to-open
      returns. → `backtest()`.
- [x] Model transaction costs (spread/slippage/fees) via `cost_per_turnover` on
      position changes. Position sizing is the clipped signal in `[-1, 1]`.
- [x] Compute core metrics: total/annualized return, Sharpe, max drawdown,
      hit rate, turnover. → `compute_metrics()`.

## Phase 3 — Base strategies

- [x] S1 — Connors RSI(2) mean-reversion with SMA(200/5) regime filter.
      → `ConnorsRsi2` in `strategies.py`.
- [x] S2 — Dual EMA(9/21) crossover with RSI(14) momentum filter.
      → `EmaCrossRsi` in `strategies.py`.
- [x] S3 — RSI(14) 50-centerline crossover with EMA(50) trend filter.
      → `RsiCenterlineEma` in `strategies.py`.
- [x] Backtest each independently and record per-strategy metrics as the baseline
      to beat. → `baseline.py` (`uv run python baseline.py`).

## Phase 4 — Ensemble

- [ ] Combine base signals: majority vote, averaged signal, and inverse-volatility
      weighting.
- [ ] Measure correlation between base strategy return streams.
- [ ] Backtest each ensemble variant; compare against individual strategies.

## Phase 5 — Validation

- [ ] Out-of-sample / walk-forward split (train window → test window).
- [ ] Run across the selected instruments to check robustness (not one market).
- [ ] Basic sensitivity check on key parameters to gauge overfitting.

## Phase 6 — Reporting & conclusion

- [ ] Generate equity-curve and metrics plots into `outputs/`.
- [ ] Evaluate against the success criteria in `RATIONALE.md`.
- [ ] Write the conclusion (edge found / not found / inconclusive) and next steps
      in this experiment's `README.md`.

## Out of scope (for this experiment)

- Learned meta-models / ML-based ensembling.
- Live or paper trading and broker integration.
- Sharing code with other experiments (copy into a new experiment instead).
