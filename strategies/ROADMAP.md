# Strategies Roadmap

This roadmap tracks the strategy research agenda for the `algo` project.

---

## Phase 1 — Strategy Research on 1-Minute Bars (current)

The primary goal of this phase is to **identify and document trading strategy
candidates** that can be derived from 1-minute OHLCV bars or from higher
timeframe bars resampled from them (5 min, 15 min, 30 min, 1 h, 4 h, daily).

### Objectives

- [x] Survey classical intraday strategies applicable to 1-minute bars →
  see [`CATEGORIES.md`](./CATEGORIES.md) for the exhaustive catalog (9 families,
  34 strategy categories with hypothesis, signals, parameters, instrument
  suitability, and a summary matrix).

#### Per-category deep-dive research

Each category below requires its own research document with:
the top strategies in the category, detailed indicator mechanics, standard
parameters, entry/exit rules, and a brute-force parameter search space.

- [x] **Cat 1 — Trend-Following** → [`01_TREND_FOLLOWING.md`](./01_TREND_FOLLOWING.md)
  20 strategies: EMA crossover, Triple EMA, MACD, MACD+200EMA, EMA+RSI, ADX+EMA,
  SuperTrend, SuperTrend+VWAP+ADX, VWAP bias, Parabolic SAR, Ichimoku, Alligator,
  EMA Ribbon, HMA, EMA Pullback, LinReg Channel, Donchian, N-bar Breakout, ROC
  Breakout, Elder Impulse System.
- [ ] **Cat 2 — Mean-Reversion** → `02_MEAN_REVERSION.md` *(pending)*
  Should cover: Bollinger Band reversion, RSI extremes (RSI-2, RSI oversold/overbought
  fades), VWAP deviation fade, Z-score reversion, Stochastic reversion,
  Keltner Channel reversion, Chandelier exit reversion, Connors RSI, DeMark
  sequential, CCI reversion, price channel reversion, statistical arbitrage,
  mean-reversion after news spike, overnight gap fill, and others.
- [ ] **Cat 3 — Volatility-Based** → `03_VOLATILITY.md` *(pending)*
  Should cover: ATR expansion/contraction, Opening Range Breakout (ORB) variants
  (5-min, 15-min, 30-min), Volatility Squeeze (Keltner+Bollinger), Bollinger Band
  width contraction, realized vol percentile regime, VIX proxy for forex/crypto,
  average true range breakout, gap-and-go, range expansion after inside bars,
  Narrow Range (NR7) patterns, and others.
- [ ] **Cat 4 — Pattern-Based** → `04_PATTERNS.md` *(pending)*
  Should cover: top candlestick patterns (pin bar, engulfing, hammer, doji, morning
  star, etc.), chart patterns (H&S, double top/bottom, triangles, flags, wedges),
  support & resistance breakout/bounce, Fair Value Gaps (FVG/imbalance), order
  blocks, liquidity sweeps, equal highs/lows, change of character (CHoCH),
  break of structure (BOS), and others from the ICT/SMC framework.
- [ ] **Cat 5 — Time-Based** → `05_TIME_BASED.md` *(pending)*
  Should cover: session open/close effects (London, NY, Asian, Sydney),
  time-of-day seasonality (hour-of-day return statistics), day-of-week seasonality,
  London Killzone, NY Killzone, Asia Killzone, macro event windows (NFP, CPI),
  end-of-month effects, and others.
- [ ] **Cat 6 — Statistical & Quantitative** → `06_STATISTICAL.md` *(pending)*
  Should cover: linear regression channel trading, Kalman Filter trend,
  Hurst Exponent regime detection, autocorrelation regime, pairs/spread trading
  (XAUUSD/XAGUSD, BTC/ETH), cointegration-based systems, ARIMA-based forecasting,
  Ornstein-Uhlenbeck spread reversion, principal component analysis (PCA)
  detrending, fractal market hypothesis applications, and others.
- [ ] **Cat 7 — Multi-Timeframe** → `07_MULTI_TIMEFRAME.md` *(pending)*
  Should cover: higher-TF trend + lower-TF entry (all combinations 1-min/5-min/
  15-min/1-h), multi-TF confluence scoring, top-down analysis (daily → 1-h →
  5-min), VWAP on multiple timeframes, MTF RSI, MTF MACD, triple screen system
  (Elder), and others.
- [ ] **Cat 8 — Volume-Based** → `08_VOLUME_BASED.md` *(pending)*
  Should cover: volume spike detection, OBV divergence, VWAP (volume-weighted
  entry timing), Money Flow Index (MFI), Chaikin Money Flow, volume profile
  (POC, VAH, VAL), Volume-Weighted MACD, Accumulation/Distribution line,
  volume-confirmed breakouts, volume climax/exhaustion patterns, and others.
- [ ] **Cat 9 — Machine Learning–Assisted** → `09_ML_ASSISTED.md` *(pending)*
  Should cover: feature engineering for 1-min bars, supervised classification
  (Random Forest, XGBoost, LightGBM), walk-forward validation methodology,
  feature importance analysis, LSTM/GRU for sequence prediction, Transformer
  attention on bar sequences, reinforcement learning environment design (gym
  wrapper over bars), meta-labeling (López de Prado), fractional differentiation,
  and others.

#### General objectives (all categories)

- [ ] Evaluate each strategy class for suitability across the available
  instruments (Forex, Metals, Crypto) given their differing liquidity and
  volatility profiles.
- [ ] Identify which strategies benefit from **multi-timeframe confirmation**
  (e.g. signal on 1-min, trend filter on 15-min).
- [ ] Prioritise the top 3–5 candidates across all categories for implementation
  in `experiments/`.

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
