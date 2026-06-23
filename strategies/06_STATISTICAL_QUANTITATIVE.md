# Category 6 — Statistical & Quantitative: Top 15 Strategies

Detailed research document for the **Statistical & Quantitative** strategy family.
Each strategy is documented with: core hypothesis, indicators and their mechanics,
standard parameters used in practice, entry/exit rules, and a **brute-force
parameter search space** suitable for exhaustive or grid-search optimization over
the `data/bars/` corpus.

All strategies operate on 1-minute bars or on bars resampled from them
(5 min, 15 min, 1 h). See `CATEGORIES.md` for context.

---

## Table of Contents

| # | Strategy | Complexity | Best TF |
|---|---|---|---|
| SQ-01 | Linear Regression Channel | Medium | 5-min, 15-min |
| SQ-02 | Kalman Filter Trend | High | 1-min, 5-min |
| SQ-03 | Hurst Exponent Regime Detection | High | Any (long window) |
| SQ-04 | Autocorrelation of Returns (Lag-1) | Medium | Any |
| SQ-05 | Cross-Instrument Pairs / Spread Trading | High | 5-min, 15-min |
| SQ-06 | Rolling Mean/Variance Breakout | Low | 5-min, 15-min |
| SQ-07 | Ornstein-Uhlenbeck Mean Reversion | High | 5-min, 15-min |
| SQ-08 | Cointegration-Based Spread Z-Score | High | 15-min, 1-h |
| SQ-09 | Adaptive Moving Average (KAMA) | Medium | 5-min, 15-min |
| SQ-10 | Fractal Dimension Regime Filter | High | Any |
| SQ-11 | Variance Ratio Test Regime Filter | Medium | Any |
| SQ-12 | Shannon Entropy Regime Filter | Medium | Any |
| SQ-13 | Rolling Beta to Market Filter | Medium | 5-min, 15-min |
| SQ-14 | Principal Component Direction (PCA) | High | 15-min, 1-h |
| SQ-15 | Statistical Arbitrage via Z-Score | High | 5-min, 15-min |

---

## SQ-01 — Linear Regression Channel

### Hypothesis

A rolling OLS linear regression fit to closing prices provides the "true" trend
direction with minimal lag, since it fits the entire lookback window rather than
weighting recent prices more. The residuals around the regression line are
approximately stationary — their standard deviation forms a natural channel.
Trading in the direction of the slope near the channel center, or fading the
outer bands as mean-reversion, provides two distinct edges.

### Indicators

- **LinReg(n):** OLS fit to the last `n` close prices. Slope indicates trend
  direction and magnitude (pips/bar or % per bar).
- **Residual σ:** Standard deviation of residuals `(Close − LinReg_fitted)`.
- **Channel:** `LinReg ± k × σ` — upper and lower bounds.
- **Predicted value:** LinReg line at the current bar (not the past endpoint).

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Regression period | 50, 100, 200 bars | Longer = smoother slope |
| Channel width (k) | 1.5, 2.0, 2.5 × σ | |
| Trend entry | Price above LinReg AND slope > 0 → long | |
| Reversion entry | Price at outer band → fade | |
| Stop | Opposite channel band or 1.5× ATR | |

### Brute-Force Parameter Search Space

```
linreg_period    : [30, 50, 75, 100, 150, 200]
channel_k        : [1.0, 1.5, 2.0, 2.5, 3.0]
entry_type       : ["trend_center", "reversion_outer"]
atr_stop_mult    : [1.0, 1.5, 2.0]
slope_filter     : [True, False]       # only trend trade if slope magnitude > threshold
timeframe        : [5min, 15min]
```

> **Look-ahead risk:** Ensure the LinReg value used is computed on bars
> [t−n+1, t], not using any future bars. The endpoint of the regression line
> at bar t is the current predicted value.

---

## SQ-02 — Kalman Filter Trend

### Hypothesis

A Kalman Filter is an optimal recursive linear estimator that dynamically
estimates the "true" underlying price (state) by minimizing mean squared error.
It adjusts its estimate based on the ratio of process noise (Q) to measurement
noise (R). With appropriate Q/R tuning, it produces a smooth trend estimate
with substantially less lag than EMA while adapting to changing market dynamics.

### Indicators

- **State estimate (x̂):** Kalman filter's best estimate of true price.
- **Gain (K):** Updated each bar based on Q/R ratio; determines how much new
  data updates the estimate.
