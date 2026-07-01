# Market Regime Detection Algorithm — EUR/USD

Instructions for building an algorithm that detects market conditions (regimes)
from a EUR/USD time series. The detector's output will later be used as a
**strategy router**: certain strategies are activated only during the regimes
they are suited for, and deactivated otherwise.

---

## 1. Objective

Given a EUR/USD OHLCV time series, produce at every bar `t` a label:

```
regime(t) ∈ { TREND_UP, TREND_DOWN, RANGE, HIGH_VOLATILITY, LOW_VOLATILITY, ... }
```

with these properties:

1. **Causal**: `regime(t)` uses only information available up to and including
   bar `t` (no look-ahead).
2. **Stable**: the label must not flip on every bar; regime changes should be
   confirmed before being emitted (hysteresis).
3. **Actionable**: each regime maps to a set of enabled strategies.

## 2. Regime taxonomy

Model regimes along **two independent axes** rather than one flat list. The
final regime is the combination of both axes.

### Axis 1 — Directionality

| Label        | Meaning                                    |
| ------------ | ------------------------------------------ |
| `TREND_UP`   | Sustained directional move upward          |
| `TREND_DOWN` | Sustained directional move downward        |
| `RANGE`      | Price oscillates inside a horizontal band  |

### Axis 2 — Volatility

| Label      | Meaning                                        |
| ---------- | ---------------------------------------------- |
| `VOL_HIGH` | Realized volatility above its rolling quantile |
| `VOL_NORM` | Volatility inside its normal band              |
| `VOL_LOW`  | Compressed volatility (squeeze / pre-breakout) |

This yields 9 combined states, e.g. `TREND_UP × VOL_NORM` or
`RANGE × VOL_LOW`. Start with these; add session-based sub-regimes
(Asian / London / New York) later if needed.

## 3. Input data and preprocessing

1. **Source**: EUR/USD 1-minute OHLCV bars.
2. **Resampling**: run detection on a slower timeframe than the raw data —
   typically **H1** (or M15) — because regimes are a medium-frequency concept.
   Keep the 1-minute data for strategy execution, not for regime detection.
3. **Cleaning**:
   - Drop or forward-handle weekend gaps and holiday sessions.
   - Verify monotonic timestamps and deduplicate bars.
   - Compute log returns: `r(t) = ln(Close(t) / Close(t-1))`.
4. **Alignment rule**: an indicator computed on a bar is only usable **after
   that bar closes**. When resampling, label each aggregated bar with its
   close time to avoid leakage.

## 4. Feature set

Compute a small, interpretable feature vector per (resampled) bar. Suggested
core set:

### Directionality features

| Feature | Definition | Reads as trend when… |
| --- | --- | --- |
| **ADX(14)** | Average Directional Index | ADX > 25 (trend), < 20 (range) |
| **Efficiency Ratio (Kaufman, N=20)** | `abs(C(t) − C(t−N)) / Σ abs(C(i) − C(i−1))` | ER > ~0.3 |
| **EMA slope** | Slope of EMA(50), normalized by ATR | `|slope|` above threshold |
| **EMA stack** | Sign of `EMA(20) − EMA(50)` | Determines UP vs DOWN |
| **R² of linear fit** | R² of regression of Close on time over N bars | R² high ⇒ trending |

### Volatility features

| Feature | Definition | Notes |
| --- | --- | --- |
| **ATR(14) percentile** | ATR relative to its rolling 90-day distribution | Main vol classifier |
| **Realized vol** | Std of log returns over N bars, annualized | Cross-check for ATR |
| **Bollinger Band width** | `(Upper − Lower) / Middle`, 20-period | Squeeze detector (VOL_LOW) |

### Optional (second iteration)

- **Hurst exponent** over rolling windows (H > 0.55 trending, H < 0.45 mean-reverting).
- **Variance ratio test** statistic (random walk vs. mean reversion).
- **Session/time features**: hour of day, day of week (EUR/USD behavior differs
  strongly between Asian range hours and London/NY trend hours).

**Normalization**: express every feature in ATR units, percentiles, or ratios —
never in raw price units — so thresholds remain valid across years.

## 5. Classification layer

Implement in this order; each stage is a usable deliverable.

### Stage 1 — Rule-based classifier (baseline, do this first)

Simple, auditable thresholds:

```text
directionality:
    if ADX > 25 and ER > 0.30:
        TREND_UP  if EMA(20) > EMA(50) and EMA slope > +k·ATR
        TREND_DOWN if EMA(20) < EMA(50) and EMA slope < −k·ATR
    elif ADX < 20:
        RANGE
    else:
        keep previous label   # ambiguous zone = hysteresis band

volatility:
    VOL_HIGH if ATR percentile > 0.80
    VOL_LOW  if ATR percentile < 0.20
    VOL_NORM otherwise
```

Key design points:

- **Hysteresis via dual thresholds**: enter TREND at ADX > 25 but only exit
  back to RANGE at ADX < 20. The gap prevents label flapping.
- **Confirmation delay**: require the new label to persist for `M` consecutive
  bars (e.g. 3 H1 bars) before officially switching regimes.
- **Minimum regime duration** (optional): ignore regime changes shorter than
  a floor (e.g. 12 H1 bars).

