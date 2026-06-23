# Category 9 — Machine Learning–Assisted: Top 10 Strategies

Detailed research document for the **Machine Learning–Assisted** strategy family.
Each strategy is documented with: core hypothesis, model architecture and
features, training methodology, validation requirements, and a **parameter
search space** suitable for systematic experiments over the `data/bars/` corpus.

> **Critical warning on validation:** Financial time series exhibit temporal
> structure, regime shifts, and non-stationarity. Standard cross-validation
> (k-fold with random splits) is **not valid** for financial ML — it introduces
> look-ahead bias. All ML strategies in this document require:
> - **Walk-forward validation** (expanding or rolling window training/test splits).
> - **Purged k-fold** (if cross-validation is used, with a gap between train and test).
> - Separate in-sample, out-of-sample, and optionally a held-out final evaluation set.
> - Out-of-sample evaluation on ≥ 1 year of unseen data.

---

## Table of Contents

| # | Strategy | Complexity | Compute | Best TF |
|---|---|---|---|---|
| ML-01 | Feature-Based Classification (XGBoost / RF) | Very High | Medium | 5-min, 15-min |
| ML-02 | Gradient Boosting with Walk-Forward Validation | Very High | Medium | 5-min, 15-min |
| ML-03 | K-Nearest Neighbors Pattern Matching | High | Low | 5-min, 15-min |
| ML-04 | Support Vector Machine (SVM) Classification | High | Medium | 5-min, 15-min |
| ML-05 | LSTM Sequence Model | Very High | Very High | 5-min |
| ML-06 | Transformer-Based Forecasting | Very High | Very High | 5-min, 15-min |
| ML-07 | Reinforcement Learning Agent | Very High | Very High | 5-min |
| ML-08 | Genetic Algorithm Parameter Optimization | High | High | Any |
| ML-09 | Bayesian Optimization for Strategy Parameters | High | Medium | Any |
| ML-10 | Ensemble Voting Classifier | Very High | Medium | 5-min, 15-min |

---

## ML-01 — Feature-Based Classification (XGBoost / Random Forest)

### Hypothesis

A supervised classifier trained on a feature matrix derived from technical
indicators and price action can predict the sign of the next N-bar return.
Tree-based models (XGBoost, LightGBM, Random Forest) are particularly suited
to financial data because they handle non-linear feature interactions, are
robust to feature scaling, and provide feature importance for interpretability.

### Feature Engineering

| Feature category | Examples |
|---|---|
| Trend | EMA(9)/EMA(21) ratio; EMA(50) slope; close/EMA(200) |
| Momentum | RSI(14); MACD histogram; ROC(10, 30) |
| Volatility | ATR(14) percentile; Bollinger %B; BBW percentile |
| Volume | Volume ratio (vol/mean); MFI; CMF |
| Time | Hour-of-day (EET); day-of-week; minutes-since-session-open |
| Pattern | Engulfing indicator; pin bar indicator; inside bar indicator |
| Multi-TF | HTF EMA slope; HTF RSI; prior session high/low relative position |

### Label Construction

```python
# Sign of N-bar forward return
label = np.sign(close_shifted_-N - close) where N in [1, 5, 10, 20]

# Threshold-based label (avoids labeling noise)
label = +1 if forward_return > +threshold
       -1 if forward_return < -threshold
        0 if |forward_return| < threshold  # neutral — skip
```

### Walk-Forward Validation Protocol

```
Total data: e.g. 2003–2024 (EURUSD)
In-sample window: 2 years rolling
Out-of-sample test: 6 months
Step: 6 months
→ Produces ~42 walk-forward periods
```

### Brute-Force Parameter Search Space

```
label_horizon_bars   : [1, 5, 10, 20]
label_threshold      : [0.0, 0.5× ATR, 1.0× ATR]    # 0 = any direction
features             : ["basic", "extended", "full"]   # feature set versions
model                : ["xgboost", "lightgbm", "random_forest"]
n_estimators         : [100, 300, 500]
max_depth            : [3, 5, 7]
min_samples_leaf     : [20, 50, 100]
probability_threshold: [0.55, 0.60, 0.65]             # confidence to enter
train_years          : [1, 2, 3]
retrain_freq         : ["monthly", "quarterly"]
timeframe            : [5min, 15min]
```

### Instrument Suitability