- **Velocity estimate:** Second-order Kalman can estimate slope (rate of change).
- **Signal:** Price above Kalman estimate → bullish; below → bearish.
  Alternatively, Kalman slope direction.

### Kalman Filter Update Equations

```
# Prediction
x_pred = x_prev + v_prev          # position + velocity
v_pred = v_prev                    # constant velocity model

# Update
K = P_pred / (P_pred + R)         # Kalman gain
x_est = x_pred + K * (Close - x_pred)
P = (1 - K) * P_pred + Q
```

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Process noise (Q) | 0.001–0.1 | Low Q = very smooth (slow to adapt) |
| Measurement noise (R) | 0.1–10.0 | High R = rely more on model |
| Order | 1 (position) or 2 (position + velocity) | 2nd order adds slope estimate |

### Brute-Force Parameter Search Space

```
Q                : [0.001, 0.005, 0.01, 0.05, 0.1]
R                : [0.1, 0.5, 1.0, 5.0, 10.0]
order            : [1, 2]
signal_type      : ["price_vs_kalman", "kalman_slope"]
slope_threshold  : [0.0, 0.00001, 0.00005]    # minimum slope to enter
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [1min, 5min]
```

---

## SQ-03 — Hurst Exponent Regime Detection

### Hypothesis

The Hurst exponent H measures the long-range dependence of a time series.
H > 0.5 indicates persistent, trending behavior (momentum strategies work);
H < 0.5 indicates anti-persistent, mean-reverting behavior (reversion strategies
work); H ≈ 0.5 is a random walk (avoid trading). Rolling estimation of H
allows real-time regime switching between trend and mean-reversion strategies.

### Estimation Method

The Rescaled Range (R/S) method is most common for financial data:

```
1. Compute log-returns of the series.
2. Divide into n sub-periods of length m.
3. For each sub-period: compute range R and std S of cumulative deviations.
4. Hurst exponent H ≈ slope of log(R/S) vs log(m).
```

Alternative: Detrended Fluctuation Analysis (DFA), which is more robust.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Estimation window | 256, 512, 1024 bars | Larger = more accurate, less responsive |
| Method | R/S, DFA | DFA preferred for detrended series |
| Trending threshold | H > 0.55 | |
| Reverting threshold | H < 0.45 | |
| Random walk zone | 0.45 ≤ H ≤ 0.55 → no trading | |

### Usage

Apply as a meta-filter:
- H > 0.55: activate trend strategies (Category 1).
- H < 0.45: activate mean-reversion strategies (Category 2).
- 0.45 ≤ H ≤ 0.55: disable all strategies or reduce position size.

### Brute-Force Parameter Search Space

```
estimation_window: [256, 512, 1024]
method           : ["rs", "dfa"]
trending_threshold: [0.50, 0.55, 0.60]
reverting_threshold: [0.50, 0.45, 0.40]
strategy_trend   : ["ema_crossover", "supertrend", "macd"]
strategy_reversion: ["bb_reversion", "rsi2", "zscore"]
timeframe        : [5min, 15min, 1h]
```

---

## SQ-04 — Autocorrelation of Returns (Lag-1)

### Hypothesis

The lag-1 autocorrelation of log-returns measures whether consecutive returns
tend to be in the same direction (positive AC → momentum) or opposite direction
(negative AC → mean-reversion). A rolling lag-1 AC estimate provides a
real-time measure of the current market's behavior style, enabling adaptive
strategy selection more responsive than the Hurst exponent.

### Method

```
1. Compute log-returns: r_t = log(Close_t / Close_{t-1})
2. Rolling lag-1 AC: AC_1(t) = corr(r_{t-n:t}, r_{t-n-1:t-1}) over window n
3. AC_1 > threshold → momentum trade; AC_1 < -threshold → mean-reversion trade
```

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| AC window | 30, 60, 120, 240 bars | Shorter = noisier but more responsive |
| Momentum threshold | AC_1 > 0.10 | |
| Reversion threshold | AC_1 < −0.10 | |
| Neutral zone | −0.10 to +0.10 → no trading | |

### Brute-Force Parameter Search Space