### Stage 2 — Unsupervised model (refinement)

Once the baseline works end to end:

- **K-means / Gaussian Mixture** on the normalized feature vector (fit on
  training years only), with k chosen by silhouette/BIC; then map clusters to
  the semantic labels by inspecting cluster centroids.
- **Hidden Markov Model** (Gaussian emissions over returns + volatility
  features). HMMs give regime persistence for free through the transition
  matrix and output regime *probabilities*, useful for position sizing.

Rules for any learned model:

- Fit **only on the training window**; apply frozen parameters out-of-sample.
- Refit on a schedule (e.g. yearly walk-forward), never continuously on the
  bar you are labeling.
- Keep the rule-based classifier as the benchmark: the learned model must beat
  it on the evaluation metrics of §7 to replace it.

## 6. Output contract

The detector emits one record per resampled bar:

```json
{
  "time_close": "2024-03-15T14:00:00",
  "direction": "TREND_UP",
  "volatility": "VOL_NORM",
  "confidence": 0.82,
  "bars_in_regime": 47
}
```

- `confidence`: distance from thresholds (rule-based) or state probability (HMM).
- `bars_in_regime`: age of the current regime, useful for strategies that only
  join established trends.
- The record for bar `t` becomes available to strategies at the **open of bar
  `t+1`** at the earliest.

## 7. Validation and evaluation

Regime labels have no ground truth, so evaluate on three levels:

1. **Sanity / visual**: plot price colored by regime for several years.
   Trends must look like trends. Check known events (e.g. 2008, 2014–2015 USD
   rally, 2020 COVID, 2022 parity move) are labeled HIGH_VOL / TREND.
2. **Statistical coherence** (out-of-sample):
   - Mean absolute return per bar should be higher inside TREND than RANGE.
   - Autocorrelation of returns: positive-ish in TREND, negative-ish in RANGE.
   - Realized vol inside VOL_HIGH must exceed VOL_LOW by construction *out of sample*.
   - **Regime persistence**: median regime duration ≥ your holding period;
     switching rate below ~1 change/day on H1 is a reasonable target.
3. **Economic value (the real test)**: backtest two toy strategies —
   a trend-follower (e.g. EMA crossover) and a mean-reverter (e.g. Bollinger
   fade) — three ways:
   - always on,
   - on only in their matching regime,
   - on only in the *opposite* regime (negative control).
   The regime filter is useful iff the matched version dominates on
   risk-adjusted metrics (Sharpe, max drawdown) and the negative control is
   clearly worse.

Use **walk-forward splits** (e.g. fit/tune on 2003–2015, validate on
2016–2020, final test on 2021–2025 touched exactly once).

## 8. Strategy routing

Maintain an explicit routing table, versioned with the detector:

| Regime (direction × vol) | Enabled strategy families |
| --- | --- |
| TREND_* × VOL_NORM       | Trend following, breakout continuation |
| TREND_* × VOL_HIGH       | Trend following with reduced size / wider stops |
| RANGE × VOL_NORM         | Mean reversion, range fading |
| RANGE × VOL_LOW          | Squeeze/breakout anticipation; reduce mean-reversion size |
| * × VOL_HIGH (extreme)   | Optionally flat: risk-off circuit breaker |

Transition policy (decide and document explicitly):

- On regime change, **stop opening** new positions for the disabled strategy.
- Existing positions either run to their natural exit (default, simpler) or
  are force-closed after a grace period.
- Optionally scale position size by `confidence`.

## 9. Implementation plan

Suggested module layout (Python, one self-contained project):

```
regime_detector/
├── data.py          # load 1-min bars, clean, resample to H1
├── features.py      # ADX, ER, EMA slope, ATR percentile, BB width…
├── classifier.py    # Stage 1 rules + hysteresis state machine
├── models.py        # Stage 2: HMM / clustering (optional)
├── router.py        # regime → enabled strategies mapping
├── evaluate.py      # §7 metrics, plots, toy-strategy backtests
├── main.py          # CLI: label a date range, emit CSV/parquet of regimes
└── tests/           # unit tests: features vs. reference values,
                     # no look-ahead, hysteresis behavior
```

Build order:

1. Data loading + resampling with leakage-safe timestamps (test this).
2. Feature computation with unit tests against known reference values.
3. Rule-based classifier + hysteresis state machine (test the state machine
   with synthetic sequences).
4. Label full history, run §7 sanity plots and statistical checks.
5. Toy-strategy economic validation (§7.3); tune thresholds on the training
   window only.
6. Freeze v1 (thresholds + routing table). Only then explore Stage 2 models.

## 10. Pitfalls checklist

- [ ] No indicator at bar `t` uses `Close(t+…)` (write an explicit test).
- [ ] Rolling percentiles use only past data (expanding or trailing windows).
- [ ] Resampled bar labeled by close time, consumed at next open.
- [ ] Thresholds tuned on training years only; test years touched once.
- [ ] Hysteresis prevents flapping (measure switching rate).
- [ ] Detector versioned together with its routing table.
- [ ] Overfitting guard: the fewer free parameters, the better — prefer the
      dumb rule set that survives out-of-sample over the clever model that
      doesn't.
