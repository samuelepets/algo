# Intraday Strategy Categories

Exhaustive catalog of intraday trading strategy families applicable to
**1-minute OHLCV bars** (or bars resampled from them). Each category describes
the core hypothesis, the signals involved, typical parameters, instrument
suitability within our corpus, and known limitations.

Use this document as the master reference for Phase 1 research. When a category
is selected for detailed development, create `strategies/<name>/README.md` and
cross-reference it here.

---

## Table of Contents

1. [Trend-Following](#1-trend-following)
   - 1.1 Moving Average Crossovers
   - 1.2 Momentum / Rate of Change
   - 1.3 Breakout / Channel Breakout
   - 1.4 Donchian Channel Breakout
   - 1.5 ADX-Filtered Trend
2. [Mean-Reversion](#2-mean-reversion)
   - 2.1 Bollinger Band Reversion
   - 2.2 RSI Extremes
   - 2.3 VWAP Deviation
   - 2.4 Z-Score / Statistical Reversion
   - 2.5 Stochastic Oscillator Reversion
3. [Volatility-Based](#3-volatility-based)
   - 3.1 ATR Expansion / Contraction
   - 3.2 Opening Range Breakout (ORB)
   - 3.3 Volatility Squeeze (Keltner + Bollinger)
   - 3.4 Implied Volatility Regime Filter
4. [Pattern-Based](#4-pattern-based)
   - 4.1 Candlestick Patterns
   - 4.2 Chart Patterns (Head & Shoulders, Triangles, etc.)
   - 4.3 Support & Resistance Levels
   - 4.4 Fair Value Gaps (FVG / Imbalance)
   - 4.5 Order Blocks
5. [Time-Based](#5-time-based)
   - 5.1 Session Open / Close Effects
   - 5.2 Time-of-Day Seasonality
   - 5.3 Day-of-Week Seasonality
6. [Statistical & Quantitative](#6-statistical--quantitative)
   - 6.1 Linear Regression Channel
   - 6.2 Kalman Filter Trend
   - 6.3 Hurst Exponent Regime Detection
   - 6.4 Autocorrelation / Serial Correlation
   - 6.5 Pairs / Spread Trading (Cross-Instrument)
7. [Multi-Timeframe (MTF)](#7-multi-timeframe-mtf)
   - 7.1 Higher-TF Trend + Lower-TF Entry
   - 7.2 Multi-TF Confluence
8. [Volume-Based](#8-volume-based)
   - 8.1 Volume Spike Detection
   - 8.2 On-Balance Volume (OBV) Divergence
   - 8.3 Volume-Weighted Signals
9. [Machine Learning–Assisted](#9-machine-learning-assisted)
   - 9.1 Feature-Based Classification
   - 9.2 Sequence Models (LSTM / Transformer)
   - 9.3 Reinforcement Learning

---

## 1. Trend-Following

**Core hypothesis:** Price exhibits serial correlation over short periods — a bar
moving in one direction is more likely to be followed by another bar in the same
direction. Capturing this momentum before it exhausts generates profit.

### 1.1 Moving Average Crossovers

| Attribute   | Detail |
|-------------|--------|
| Signal      | Fast MA crosses above/below slow MA → long/short. |
| Common MAs  | EMA(5), EMA(10), EMA(20), EMA(50); SMA alternatives. |
| Parameters  | Fast period, slow period, MA type (EMA/SMA/WMA). |
| Entry       | Bar close after crossover confirmation. |
| Exit        | Opposite crossover or trailing stop (ATR multiple). |
| Instruments | All; works best on trending instruments (BTCUSD, XAUUSD, EURUSD). |
| Strengths   | Simple, well-studied, easy to combine with filters. |
| Weaknesses  | Heavy whipsawing in choppy/ranging markets; lag inherent to MAs. |
| Notes       | On 1-min bars, very short periods (3/8) can reduce lag but increase noise. Multi-TF filter (e.g. 1-h trend direction) strongly recommended. |

### 1.2 Momentum / Rate of Change (ROC)

| Attribute   | Detail |
|-------------|--------|
| Signal      | ROC(n) > threshold → long; ROC(n) < −threshold → short. |
| Parameters  | Lookback period n (e.g. 5–30 bars on 1-min = 5–30 minutes). |
| Entry       | On bar close when ROC threshold is crossed. |
| Exit        | Fixed holding period, or ROC returns to zero, or stop-loss. |
| Instruments | Best on high-volatility instruments (BTCUSD, ETHUSD, XAUUSD). |
| Strengths   | Directly measures price velocity; no lag from MA smoothing. |
| Weaknesses  | Highly sensitive to noise on short timeframes; prone to false signals near news events. |

### 1.3 Breakout / Channel Breakout

| Attribute   | Detail |
|-------------|--------|
| Signal      | Price closes above recent high (or below recent low) → directional entry. |
| Parameters  | Lookback window for high/low (e.g. 20–120 bars). |
| Entry       | On bar close above high + optional buffer (% or ATR). |
| Exit        | Trailing stop; or reversion inside channel. |
| Instruments | All; particularly effective around high-volatility sessions (London, NY open). |
| Strengths   | Objective level definition; captures large moves early. |
| Weaknesses  | Many false breakouts on 1-min; requires volume or volatility confirmation. |

### 1.4 Donchian Channel Breakout

| Attribute   | Detail |
|-------------|--------|
| Signal      | Price touches upper/lower Donchian channel (n-period high/low). |
| Parameters  | Channel period n; stop at middle band or opposite channel. |
| Entry       | Touch or close beyond channel band. |
| Exit        | Opposite channel touch; fixed ATR multiple stop. |
| Instruments | Originally designed for futures/commodities; applicable to XAUUSD, XAGUSD, Crypto. |
| Strengths   | Systematic, no ambiguity in channel definition. |
| Weaknesses  | Same false-breakout exposure as 1.3; performs poorly in ranging markets. |

### 1.5 ADX-Filtered Trend

| Attribute   | Detail |
|-------------|--------|
| Signal      | ADX > threshold (e.g. 25) confirms a trend is present; use with +DI/−DI crossover or MA crossover. |
| Parameters  | ADX period (14 typical), ADX threshold. |
| Role        | Filter — only take trend signals when ADX confirms trend strength. |
| Instruments | All. |
| Strengths   | Reduces whipsaw by avoiding entries in ranging conditions. |
| Weaknesses  | ADX is a lagging indicator; can miss the early part of a trend. |

---

## 2. Mean-Reversion

**Core hypothesis:** Price has a tendency to revert to a statistical mean after
short-term extremes. Fading overextensions generates profit when the mean holds.

### 2.1 Bollinger Band Reversion

| Attribute   | Detail |
|-------------|--------|
| Signal      | Price touches/closes outside outer band → fade entry toward middle band. |
| Parameters  | MA period (20 typical), band width (σ multiplier: 1.5–2.5). |
| Entry       | Bar close outside band; or first close back inside band. |
| Exit        | Middle band (MA); or opposite band. |
| Instruments | All; most reliable on Forex (EURUSD) during low-volatility sessions. |
| Strengths   | Self-adjusting to volatility; very well understood. |
| Weaknesses  | Bands widen during trending moves, making "outside band" entries dangerous; stop placement is non-trivial. |

### 2.2 RSI Extremes

| Attribute   | Detail |
|-------------|--------|
| Signal      | RSI < 30 → long; RSI > 70 → short. Tighter levels (20/80) reduce frequency but improve quality. |
| Parameters  | RSI period (2–14); overbought/oversold thresholds. |
| Entry       | On threshold cross or on first bar exiting extreme zone. |
| Exit        | RSI returns to 50; or fixed holding period; or ATR stop. |
| Instruments | All; RSI(2) mean-reversion is well-documented on equities — adapt for Forex/Crypto. |
| Strengths   | Bounded oscillator; intuitive. |
| Weaknesses  | In strong trends, RSI can stay extreme for many bars; momentum regime must be excluded. |

### 2.3 VWAP Deviation

| Attribute   | Detail |
|-------------|--------|
| Signal      | Price deviates > N standard deviations from intraday VWAP → fade back toward VWAP. |
| Parameters  | VWAP reset period (session, day); deviation bands (1σ, 2σ). |
| Entry       | Price at ±2σ from VWAP. |
| Exit        | Price returns to VWAP; or ±1σ band. |
| Instruments | VWAP is session-anchored; most meaningful for instruments with clear session structure (EURUSD, XAUUSD). Volume data required. |
| Strengths   | Widely used by institutional traders — VWAP acts as an actual price anchor. |
| Weaknesses  | Volume in our corpus may be tick-volume (not notional); VWAP anchor validity depends on data quality. |
| Notes       | Verify that Volume > 0 is consistently available for target instruments before relying on VWAP. |

### 2.4 Z-Score / Statistical Reversion

| Attribute   | Detail |
|-------------|--------|
| Signal      | Rolling z-score of price (or returns) exceeds ±2 → fade. |
| Parameters  | Rolling window for mean/std (e.g. 60–240 bars); z-score threshold. |
| Entry       | Z > +threshold → short; Z < −threshold → long. |
| Exit        | Z returns to 0 (mean). |
| Instruments | All; particularly applicable to spread series in pairs trading (see 6.5). |
| Strengths   | Statistically grounded; easy to parameterise. |
| Weaknesses  | Assumes stationarity — price is not stationary; log-returns or detrended price recommended. |

### 2.5 Stochastic Oscillator Reversion

| Attribute   | Detail |
|-------------|--------|
| Signal      | %K < 20 and crosses above %D → long; %K > 80 and crosses below %D → short. |
| Parameters  | %K period, %D smoothing, overbought/oversold levels. |
| Entry       | %K/%D crossover inside extreme zone. |
| Exit        | Crossover in opposite extreme; or fixed holding period. |
| Instruments | All. |
| Strengths   | More responsive than RSI in ranging markets due to dual-line confirmation. |
| Weaknesses  | Very noisy on 1-min; typically better applied to 5-min or 15-min resampled bars. |

---

## 3. Volatility-Based

**Core hypothesis:** Volatility is mean-reverting and clustered. Expansions
follow contractions (and vice versa), providing edge in timing entries before
large moves or fading spike exhaustion.

### 3.1 ATR Expansion / Contraction

| Attribute   | Detail |
|-------------|--------|
| Signal      | ATR(n) drops to multi-period low → expect volatility expansion; enter breakout on first large bar. ATR spike → potential exhaustion; fade or tighten stops. |
| Parameters  | ATR period (e.g. 14); lookback for ATR low (e.g. 50 bars). |
| Entry       | Long/short bias from existing trend; triggered by ATR expansion signal. |
| Exit        | Fixed ATR multiple; or when ATR contracts again. |
| Instruments | All. |
| Strengths   | ATR is one of the most reliable volatility measures; dynamically scales stops. |
| Weaknesses  | Does not provide directional bias on its own — must be combined with trend filter. |

### 3.2 Opening Range Breakout (ORB)

| Attribute   | Detail |
|-------------|--------|
| Signal      | Define the opening range (first N minutes of the session); enter long/short on breakout above/below range. |
| Parameters  | ORB duration (5, 15, 30 minutes); buffer size; session start time. |
| Entry       | First close outside range + optional volume confirmation. |
| Exit        | End-of-session flat; ATR trailing stop; or range opposite side as stop. |
| Instruments | EURUSD (London/NY open); XAUUSD (NY open); Crypto (24 h — arbitrary session start). |
| Strengths   | Well-documented in futures and equities; session open often has directional momentum. |
| Weaknesses  | Requires accurate session time definition; Crypto has no natural session; fake breakouts common on 1-min. |

### 3.3 Volatility Squeeze (Keltner + Bollinger)

| Attribute   | Detail |
|-------------|--------|
| Signal      | Bollinger Bands contract inside Keltner Channels ("squeeze") — low volatility consolidation; enter on first bar that breaks out of the squeeze. |
| Parameters  | BB period/σ; KC period/ATR multiplier; squeeze definition (BB inside KC). |
| Entry       | First bar after squeeze releases in direction of momentum (histogram of ROC). |
| Exit        | ATR trailing stop; or when BB expands fully. |
| Instruments | All; very popular on Crypto due to frequent consolidation periods. |
| Strengths   | Identifies low-risk high-reward entry points before large moves. |
| Weaknesses  | Direction of the breakout is not guaranteed by the squeeze alone; false breakouts common. |

### 3.4 Volatility Regime Filter

| Attribute   | Detail |
|-------------|--------|
| Signal      | Classify current market as low / medium / high volatility using rolling ATR or realized volatility percentile. Apply different strategies (or no strategy) per regime. |
| Parameters  | ATR lookback; percentile thresholds (e.g. < 30th = low, > 70th = high). |
| Role        | Meta-filter — not a standalone strategy. |
| Instruments | All. |
| Strengths   | Avoids applying trend strategies in choppy regimes and reversion strategies in trending regimes. |
| Weaknesses  | Regime boundaries are arbitrary; transitions can be slow. |

---

## 4. Pattern-Based

**Core hypothesis:** Recurring price formations reflect repeatable crowd
psychology and supply/demand imbalances, leading to statistically predictable
short-term outcomes.

### 4.1 Candlestick Patterns

| Attribute   | Detail |
|-------------|--------|
| Patterns    | Doji, Hammer, Shooting Star, Engulfing (bullish/bearish), Morning Star, Evening Star, Pin Bar, Inside Bar. |
| Signal      | Pattern detected at close of forming bar → directional bias for next 1–5 bars. |
| Parameters  | Body/wick ratio thresholds per pattern; confirmation bar requirement. |
| Entry       | On close of pattern bar, or on open of next bar. |
| Exit        | Fixed R:R target (1.5:1 or 2:1); ATR-based stop. |
| Instruments | All; pin bars and engulfing patterns are reliable at key S/R levels. |
| Strengths   | Objective when coded with strict ratio rules; widely observed. |
| Weaknesses  | On 1-min bars, many false positives; most meaningful at support/resistance confluence. |

### 4.2 Chart Patterns

| Attribute   | Detail |
|-------------|--------|
| Patterns    | Head & Shoulders, Double Top/Bottom, Triangles (ascending/descending/symmetrical), Wedges, Flags, Pennants. |
| Signal      | Pattern completion + neckline/trendline breakout → entry. |
| Parameters  | Swing detection sensitivity; breakout confirmation buffer. |
| Entry       | Breakout candle close; or retest of broken level. |
| Exit        | Pattern-projected target (measured move); or invalidation of pattern. |
| Instruments | All; triangles and flags are common on Crypto intraday. |
| Strengths   | Price targets are built into the pattern definition. |
| Weaknesses  | Pattern detection on 1-min is very noisy; requires higher TF (15-min, 1-h) for reliable setups. Harder to automate than indicator-based signals. |

### 4.3 Support & Resistance Levels

| Attribute   | Detail |
|-------------|--------|
| Signal      | Price approaches a previously established S/R level → fade (reversion trade) or trade breakout. |
| Level types | Swing highs/lows; round numbers (psychological levels); prior session high/low/close. |
| Parameters  | Swing detection lookback; proximity threshold (% or ATR); level invalidation rule. |
| Entry       | Bounce entry (reversion) or breakout-retest entry. |
| Exit        | Next S/R level as target; invalidation below/above level as stop. |
| Instruments | Round numbers highly relevant for EURUSD (1.1000, 1.0950), XAUUSD (2000, 2050), BTCUSD (round thousands). |
| Strengths   | S/R is a self-fulfilling mechanism used by most market participants. |
| Weaknesses  | Level detection algorithms produce many irrelevant levels; requires careful filtering. |

### 4.4 Fair Value Gaps (FVG / Imbalance)

| Attribute   | Detail |
|-------------|--------|
| Signal      | A 3-bar sequence where bar N+1's range does not overlap bar N-1 creates a gap (imbalance). Price tends to return to fill the gap. |
| Parameters  | Minimum gap size (in ATR or pips) to filter trivial gaps; gap validity window (expire after N bars unfilled). |
| Entry       | Price returns to fill the gap → trade in the original direction of the move that created it. |
| Exit        | Gap fully filled; or fixed ATR stop. |
| Instruments | All; heavily used in ICT / Smart Money Concepts (SMC) frameworks. |
| Strengths   | Objective detection; provides both entry price and target. |
| Weaknesses  | Not all gaps are filled; concept is recent and may be over-traded on well-known instruments. |

### 4.5 Order Blocks

| Attribute   | Detail |
|-------------|--------|
| Signal      | The last bearish/bullish bar before a significant impulsive move represents institutional order accumulation. Price returning to that zone tends to react. |
| Parameters  | Impulse magnitude threshold (e.g. ATR multiple); order block zone width; validity window. |
| Entry       | Price revisits order block zone → trade in direction of original impulse. |
| Exit        | Next structural target; stop below/above the order block. |
| Instruments | All (SMC framework origin is in Forex). |
| Strengths   | Complements FVG analysis; popular and well-documented in SMC community. |
| Weaknesses  | Subjective in manual analysis; programmatic definition requires careful codification. Edge may dilute as the concept becomes mainstream. |

---

## 5. Time-Based

**Core hypothesis:** Price behaviour exhibits systematic patterns tied to the
time of day, session overlap, and day of week, driven by the predictable
activity cycles of institutional participants.

### 5.1 Session Open / Close Effects

| Attribute   | Detail |
|-------------|--------|
| Sessions    | Asian (22:00–08:00 EET), London (08:00–16:00 EET), New York (13:00–21:00 EET). |
| Signal      | London open (08:00 EET) and NY open (13:00 EET) tend to produce directional moves; Asian session tends toward consolidation. |
| Entry       | ORB variant (see 3.2); or fade the pre-session range at London/NY open. |
| Exit        | Session close or end-of-day flat. |
| Instruments | EURUSD (strong session effects); XAUUSD (NY open dominant); Crypto (attenuated — 24 h market). |
| Notes       | All timestamps in our corpus are EET; session times need to account for DST. |

### 5.2 Time-of-Day Seasonality

| Attribute   | Detail |
|-------------|--------|
| Signal      | Certain hours of the day statistically have higher average returns or volatility. Apply strategy only during those windows. |
| Method      | Compute average return by hour-of-day across all available years; identify statistically significant hours. |
| Role        | Time filter — restrict entry window for any other strategy. |
| Instruments | All; must be computed per instrument since session structure differs. |
| Strengths   | Data-driven; easy to implement as a binary filter. |
| Weaknesses  | Non-stationary — the profitable hour may shift across years as market structure changes. |

### 5.3 Day-of-Week Seasonality

| Attribute   | Detail |
|-------------|--------|
| Signal      | Certain weekdays may have higher/lower directional bias (e.g. Monday reversals, Friday close effects). |
| Method      | Aggregate daily returns by weekday; test statistical significance. |
| Role        | Weekday filter on top of any other strategy. |
| Instruments | Forex (weekend gap on Monday relevant); Crypto (continuous, weaker weekend effect). |
| Weaknesses  | Signal is weak and may not survive transaction costs alone. Best used as a filter, not a standalone signal. |

---

## 6. Statistical & Quantitative

**Core hypothesis:** Price series exhibit statistical properties (autocorrelation,
cointegration, fractal structure) that can be exploited systematically.

### 6.1 Linear Regression Channel

| Attribute   | Detail |
|-------------|--------|
| Signal      | Fit a rolling linear regression to Close prices; trade the upper/lower channel bands (mean ± Nσ of residuals). |
| Parameters  | Regression window (e.g. 50–200 bars); channel width (σ multiplier). |
| Entry       | Price at ±channel edge → reversion toward regression line. |
| Exit        | Regression line (centre); or opposite channel band. |
| Instruments | All. |
| Strengths   | Adapts to the current trend slope; residuals are more stationary than raw price. |
| Weaknesses  | Regression line changes on every bar (look-ahead risk if not computed correctly). |

### 6.2 Kalman Filter Trend

| Attribute   | Detail |
|-------------|--------|
| Signal      | Kalman filter estimates the true underlying price trend dynamically; trade deviations from the filter as mean-reversion or use filter direction as trend signal. |
| Parameters  | Process noise (Q), measurement noise (R) — control smoothness. |
| Instruments | All; popular in quantitative Forex strategies. |
| Strengths   | Optimal linear estimator for Gaussian noise; very smooth with minimal lag compared to MAs. |
| Weaknesses  | Requires careful tuning of Q/R; less intuitive than standard indicators. |

### 6.3 Hurst Exponent Regime Detection

| Attribute   | Detail |
|-------------|--------|
| Signal      | H > 0.5 → trending regime (apply trend strategies); H < 0.5 → mean-reverting regime; H ≈ 0.5 → random walk (avoid trading). |
| Parameters  | Rolling window for Hurst estimation (e.g. 512 bars). |
| Role        | Meta-filter / regime classifier. |
| Instruments | All. |
| Strengths   | Theoretically grounded measure of market memory. |
| Weaknesses  | Estimation requires long windows (reduces responsiveness); multiple estimation methods give different results. |

### 6.4 Autocorrelation of Returns

| Attribute   | Detail |
|-------------|--------|
| Signal      | Significant positive autocorrelation at lag 1 → momentum trade; negative autocorrelation → mean-reversion trade. |
| Method      | Rolling ACF at lag 1 (and 2–5) on 1-min log-returns. |
| Role        | Regime classifier that directly measures the type of serial dependence present. |
| Instruments | All; measure per instrument and per session. |
| Strengths   | Direct empirical measure of whether trend-following or mean-reversion should be favoured at a given time. |
| Weaknesses  | ACF estimates are noisy on short windows; multiple testing risk. |

### 6.5 Cross-Instrument Spread / Pairs Trading

| Attribute   | Detail |
|-------------|--------|
| Signal      | Two cointegrated instruments (e.g. XAUUSD vs XAGUSD; BTCUSD vs ETHUSD) — trade the spread when it deviates from its long-run equilibrium. |
| Method      | Johansen or Engle-Granger cointegration test; trade spread z-score > ±2. |
| Parameters  | Cointegration lookback window; z-score threshold; hedge ratio (β). |
| Entry       | Buy underperformer, sell outperformer when spread is extreme. |
| Exit        | Spread reverts to mean. |
| Instruments | XAUUSD / XAGUSD (gold-silver ratio); BTCUSD / ETHUSD; BTCUSD / ADAUSD. |
| Strengths   | Market-neutral; edge independent of overall market direction. |
| Weaknesses  | Cointegration is not permanent — relationship can break (regime change); requires simultaneous execution on two instruments. |

---

## 7. Multi-Timeframe (MTF)

**Core hypothesis:** Combining signals from multiple timeframes reduces noise and
aligns trades with the prevailing directional bias of higher-TF participants.

### 7.1 Higher-TF Trend + Lower-TF Entry

| Attribute   | Detail |
|-------------|--------|
| Signal      | Use 1-h or 4-h bar to determine trend direction (e.g. price above/below EMA200 on 1-h); enter only in that direction on 1-min or 5-min signals. |
| Parameters  | Higher TF (15 min, 1 h, 4 h); trend indicator (EMA, MA slope, ADX). |
| Instruments | All; fundamental to most professional intraday approaches. |
| Strengths   | Filters counter-trend noise; aligns with larger time-scale participants. |
| Weaknesses  | May miss short counter-trend moves; still requires precise 1-min entry logic. |

### 7.2 Multi-TF Confluence

| Attribute   | Detail |
|-------------|--------|
| Signal      | Require the same signal (e.g. RSI oversold, near S/R, candlestick pattern) to appear on multiple timeframes simultaneously before entering. |
| Parameters  | Number of required confluences; specific conditions per TF. |
| Instruments | All. |
| Strengths   | Very high-quality entries; low false positive rate. |
| Weaknesses  | Low trade frequency; complex to implement correctly. |

---

## 8. Volume-Based

**Core hypothesis:** Tick-volume (or notional volume where available) is a proxy
for institutional participation. Unusual volume signals conviction behind a move.

> **Important:** Volume in the corpus may be tick-volume (number of ticks), not
> traded notional. Validate consistency before building volume-dependent
> strategies; prefer volume as a confirmation filter rather than a primary signal.

### 8.1 Volume Spike Detection

| Attribute   | Detail |
|-------------|--------|
| Signal      | Volume on bar N is > N× rolling average (e.g. 2× the 20-bar average) → high-conviction bar; trade the direction of the bar's close or breakout from its range. |
| Parameters  | Rolling average window; spike multiplier threshold. |
| Entry       | Same-direction breakout on the following bar, or on the spike bar itself. |
| Exit        | ATR trailing stop; reversion on follow-through failure. |
| Instruments | EURUSD, XAUUSD (more consistent volume data); verify Crypto volume first. |
| Weaknesses  | Tick-volume spikes may reflect broker-specific data artefacts rather than true institutional flow. |

### 8.2 OBV Divergence

| Attribute   | Detail |
|-------------|--------|
| Signal      | Price makes new high/low but OBV does not confirm → reversal signal. |
| Parameters  | OBV period; divergence detection window. |
| Entry       | Divergence confirmed over N bars. |
| Exit        | Fixed ATR stop; divergence resolved. |
| Instruments | All (with volume caveat above). |

### 8.3 Volume-Weighted Entry Timing

| Attribute   | Detail |
|-------------|--------|
| Signal      | Only enter positions when volume is above its rolling average — avoids thin-market false moves. |
| Role        | Entry filter — apply on top of any signal-generating strategy. |
| Instruments | All. |

---

## 9. Machine Learning–Assisted

**Core hypothesis:** Non-linear relationships between features (technical
indicators, price action, time features) and future returns can be learned from
historical data and exploited out-of-sample.

> These categories require careful cross-validation to avoid look-ahead bias and
> overfitting. Always use walk-forward or purged k-fold validation.

### 9.1 Feature-Based Classification

| Attribute   | Detail |
|-------------|--------|
| Signal      | Train a classifier (Random Forest, XGBoost, LightGBM) on a feature matrix derived from technical indicators and price action to predict the sign of the next N-bar return. |
| Features    | RSI, MACD, ATR, Bollinger %B, ROC, hour-of-day, day-of-week, spread, volume ratio, etc. |
| Labels      | Sign of log-return over next 1/5/15/60 bars; or threshold-based (only label large moves). |
| Entry       | Model probability > threshold → entry in predicted direction. |
| Exit        | Inverse probability signal, or fixed holding period. |
| Instruments | All; train per instrument (or per asset class). |
| Strengths   | Can discover non-linear feature interactions invisible to rule-based methods. |
| Weaknesses  | Prone to overfitting on financial time series; requires rigorous walk-forward validation; non-stationary features degrade out-of-sample. |
| Notes       | Best combined with GA/hyperparameter search (see `e0010_first_ensemble`). |

### 9.2 Sequence Models (LSTM / Transformer)

| Attribute   | Detail |
|-------------|--------|
| Signal      | Recurrent or attention-based model learns temporal dependencies in raw OHLCV or derived features to forecast direction or magnitude. |
| Input       | Sliding window of 1-min bars (or multi-TF concatenated). |
| Instruments | All; BTCUSD/ETHUSD have shorter history but higher signal-to-noise for ML. |
| Strengths   | Can capture complex temporal patterns; no manual feature engineering required if using raw OHLCV. |
| Weaknesses  | Data-hungry; computationally expensive; very high overfitting risk on financial data; difficult to interpret. |

### 9.3 Reinforcement Learning

| Attribute   | Detail |
|-------------|--------|
| Signal      | RL agent learns a policy (when to enter, hold, exit) directly from reward signals (P&L, Sharpe ratio). |
| Environment | Simulated market from 1-min bars; agent observes OHLCV window + portfolio state. |
| Instruments | All. |
| Strengths   | Directly optimises the trading objective; no need for separate signal and execution layers. |
| Weaknesses  | Very data-hungry; training instability; severe overfitting risk; highly experimental for live trading. Best treated as a research track rather than near-term deliverable. |

---

## Summary Matrix

Quick reference to compare categories across key dimensions:

| Category                     | Direction | Freq    | Complexity | Instruments       | TF Recommendation  |
|------------------------------|-----------|---------|------------|-------------------|--------------------|
| MA Crossover                 | Trend     | Medium  | Low        | All               | 5-min, 15-min      |
| Momentum / ROC               | Trend     | High    | Low        | Crypto, Metals    | 1-min, 5-min       |
| Breakout                     | Trend     | Low     | Low        | All               | 5-min, 15-min      |
| Donchian Breakout            | Trend     | Low     | Low        | Metals, Crypto    | 15-min, 1-h        |
| ADX Filter                   | Filter    | —       | Low        | All               | Any                |
| Bollinger Reversion          | Reversion | Medium  | Low        | Forex             | 5-min, 15-min      |
| RSI Extremes                 | Reversion | Low     | Low        | All               | 5-min, 15-min      |
| VWAP Deviation               | Reversion | Medium  | Medium     | Forex, Metals     | 1-min, 5-min       |
| Z-Score Reversion            | Reversion | Medium  | Low        | All               | 5-min              |
| Stochastic Reversion         | Reversion | Medium  | Low        | All               | 5-min, 15-min      |
| ATR Expansion                | Both      | Low     | Low        | All               | 1-min, 5-min       |
| ORB                          | Trend     | Very Low| Low        | Forex, Metals     | 5-min              |
| Volatility Squeeze           | Trend     | Low     | Medium     | Crypto            | 5-min, 15-min      |
| Volatility Regime Filter     | Filter    | —       | Low        | All               | Any                |
| Candlestick Patterns         | Both      | Low     | Medium     | All               | 5-min, 15-min      |
| Chart Patterns               | Both      | Very Low| High       | All               | 15-min, 1-h        |
| Support & Resistance         | Both      | Low     | Medium     | All               | 5-min, 15-min      |
| Fair Value Gaps              | Both      | Medium  | Medium     | All               | 1-min, 5-min       |
| Order Blocks                 | Both      | Low     | High       | All               | 5-min, 15-min      |
| Session Open/Close           | Trend     | Very Low| Medium     | Forex, Metals     | 5-min              |
| Time-of-Day Seasonality      | Filter    | —       | Low        | All               | Any                |
| Day-of-Week Seasonality      | Filter    | —       | Low        | All               | Any                |
| Linear Regression Channel    | Reversion | Medium  | Medium     | All               | 5-min, 15-min      |
| Kalman Filter Trend          | Both      | Medium  | High       | Forex             | 1-min, 5-min       |
| Hurst Exponent               | Filter    | —       | High       | All               | Any (long window)  |
| Autocorrelation Regime       | Filter    | —       | Medium     | All               | Any                |
| Pairs / Spread Trading       | Neutral   | Low     | High       | Metals, Crypto    | 5-min, 15-min      |
| MTF Trend + Entry            | Trend     | Low     | Medium     | All               | 1-min entry, ≥15-min filter |
| MTF Confluence               | Both      | Very Low| High       | All               | Multiple           |
| Volume Spike                 | Trend     | Low     | Low        | Forex, Metals     | 1-min, 5-min       |
| OBV Divergence               | Reversion | Low     | Medium     | All               | 5-min, 15-min      |
| Volume-Weighted Filter       | Filter    | —       | Low        | All               | Any                |
| Feature-Based Classification | Both      | High    | Very High  | All               | 5-min, 15-min      |
| LSTM / Transformer           | Both      | High    | Very High  | Crypto            | 5-min              |
| Reinforcement Learning       | Both      | High    | Very High  | All               | Research track     |

---

*Last updated: Phase 1 — initial catalog. Expand with per-strategy detail files as
research progresses.*
