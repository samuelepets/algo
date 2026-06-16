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

- **Diversification of edge.** Individual simple strategies — here a
  mean-reverting one and two trend-following ones — tend to work in different
  market regimes. If their return streams are weakly correlated, combining them
  should improve risk-adjusted performance and smooth the equity curve.
- **Lower overfitting risk.** A handful of simple, low-parameter rules combined is
  less prone to curve-fitting than a single highly-tuned model — a safer starting
  point before investing in complex strategies.
- **Reusable scaffolding.** Building an ensemble forces a clean separation between
  signal generation, position sizing, backtesting, and evaluation — infrastructure
  that later experiments can re-implement (copied, not shared) on a solid template.

## Hypothesis

> On the continuous EUR/USD 1-minute series, an equal-or-volatility-weighted
> ensemble of the three RSI + moving-average strategies defined below (S1–S3)
> achieves a
> **higher out-of-sample risk-adjusted return** (Sharpe) and **lower maximum
> drawdown** than the best individual strategy, because their mean-reverting and
> trend-following signals are weakly correlated.

## Scope

- **Instrument:** **EUR/USD only** (`data/bars/EURUSD/`, 2003–2025), 1-minute
  OHLCV bars.
- **Timeframe:** signals are computed directly on 1-minute bars for the first
  pass (coarser resampling may be explored later).
- **Continuous price series.** The EUR/USD bars are concatenated in chronological
  order and treated as **one continuous stream**. We deliberately ignore overnight
  and weekend boundaries during which the market is inactive: no gap modeling, no
  session resets, and no forced flattening at day/week boundaries. Indicators and
  bar-to-bar returns are computed over consecutive *available* bars as if no gap
  existed.
- **Base strategies:** three well-known, low-parameter strategies built from RSI
  and moving averages (see [Base strategies](#base-strategies-rsi--moving-averages)).
- **Ensemble methods:** simple aggregation (majority vote / averaged signal /
  inverse-volatility weighting); no learned meta-models for now.

## Base strategies (RSI + moving averages)

Three battle-tested, widely-documented strategies that combine the Relative
Strength Index (RSI) with moving averages (MA). They are intentionally
*different in nature* (one mean-reverting, two trend-following) so their signals
are weakly correlated — the prerequisite for a useful ensemble. Parameters below
are sensible defaults; the roadmap covers tuning and out-of-sample validation.

### S1 — Connors RSI(2) mean-reversion with SMA(200) regime filter

Larry Connors' classic short-term mean-reversion system: buy sharp pullbacks
*inside* a longer-term trend.

- **Regime filter:** `Close > SMA(200)` → longs only; `Close < SMA(200)` → shorts only.
- **Entry (long):** `RSI(2) < 10` (Connors found `< 5` even stronger) while above SMA(200).
- **Entry (short):** `RSI(2) > 90` (or `> 95`) while below SMA(200).
- **Exit:** long closes when `Close > SMA(5)`; short closes when `Close < SMA(5)`.
- **Nature:** mean-reversion. Well documented with high historical win rates on
  daily data; here it is adapted to the 1-minute continuous series.

### S2 — Dual EMA crossover with RSI(14) momentum filter

A standard trend-following crossover where RSI vetoes entries made into already
stretched momentum, reducing false signals in chop.

- **Trend signal:** fast `EMA(9)` vs. slow `EMA(21)` (slow `EMA(50)` as a slower
  variant).
- **Entry (long):** `EMA(9)` crosses above `EMA(21)` **and** `RSI(14) < 70`.
- **Entry (short):** `EMA(9)` crosses below `EMA(21)` **and** `RSI(14) > 30`.
- **Exit:** opposite crossover (optionally an ATR-based stop / 2:1 target later).
- **Nature:** trend-following. Reported as profitable across many instruments
  including EUR/USD with the same settings (evidence of a non-curve-fit edge).

### S3 — RSI(14) 50-centerline crossover with EMA(50) trend filter

Uses the RSI midline (50) as a momentum delimiter to time trend-continuation
entries, gated by a moving-average trend filter.

- **Trend filter:** `Close > EMA(50)` → bullish bias; `Close < EMA(50)` → bearish bias.
- **Entry (long):** `RSI(14)` crosses **above 50** while `Close > EMA(50)`.
- **Entry (short):** `RSI(14)` crosses **below 50** while `Close < EMA(50)`.
- **Exit:** long closes when `RSI(14)` crosses back below 50; short mirrors.
- **Nature:** trend/momentum continuation. The 50-line bull/bear logic combined
  with an MA filter is a well-established way to trade pullbacks in a trend.

## Success criteria

The experiment is considered to have found an **edge** if, **out of sample**:

- The ensemble's Sharpe ratio exceeds that of every individual base strategy
  (S1–S3), and
- Its maximum drawdown is no worse than the median base strategy, and
- Results hold across more than one time period / walk-forward window on EUR/USD
  (not a single lucky stretch), net of modeled transaction costs.

Otherwise the conclusion is recorded as *no edge* or *inconclusive*, with notes on
what to try next. Either outcome is a valid, useful result.

## Assumptions & caveats

- **Continuous-series simplification.** Treating EUR/USD as a gapless stream
  ignores weekend/holiday gap risk and session microstructure. A position held
  "across" an inactive period is, in reality, exposed to the open-gap on the next
  active bar — this model does not penalize that. Acceptable for a first pass;
  revisit if results look sensitive to boundary bars.
- Costs (spread, slippage, fees) and execution realism materially affect results
  on 1-minute data; they must be modeled explicitly (see roadmap). Assume
  signals are evaluated at `Close(t)` and executed at `Open(t+1)` to avoid
  look-ahead bias.
- The three strategies' default parameters come from the literature (daily/higher
  timeframes); they may need adjustment for 1-minute bars. Tuning must be done on
  in-sample data only and validated out-of-sample.
- Findings are descriptive of historical data only; no live-trading claims.

## References

- Connors RSI(2): StockCharts ChartSchool —
  <https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2>;
  QuantifiedStrategies — <https://www.quantifiedstrategies.com/rsi-2-strategy/>
- EMA crossover + RSI filter (multi-instrument incl. EUR/USD): TradingView
  "EMA Cross + RSI Day" — <https://www.tradingview.com/script/9YyXVQSn-EMA-Cross-RSI-Day/>
- RSI 50-centerline + trend confirmation: Aurra Markets —
  <https://www.aurra.markets/academy/advanced-guides/3-powerful-rsi-trading-strategies-beyond-overbought-or-oversold>
