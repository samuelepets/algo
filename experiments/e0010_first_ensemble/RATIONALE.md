# Rationale — e0010_first_ensemble

## Motivation

This is the first experiment in the repository. It has two intertwined goals:

1. **Bootstrap the research workflow.** Stand up the minimal, reusable pieces a
   trading experiment needs — data loading from the root `data/` corpus, a simple
   backtest loop, and a metrics/reporting step — inside a single self-contained
   experiment, following the project conventions (Python + uv).
2. **Test the ensemble idea as a baseline.** Rather than betting on one clever
   signal, start by combining several *simple, well-understood* strategies into an
   **ensemble** and measure whether the combination is more robust than its parts.

## Why an ensemble first

- **Diversification of edge.** Individual simple strategies (trend/momentum,
  mean-reversion, breakout) tend to work in different market regimes. If their
  return streams are weakly correlated, combining them should improve risk-adjusted
  performance and smooth the equity curve.
- **Lower overfitting risk.** A handful of simple, low-parameter rules combined is
  less prone to curve-fitting than a single highly-tuned model — a safer starting
  point before investing in complex strategies.
- **Reusable scaffolding.** Building an ensemble forces a clean separation between
  signal generation, position sizing, backtesting, and evaluation — infrastructure
  that later experiments can re-implement (copied, not shared) on a solid template.

## Hypothesis

> An equal-or-volatility-weighted ensemble of a few simple, weakly-correlated base
> strategies achieves a **higher out-of-sample risk-adjusted return** (Sharpe) and
> **lower maximum drawdown** than the best individual base strategy, on the
> instruments and period studied.

## Scope

- **Data:** 1-minute OHLCV bars from `data/bars/` (resampled to a coarser
  timeframe as needed). Initial focus on a small, liquid subset (e.g. `BTCUSD`,
  `ETHUSD`, `EURUSD`, `XAUUSD`); exact selection to be fixed in the roadmap.
- **Base strategies:** a small set of classic, low-parameter rules (e.g. moving-
  average trend, RSI/z-score mean-reversion, Donchian breakout).
- **Ensemble methods:** start with simple aggregation (majority vote / averaged
  signal / inverse-volatility weighting); avoid learned meta-models for now.

## Success criteria

The experiment is considered to have found an **edge** if, **out of sample**:

- The ensemble's Sharpe ratio exceeds that of every individual base strategy, and
- Its maximum drawdown is no worse than the median base strategy, and
- Results hold across more than one instrument (not a single lucky market).

Otherwise the conclusion is recorded as *no edge* or *inconclusive*, with notes on
what to try next. Either outcome is a valid, useful result.

## Assumptions & caveats

- Costs (spread, slippage, fees) and execution realism materially affect results
  on 1-minute data; they must be modeled explicitly (see roadmap).
- Volume is `0` for some instruments/periods in the corpus — volume-based signals
  may be unusable for those and must be handled or excluded.
- Findings are descriptive of historical data only; no live-trading claims.