```
ac_window        : [20, 30, 60, 120, 240]
momentum_thresh  : [0.05, 0.10, 0.15, 0.20]
reversion_thresh : [-0.05, -0.10, -0.15, -0.20]
strategy_momentum: ["ema_crossover", "supertrend"]
strategy_reversion: ["bb_reversion", "rsi2"]
timeframe        : [5min, 15min, 1h]
```

### Instrument Suitability

All instruments; compute per instrument as autocorrelation behavior differs.
EURUSD has slightly positive lag-1 AC during trending sessions. BTCUSD shows
more variable AC.

---

## SQ-05 — Cross-Instrument Pairs / Spread Trading

### Hypothesis

Cointegrated instruments share a long-run equilibrium — deviations from this
equilibrium are temporary and tend to mean-revert. Trading the spread between
two cointegrated instruments (buy the underperformer, sell the outperformer)
when the spread z-score exceeds ±2 provides a market-neutral edge independent
of overall market direction.

### Candidate Pairs in Corpus

| Pair | Instruments | Rationale |
|---|---|---|
| Gold/Silver | XAUUSD / XAGUSD | Gold-silver ratio is historically mean-reverting |
| BTC/ETH | BTCUSD / ETHUSD | High correlation; ETH often leads/lags BTC |
| BTC/ADA | BTCUSD / ADAUSD | Crypto correlation pairs |
| ETH/AVE | ETHUSD / AVEUSD | DeFi correlation |

### Method

1. Test cointegration (Engle-Granger or Johansen) over a rolling window.
2. If cointegrated, estimate hedge ratio β: `Spread = Price_A − β × Price_B`.
3. Compute rolling spread z-score.
4. Enter when z > +2 (sell A, buy B) or z < −2 (buy A, sell B).
5. Exit when z returns to 0.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Cointegration window | 500, 1000, 2000 bars |
| Hedge ratio method | OLS, Johansen |
| Z-score window | 60, 120, 240 bars |
| Entry threshold | ±1.5, ±2.0, ±2.5 |
| Exit threshold | ±0.5, 0.0 |

### Brute-Force Parameter Search Space

```
coint_window     : [500, 1000, 2000]
hedge_method     : ["ols", "johansen"]
zscore_window    : [60, 120, 240]
entry_z          : [1.5, 2.0, 2.5, 3.0]
exit_z           : [0.0, 0.5]
stop_z           : [3.0, 4.0]            # exit if z extends further
timeframe        : [5min, 15min]
```

### Notes

Cointegration is not permanent. Always re-test cointegration on a rolling basis.
If the pair fails the cointegration test, disable trading until it re-establishes.
Requires simultaneous execution on two instruments.

---

## SQ-06 — Rolling Mean/Variance Breakout

### Hypothesis

Combining a rolling mean and variance in a dynamic threshold creates a
statistically-adaptive breakout signal. Rather than using a fixed ATR multiple,
this approach normalizes price movements by the rolling standard deviation.
When the current bar's return exceeds the rolling mean return by a statistically
significant multiple of the rolling std, it indicates an unusual directional
event — a potential breakout.

### Indicators

- **Rolling mean return:** `mean(r, n)` over n bars.
- **Rolling std:** `std(r, n)` over n bars.
- **Standardized return:** `(r_t − mean) / std` — z-score of current return.
- **Signal:** Standardized return > threshold → enter in direction of the outlier.

### Brute-Force Parameter Search Space

```
window           : [20, 30, 60, 120]
threshold_z      : [1.5, 2.0, 2.5, 3.0]
signal_direction : ["same_as_outlier", "reversion"]
atr_stop_mult    : [1.0, 1.5, 2.0]
hold_bars        : [5, 10, 20]
timeframe        : [5min, 15min]
```

---

## SQ-07 — Ornstein-Uhlenbeck Mean Reversion

### Hypothesis

The Ornstein-Uhlenbeck (OU) process models a mean-reverting stochastic process:
`dX = θ(μ − X)dt + σdW`, where θ is the mean-reversion speed, μ is the
long-run mean, and σ is volatility. Fitting an OU model to price deviations
from a trend (spread z-score, residuals, or log-price) allows estimation of
the expected half-life of mean reversion — critical for setting holding periods
and stop-loss levels.

### Method

1. Extract a mean-reverting series (e.g. spread residuals from SQ-05, or
   price detrended by LinReg from SQ-01).