All instruments. Train per instrument — parameters and features that work on
EURUSD may not transfer to BTCUSD due to different volatility characteristics
and institutional participant mix.

### Overfitting Guards

1. Limit feature count relative to sample size: < 50 features per 5,000 samples.
2. Minimum leaf size: force at least 20–50 samples per leaf.
3. Out-of-sample Sharpe > 0.8 before considering live deployment.
4. Compare feature importance across walk-forward periods — unstable importance
   indicates overfit features.

---

## ML-02 — Gradient Boosting with Walk-Forward Validation

### Hypothesis

LightGBM or XGBoost with careful hyperparameter tuning and strict walk-forward
validation is the most practical and interpretable ML approach for intraday
financial forecasting. The key differentiation from ML-01 is the explicit focus
on the walk-forward framework and regularization as the primary tool against
overfitting — not model complexity.

### Key Distinction from ML-01

ML-02 emphasizes:
- Aggressive regularization (`lambda`, `alpha`, `min_child_weight`).
- Early stopping on a validation window immediately following the training window
  (not a random split).
- Feature selection based on walk-forward feature stability, not just importance
  on a single in-sample window.

### Training Protocol

```
For each walk-forward step:
  1. Train on bars [t-train_bars, t]
  2. Validation window for early stopping: [t, t+val_bars]
  3. Evaluate on test window: [t+val_bars, t+val_bars+test_bars]
  4. Record test metrics: Sharpe, profit factor, win rate, drawdown
  5. Move window forward by step_bars
```

### Brute-Force Parameter Search Space

```
train_bars       : [10000, 20000, 50000]
val_bars         : [2000, 5000]
test_bars        : [5000, 10000]
step_bars        : [2500, 5000]
num_leaves       : [15, 31, 63]
learning_rate    : [0.01, 0.05, 0.1]
reg_lambda       : [0.1, 1.0, 10.0]
min_child_weight : [50, 100, 200]
early_stop_rounds: [20, 50, 100]
label_horizon    : [5, 10, 20]
timeframe        : [5min, 15min]
```

---

## ML-03 — K-Nearest Neighbors Pattern Matching

### Hypothesis

KNN retrieves the K most similar historical price patterns to the current
context and uses their subsequent outcomes to predict the next move. Unlike
parametric models, KNN makes no assumptions about the data distribution —
it purely asks "when the market looked like this before, what happened next?"
This makes it a useful baseline and can capture local non-stationarities.

### Method

1. Define a feature vector for each bar (e.g. last N normalized returns,
   current RSI, MACD histogram, BBW percentile).
2. Find K nearest neighbors in the training set using Euclidean or cosine distance.
3. Aggregate neighbors' forward returns (mean, median, or vote on sign).
4. Enter long if predicted return > threshold; short if < −threshold.

### Implementation Notes

- Normalize all features before distance computation.
- Use `sklearn.neighbors.NearestNeighbors` with a ball tree for efficiency.
- Lookback window for "pattern" should be short (5–20 bars) to keep distances
  meaningful.

### Brute-Force Parameter Search Space

```
pattern_bars     : [5, 10, 15, 20]          # bars in the pattern vector
n_neighbors      : [10, 20, 50, 100]
distance_metric  : ["euclidean", "cosine"]
feature_set      : ["raw_returns", "normalized_indicators"]
label_horizon    : [5, 10, 20]
prediction_thresh: [0.0, 0.001, 0.002]
train_years      : [2, 3, 5]
timeframe        : [5min, 15min]
```

---

## ML-04 — Support Vector Machine (SVM) Classification

### Hypothesis

SVMs with RBF kernel find a maximum-margin hyperplane separating bullish and
bearish outcomes in a high-dimensional feature space. They are particularly
effective when the number of features is large relative to the number of samples,
and when the decision boundary is non-linear. On financial data, SVMs with
careful feature engineering can outperform simpler baselines.

### Method

1. Construct normalized feature matrix (same as ML-01 features).
2. Train SVM with RBF kernel on in-sample data.
3. Predict class probabilities using Platt scaling (`probability=True`).
4. Enter when predicted probability exceeds threshold.

### Notes

SVMs do not scale well to very large datasets (slow training on > 50,000
samples). Consider training on a sampled subset or using a linear SVM (SGD)
for large datasets.

### Brute-Force Parameter Search Space

