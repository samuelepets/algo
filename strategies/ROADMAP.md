# Strategies Roadmap

This roadmap tracks the strategy research agenda for the `algo` project.

---

## Phase 1 — Strategy Research on 1-Minute Bars (current)

The primary goal of this phase is to **identify and document trading strategy
candidates** that can be derived from 1-minute OHLCV bars or from higher
timeframe bars resampled from them (5 min, 15 min, 30 min, 1 h, 4 h, daily).

### Objectives

- [ ] Survey classical intraday strategies applicable to 1-minute bars:
  - Trend-following (moving average crossovers, breakouts, momentum).
  - Mean-reversion (Bollinger Bands, RSI extremes, VWAP deviation).
  - Volatility-based (ATR expansions, opening range breakout).
  - Pattern-based (candlestick patterns, support/resistance levels).
- [ ] Evaluate each strategy class for suitability across the available
  instruments (Forex, Metals, Crypto) given their differing liquidity and
  volatility profiles.
- [ ] Identify which strategies benefit from **multi-timeframe confirmation**
  (e.g. signal on 1-min, trend filter on 15-min).
- [ ] Document each candidate in its own `strategies/<name>/README.md` with:
  - Hypothesis and theoretical edge.
  - Suggested entry/exit rules.
  - Key parameters to optimise.
  - Known failure modes and market conditions to avoid.
- [ ] Prioritise the top 3–5 candidates for implementation in `experiments/`.

### Timeframe resampling note

All higher timeframe bars should be **derived programmatically** from the
1-minute corpus (no separate data downloads). Resampling rules:

| Target TF | Aggregation                              |
|-----------|------------------------------------------|
| 5 min     | Group every 5 rows; OHLCV aggregation    |
| 15 min    | Group every 15 rows; OHLCV aggregation   |
| 30 min    | Group every 30 rows; OHLCV aggregation   |
| 1 h       | Group every 60 rows; OHLCV aggregation   |
| 4 h       | Group every 240 rows; OHLCV aggregation  |
| Daily     | Group by calendar date; OHLCV aggregation|

Standard OHLCV aggregation: Open = first, High = max, Low = min, Close = last,
Volume = sum.

---

## Phase 2 — Experiment Implementation (future)

Once Phase 1 research is complete, implement and backtest the top candidates
under `experiments/`. Each experiment will reference the strategy document from
this folder as its specification.

---

## Phase 3 — Evaluation & Selection (future)

Compare experiment results across instruments and timeframes. Select strategies
that demonstrate a robust, statistically significant edge for further development
(live paper trading, risk management integration, ensemble models, etc.).