2. Fit OU model: estimate θ (reversion rate) and μ (equilibrium).
3. Compute half-life: `HL = ln(2) / θ`.
4. Enter when deviation > 2σ from μ; hold for ~HL bars.
5. Set stop at 3σ from μ.

### Key Metrics

| Parameter | Interpretation |
|---|---|
| θ (reversion rate) | Higher = faster reversion; HL = ln(2)/θ |
| μ (equilibrium mean) | Target price for exit |
| σ (volatility) | Controls position sizing |
| Half-life | Expected bars to revert halfway; sets holding period |

### Brute-Force Parameter Search Space

```
fitting_window   : [60, 120, 240, 500]    # bars for OU estimation
series_type      : ["spread", "residuals", "price_detrended"]
entry_z          : [1.5, 2.0, 2.5]
exit_z           : [0.0, 0.5]
stop_z           : [3.0, 4.0]
hold_mult        : [0.5, 1.0, 2.0]        # hold = HL × mult
timeframe        : [5min, 15min]
```

---

## SQ-08 — Cointegration-Based Spread Z-Score

### Hypothesis

A simpler implementation than full OU fitting (SQ-07): once cointegration is
established between two instruments (SQ-05), the rolling z-score of the spread
provides a clean mean-reversion signal without requiring the full OU estimation.
The z-score automatically adjusts to the current spread volatility regime.

### Method

1. Compute spread: `Spread_t = Price_A_t − β × Price_B_t` (β from SQ-05).
2. Rolling z-score: `z_t = (Spread_t − mean(Spread, n)) / std(Spread, n)`.
3. Enter when `|z_t| > entry_threshold`; exit when `|z_t| < exit_threshold`.

### Brute-Force Parameter Search Space

```
spread_window    : [60, 120, 240]
entry_z          : [1.5, 2.0, 2.5]
exit_z           : [0.0, 0.5]
stop_z           : [3.0, 4.0, 5.0]
beta_update      : ["rolling_60", "rolling_120", "static"]
timeframe        : [5min, 15min]
```

---

## SQ-09 — Adaptive Moving Average (KAMA)

### Hypothesis

Kaufman's Adaptive Moving Average (KAMA) adjusts its smoothing constant based
on the current market efficiency ratio (ER): `ER = |price_change| / sum(|bar_changes|)`.
When ER is high (trending), KAMA tracks price closely (fast EMA). When ER is
low (choppy), KAMA barely moves. This makes KAMA direction and slope particularly
reliable signals, filtering out much of the noise that plagues standard EMAs.

### Indicators

- **Efficiency Ratio (ER):** `|Close − Close[−n]| / sum(|Close[i] − Close[i−1]|, n)`.
  Range 0 (pure noise) to 1 (pure trend).
- **Smoothing constant (SC):** `(ER × (fast_sc − slow_sc) + slow_sc)^2`
  where `fast_sc = 2/(fast+1)`, `slow_sc = 2/(slow+1)`.
- **KAMA:** `KAMA_prev + SC × (Close − KAMA_prev)`.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| ER period | 10 | Lookback for efficiency ratio |
| Fast SC period | 2 | Tracks price in trending markets |
| Slow SC period | 30 | Barely moves in choppy markets |
| Signal | KAMA slope change, or price/KAMA crossover | |

### Brute-Force Parameter Search Space