```
kernel           : ["rbf", "linear"]
C                : [0.1, 1.0, 10.0, 100.0]    # regularization
gamma            : ["scale", "auto", 0.001, 0.01]
probability_thresh: [0.55, 0.60, 0.65]
feature_set      : ["basic", "extended"]
label_horizon    : [5, 10, 20]
train_sample_size: [5000, 10000, 20000]
timeframe        : [5min, 15min]
```

---

## ML-05 — LSTM Sequence Model

### Hypothesis

Long Short-Term Memory (LSTM) networks learn temporal dependencies in sequential
data through gated recurrent units. Applied to a sliding window of normalized
OHLCV bars (and derived features), an LSTM can potentially capture complex
multi-bar patterns that cannot be expressed as simple indicator combinations.
The architecture naturally handles the sequential structure of bar data.

### Architecture

```
Input: (batch, seq_len, n_features) where:
  - seq_len: 30–120 bars
  - n_features: OHLCV + indicators = 10–30

LSTM layers: 1–3 stacked layers, 32–128 units each
Dropout: 0.2–0.5 between layers
Output: Dense(1) with sigmoid for binary classification
         or Dense(3) with softmax for (buy, sell, hold)

Optimizer: Adam, lr=0.001–0.0001
Loss: Binary crossentropy or categorical crossentropy
```

### Walk-Forward Protocol

Same as ML-02 but with Keras/PyTorch LSTM. Retrain from scratch each step
(no weight transfer — financial data distribution shifts make transfer risky).

### Brute-Force Parameter Search Space

```
seq_len          : [30, 60, 120]
lstm_units       : [32, 64, 128]
n_layers         : [1, 2, 3]
dropout          : [0.2, 0.3, 0.5]
label_horizon    : [5, 10, 20]
batch_size       : [32, 64]
epochs_max       : [50]              # use early stopping
early_stop_patience: [5, 10]
learning_rate    : [0.001, 0.0005]
feature_set      : ["ohlcv_normalized", "ohlcv_plus_indicators"]
timeframe        : [5min]
```

### Caveats

- Training time is significant: ~5–30 minutes per walk-forward step per GPU.
- Very high overfitting risk on financial time series.
- Requires GPU for practical grid search. On CPU, restrict to small grids.
- Treat as a research track with high computational cost.

---

## ML-06 — Transformer-Based Forecasting

### Hypothesis

Transformer models with self-attention can capture long-range temporal
dependencies that LSTMs struggle with. Applied to multi-bar intraday sequences,
a transformer encoder can learn which historical time steps are most predictive
for the current bar's forecast. Temporal fusion transformers (TFT) extend this
with explicit handling of known future inputs (time features) and past observed
inputs (OHLCV).

### Architecture Options

| Architecture | Complexity | Notes |
|---|---|---|
| Vanilla Transformer Encoder + head | Medium | Self-attention on sequence |
| Temporal Fusion Transformer (TFT) | High | Handles mixed input types well |
| PatchTST | Medium | Treats bar sequence as patches |
| Informer | High | Long-sequence efficiency |

### Practical Notes

- TFT is the most suited architecture for tabular time series like OHLCV bars.
- Use positional encoding based on time (hour of day, day of week) rather than
  just sequence position.
- Very data-hungry: minimum 50,000 training samples recommended.
- Suitable for 5-min bars on EURUSD or XAUUSD with years of history.

### Brute-Force Parameter Search Space

```
architecture     : ["transformer_encoder", "tft", "patchtst"]
seq_len          : [48, 96, 192]            # bars (5-min: 48=4h, 96=8h)
d_model          : [32, 64, 128]
n_heads          : [4, 8]
n_layers         : [2, 4, 6]
dropout          : [0.1, 0.2, 0.3]
label_horizon    : [5, 10, 20]
timeframe        : [5min]
```

---

## ML-07 — Reinforcement Learning Agent

### Hypothesis

A Reinforcement Learning (RL) agent learns a policy — when to enter, hold, or
exit positions — directly from interaction with a simulated trading environment.
The reward signal (e.g. Sharpe ratio increment, log P&L, or risk-adjusted
return) shapes the policy without needing explicit price direction labels. The
agent can potentially discover non-trivial execution strategies that hand-coded
rules cannot capture.

### Environment Specification