```
er_period        : [5, 10, 14, 20]
fast_period      : [2, 3]
slow_period      : [20, 30, 50]
signal_type      : ["kama_slope", "price_kama_cross"]
slope_bars       : [1, 2, 3]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## SQ-10 — Fractal Dimension Regime Filter

### Hypothesis

The Fractal Dimension (FD) of a price series measures its complexity. FD = 1.5
approximates a random walk (Brownian motion). FD → 1.0 indicates a smooth
trending series (low complexity). FD → 2.0 indicates a very jagged, choppy
series. A rolling FD estimate can distinguish trending (FD < 1.4) from choppy
(FD > 1.6) regimes, enabling adaptive strategy selection.

### Estimation Method

```
1. Compute price range over N bars: H_max = max(High), L_min = min(Low)
2. Compute sum of single-bar ranges: sum_range = sum(High - Low, N)
3. FD = 1 + log(sum_range / (H_max - L_min)) / log(N)
```

Alternative: Box-counting method or variance method.

### Standard Parameters

| Parameter | Common values |
|---|---|
| FD window | 20, 30, 50, 100 bars |
| Trending threshold | FD < 1.40 |
| Choppy threshold | FD > 1.60 |
| Neutral zone | 1.40–1.60 |

### Usage

Same meta-filter application as SQ-03 (Hurst) but with FD:
- FD < 1.40 → trend strategies.
- FD > 1.60 → mean-reversion or no trade.

### Brute-Force Parameter Search Space

```
fd_window        : [20, 30, 50, 100]
trending_thresh  : [1.35, 1.40, 1.45]
choppy_thresh    : [1.55, 1.60, 1.65]
strategy_trend   : ["ema_crossover", "supertrend"]
strategy_reversion: ["bb_reversion", "zscore"]
timeframe        : [5min, 15min, 1h]
```

---

## SQ-11 — Variance Ratio Test Regime Filter

### Hypothesis

The Variance Ratio (VR) test compares the variance of q-period returns to the
variance of 1-period returns: `VR(q) = Var(r_q) / (q × Var(r_1))`. For a
random walk, VR ≈ 1. VR > 1 indicates positive serial correlation (momentum);
VR < 1 indicates negative serial correlation (mean-reversion). A rolling VR
estimate provides a regime filter similar to autocorrelation (SQ-04) but with
different statistical properties.

### Standard Parameters

| Parameter | Common values |
|---|---|
| VR lag q | 2, 4, 8, 16 |
| Window | 60, 120, 240 bars |
| Momentum threshold | VR > 1.05 |
| Reversion threshold | VR < 0.95 |

### Brute-Force Parameter Search Space

```
vr_lag           : [2, 4, 8, 16]
vr_window        : [60, 120, 240]
momentum_thresh  : [1.03, 1.05, 1.10]
reversion_thresh : [0.97, 0.95, 0.90]
strategy_momentum: ["ema_crossover", "supertrend"]
strategy_reversion: ["bb_reversion", "zscore"]
timeframe        : [5min, 15min]
```

---

## SQ-12 — Shannon Entropy Regime Filter

### Hypothesis

Shannon entropy of a discretized return distribution measures the uncertainty
(disorder) in the price series. Low entropy indicates a predictable, directed
series (trending regime). High entropy indicates maximum uncertainty (random
walk or complex dynamics). Rolling entropy estimation provides yet another
lens for regime classification.

### Method

1. Discretize log-returns into bins (e.g. 5 bins based on std).
2. Compute probability of each bin over a rolling window.
3. Entropy: `H = −sum(p_i × log(p_i))`.
4. Normalize: `H_norm = H / log(n_bins)` → range [0, 1].
5. Low `H_norm` → low entropy → trending. High → choppy.

### Brute-Force Parameter Search Space

```
entropy_window   : [30, 60, 120]
n_bins           : [5, 8, 10]
low_entropy_thresh: [0.3, 0.4, 0.5]     # below = trending regime
high_entropy_thresh: [0.7, 0.8, 0.9]    # above = random/choppy
strategy_low_ent : ["ema_crossover", "supertrend"]
strategy_high_ent: ["bb_reversion", "vwap_fade"]
timeframe        : [5min, 15min]
```

---

## SQ-13 — Rolling Beta to Reference Asset

### Hypothesis

The rolling correlation and beta of one instrument relative to a reference
(e.g. BTCUSD as reference for ETHUSD, or EURUSD as reference for XAGUSD)
can identify when the pair relationship is unusually strong or weak. High beta
with high correlation: trade the pair together (ride the lead/lag). Low beta
or decoupling: the pair relationship has changed — potential spread trade or
standalone signal.

### Method

1. Compute rolling beta: `β = Cov(r_A, r_B) / Var(r_B)` over N bars.
2. Compute rolling correlation: `ρ = β × Var(r_B) / (std(r_A) × std(r_B))`.
3. Signal: high ρ (> 0.8) + ρ decoupling → anticipate reversion to historical β.

### Brute-Force Parameter Search Space

```
beta_window      : [30, 60, 120, 240]
high_corr_thresh : [0.7, 0.8, 0.90]
decoupling_thresh: [0.1, 0.2, 0.3]      # correlation drop from rolling max
instrument_pair  : [("BTCUSD","ETHUSD"), ("XAUUSD","XAGUSD")]
timeframe        : [5min, 15min, 1h]
```

---

## SQ-14 — Principal Component Analysis (PCA) Direction

### Hypothesis

Applied to a panel of correlated instruments (e.g. all crypto assets), PCA
extracts the dominant directional factor (PC1). This "market factor" represents
the common systemic move across all assets. The deviation of an individual
asset from the market factor represents its idiosyncratic component — which
may mean-revert faster than the absolute price series.

### Method

1. Compute log-returns for all instruments over a rolling window.
2. Standardize returns (z-score across instruments).
3. Compute PCA; extract PC1 (first principal component = market factor).
4. Compute each instrument's residual: `r_residual = r_instrument − PC1_loading × PC1`.
5. Trade the residual as a mean-reverting series using SQ-04 or SQ-05 methods.

### Brute-Force Parameter Search Space

```
pca_window       : [60, 120, 240]
n_components     : [1, 2]               # use 1 or 2 dominant PCs
entry_z_residual : [1.5, 2.0, 2.5]
exit_z_residual  : [0.0, 0.5]
stop_z_residual  : [3.0, 4.0]
instruments      : [["BTCUSD","ETHUSD","ADAUSD"], ["XAUUSD","XAGUSD"]]
timeframe        : [15min, 1h]
```

---

## SQ-15 — Statistical Arbitrage via Z-Score

### Hypothesis

Combining elements of SQ-05, SQ-07, and SQ-08, this strategy implements a
complete statistical arbitrage (stat arb) framework: identify cointegrated
pairs, model the spread as an OU process, and trade using a z-score entry
with the OU half-life defining the holding period. This is the most complete
and institutionally rigorous implementation of pairs trading in this corpus.

### Method

1. Identify cointegrated pairs (Engle-Granger test, rolling window).
2. Compute spread and fit OU model to get θ, μ, σ, half-life.
3. Compute spread z-score.
4. Enter at `|z| > 2`; exit at `|z| < 0.5`.
5. Set maximum holding period to 2× half-life; stop at `|z| > 4`.

### Brute-Force Parameter Search Space

```
coint_window     : [500, 1000, 2000]
ou_fit_window    : [120, 240, 500]
entry_z          : [1.5, 2.0, 2.5, 3.0]
exit_z           : [0.0, 0.25, 0.5]
stop_z           : [3.0, 4.0]
max_hold_mult    : [1.0, 2.0, 3.0]      # max_hold = HL × mult
beta_method      : ["ols", "tls"]       # total least squares for symmetric spread
timeframe        : [5min, 15min]
```

---

## Cross-Strategy Considerations

### Computational Complexity

Statistical strategies tend to be more compute-intensive than indicator-based
strategies. Key optimizations:

| Strategy | Optimization |
|---|---|
| SQ-01 LinReg | Incremental update using Welford's algorithm |
| SQ-02 Kalman | Natural incremental; negligible overhead |
| SQ-03 Hurst | Pre-compute on rolling basis; cache 512-bar windows |
| SQ-05 Pairs | Vectorize using Numba on aligned price arrays |
| SQ-07 OU | Fit once per day; update parameters daily |

### Regime Filter Hierarchy

When multiple regime filters are available, their correlation matters:

| Filters | Correlation | Recommendation |
|---|---|---|
| Hurst + FD | High | Use one, not both |
| Hurst + ACF | Medium | Can combine |
| ACF + VR | High | Very similar signals |
| Entropy + Hurst | Low | Good complementary pair |

### Suggested Evaluation Priority

| Priority | Strategy | Reason |
|---|---|---|
| 1 | SQ-01 Linear Regression Channel | Clean signal; low look-ahead risk; adaptable |
| 2 | SQ-05 Pairs Trading (XAUUSD/XAGUSD) | Strong cointegration candidate; market-neutral |
| 3 | SQ-09 KAMA | Practical adaptive MA; easy to implement with Numba |
| 4 | SQ-04 Autocorrelation Filter | Directly measures momentum vs. reversion |
| 5 | SQ-02 Kalman Filter | Minimal lag; excellent for 1-min/5-min trend |
| 6 | SQ-03 Hurst Exponent | Theoretically grounded regime classifier |
| 7 | SQ-07 OU Mean Reversion | Rigorous mean-reversion timing |
| 8 | SQ-15 Stat Arb | Complete pairs framework; highest complexity |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