```python
Observation:
  - Last N bars of OHLCV (normalized)
  - Current position (long, flat, short)
  - Current P&L
  - Time features (hour, day)

Action space:
  - Discrete(3): BUY, HOLD, SELL
  - Or continuous: position size in [-1, +1]

Reward:
  - Sharpe-like: step_return − penalty × step_return_std
  - Or: log(portfolio_value) increment per step
  - Transaction cost penalty on position changes

Done:
  - End of episode (end of day, week, or fixed n_bars)
```

### Recommended Algorithms

| Algorithm | Complexity | Notes |
|---|---|---|
| PPO (Proximal Policy Optimization) | High | Most stable for continuous control |
| SAC (Soft Actor-Critic) | High | Good for continuous action spaces |
| DQN | Medium | Simple; works for discrete actions |
| A2C | Medium | Faster but less stable than PPO |

### Brute-Force Parameter Search Space

```
algorithm        : ["ppo", "sac", "dqn"]
obs_bars         : [20, 50, 100]
reward_type      : ["pnl", "sharpe", "calmar"]
transaction_cost : [0.0001, 0.0005, 0.001]    # per trade
n_episodes       : [1000, 5000]
episode_length   : [390, 1950]                  # bars per episode (1 day, 1 week)
network_arch     : [[64,64], [128,64,32]]
learning_rate    : [0.0003, 0.001]
timeframe        : [5min]
```

### Critical Limitation

RL agents trained on historical data are extremely prone to overfitting to
the specific noise patterns of the training environment. Walk-forward validation
is mandatory. Use this as a research track with low expectation of immediate
live deployment.

---

## ML-08 — Genetic Algorithm Parameter Optimization

### Hypothesis

A Genetic Algorithm (GA) can search the parameter space of a traditional
rule-based strategy more efficiently than exhaustive grid search for high-
dimensional spaces. GA evolves a population of parameter sets through
selection, crossover, and mutation, converging on high-fitness regions of the
search space. The fitness function is a walk-forward Sharpe ratio, preventing
overfitting better than in-sample Sharpe.

### Method

1. Define chromosome: parameter set for target strategy (e.g. EMA periods,
   ATR multiplier, RSI threshold).
2. Initialize population of N random chromosomes.
3. Evaluate each chromosome using walk-forward backtesting.
4. Selection: retain top K% by Sharpe; discard bottom K%.
5. Crossover: mix parameters from two parent chromosomes.
6. Mutation: randomly perturb parameters within bounds.
7. Repeat for G generations.

### Implementation Notes

- Use `DEAP` or `pymoo` Python library for GA implementation.
- Parallelize fitness evaluation using Numba kernels (same as grid search).
- Set realistic chromosome bounds to avoid degenerate parameters.
- Add parsimony penalty to avoid over-complex parameter combinations.

### Brute-Force Parameter Search Space

```
population_size  : [50, 100, 200]
n_generations    : [20, 50, 100]
crossover_rate   : [0.7, 0.8, 0.9]
mutation_rate    : [0.05, 0.10, 0.20]
selection_method : ["tournament", "roulette", "elitist"]
fitness_metric   : ["sharpe", "calmar", "profit_factor"]
target_strategy  : ["ema_crossover", "supertrend", "multi_indicator"]
timeframe        : [5min, 15min]
```

---

## ML-09 — Bayesian Optimization for Strategy Parameters

### Hypothesis

Bayesian Optimization (BO) builds a probabilistic surrogate model of the
objective function (walk-forward Sharpe as a function of strategy parameters)
and uses it to intelligently select the next parameter set to evaluate. BO
is far more sample-efficient than grid search — it requires 10–100× fewer
evaluations to find near-optimal parameters, making it practical for strategies
with expensive backtests.

### Method

1. Define parameter bounds (same as grid search space).
2. Evaluate an initial set of random parameter combinations (exploration).
3. Fit a Gaussian Process (GP) surrogate to observed (params → Sharpe) pairs.
4. Use acquisition function (Expected Improvement, UCB) to select next params.
5. Evaluate, update GP, repeat until budget exhausted.

### Implementation Notes

- Use `scikit-optimize` (`skopt.gp_minimize`) or `optuna` (TPE sampler).
- Budget: 50–200 evaluations typically sufficient for 5–10 dimensional spaces.
- Combine with walk-forward validation as the objective function evaluation.
- BO can be multi-objective (Sharpe + Drawdown) using Pareto-front methods.

### Brute-Force Parameter Search Space

```
n_initial_points : [10, 20]
n_calls          : [50, 100, 200]
surrogate_model  : ["gp", "random_forest_surrog", "gbrt"]
acquisition_func : ["ei", "ucb", "poi"]
target_strategy  : ["ema_crossover", "supertrend", "mean_reversion_bb"]
objective        : ["sharpe", "calmar", ["sharpe", "max_drawdown"]]
timeframe        : [5min, 15min]
```

### Advantage over Grid Search

For a 6-dimensional parameter search with 5 values each (= 15,625 combinations),
Bayesian optimization typically finds > 90% of the optimal solution in < 200
evaluations. Grid search requires 15,625. For computationally expensive
backtests, BO provides the same answer much faster.

---

## ML-10 — Ensemble Voting Classifier

### Hypothesis

Combining predictions from multiple diverse ML models (XGBoost, LSTM, KNN,
SVM) through a voting or stacking mechanism produces more stable and
generalizable predictions than any single model. The diversity of the ensemble
reduces the risk that all models simultaneously make errors on the same market
regime — the models' errors are partially uncorrelated.

### Ensemble Methods

| Method | Description |
|---|---|
| Hard voting | Take majority vote of model predictions |
| Soft voting | Average predicted probabilities; threshold |
| Stacking | Train a meta-model on model predictions as features |
| Blending | Simple average of walk-forward probabilities |

### Implementation Notes

- Models must be trained independently on the same walk-forward splits.
- Use soft voting (probability averaging) rather than hard voting — more stable.
- Add models only if they have positive correlation with the target AND low
  correlation with each other (diversity requirement).
- Stacking meta-model should be extremely simple (logistic regression, ridge)
  to avoid re-overfitting.

### Brute-Force Parameter Search Space

```
base_models      : [["xgboost", "random_forest"],
                    ["xgboost", "knn"],
                    ["xgboost", "lightgbm", "knn"],
                    ["xgboost", "lightgbm", "lstm"]]
ensemble_method  : ["soft_vote", "stacking_logreg"]
probability_thresh: [0.55, 0.60, 0.65]
min_agreement    : [0.5, 0.6, 0.7]          # fraction of models that must agree
timeframe        : [5min, 15min]
```

---

## Cross-Strategy Considerations

### Feature Importance Stability

A well-calibrated ML model should show consistent feature importance across
walk-forward periods. If the top features change drastically between periods,
the model is likely overfitting to noise:

```python
# Check feature importance stability
for period in walk_forward_periods:
    importances[period] = model.feature_importances_

stability_score = rank_correlation(importances)   # should be > 0.7
```

### Transaction Cost Break-Even

ML models tend to generate higher signal frequency than rule-based strategies.
Compute the minimum net accuracy required to break even after costs:

```
break_even_accuracy = 0.5 + (spread_cost / avg_win_size)
# e.g. for EURUSD: 0.5 + (1 pip / 5 pip avg win) = 0.70
# The model must be right > 70% of the time to be profitable after spread
```

### Data Size Requirements

| Model | Minimum samples | Recommended |
|---|---|---|
| Random Forest / XGBoost | 5,000 | > 20,000 |
| SVM | 1,000 | > 10,000 |
| KNN | 1,000 | > 5,000 |
| LSTM | 50,000 | > 200,000 |
| Transformer | 100,000 | > 500,000 |

On 5-min bars, EURUSD (2003–2024) provides ~1.1 million bars — sufficient
for all models above.

### Suggested Evaluation Priority

| Priority | Strategy | Reason |
|---|---|---|
| 1 | ML-01 XGBoost Classification | Best balance of performance and interpretability |
| 2 | ML-09 Bayesian Optimization | Improves any strategy; not standalone ML |
| 3 | ML-08 Genetic Algorithm | Efficient parameter search alternative to grid |
| 4 | ML-02 LightGBM Walk-Forward | Rigorous framework; production-ready approach |
| 5 | ML-10 Ensemble | Combine best models; final performance boost |
| 6 | ML-03 KNN Pattern Matching | Interesting baseline; no distributional assumptions |
| 7 | ML-04 SVM | Solid for small-to-medium datasets |
| 8 | ML-05 LSTM | High compute; treat as research track |
| 9 | ML-06 Transformer | Cutting-edge; very high compute; research only |
| 10 | ML-07 Reinforcement Learning | Most experimental; long-term research track |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
