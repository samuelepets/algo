# ROADMAP — regime_detector

Status: **paused** (2026-07-01). Stage 1 is complete and validated; the work
below is ordered by expected value for whenever this is picked up again.
Read [`README.md`](./README.md) (findings) and
[`../MARKET_REGIME_DETECTION.md`](../MARKET_REGIME_DETECTION.md) (design doc)
first.

## Done

- [x] Stage 1 rule-based classifier (direction x volatility) with hysteresis,
      confirmation delay, and leakage-safe H1/H4 resampling. 12 unit tests,
      including an explicit no-look-ahead test.
- [x] Walk-forward threshold tuning (`tune.py`): train 2003-2015, confirm
      2016-2020, single test pass 2021-2025. Final config: **H4, ADX 28/23,
      ER 0.40, slope 0, confirm 5** (frozen in `economic.py::FINAL_TH`).
- [x] §7 sanity metrics (`main.py`, `evaluate.py`) — labels are stable
      (~0.08 changes/day); volatility axis coherent out-of-sample.
- [x] §7.3 economic validation (`economic.py`) — naive routing table
      **rejected**; inverted mapping found: *Bollinger fade enabled only
      during TREND regimes* is positive in all three periods
      (test 2021-2025: +2.8%/yr, Sharpe 0.88, max DD ~3%).

## Next (in order)

1. **Promote "fade-in-trend" to a formal experiment** under
   `experiments/` (self-contained, per repo conventions):
   - Real strategy mechanics: stops, position sizing, session filters,
     slippage model beyond fixed half-spread.
   - Re-run the full walk-forward protocol inside the experiment; the toy
     result here is the hypothesis, not the evidence.
   - Robustness: parameter neighborhoods (BB period/k, detector thresholds),
     yearly return breakdown, regime-age conditioning (`bars_in_regime`).
2. **Cross-instrument check** of the inverted mapping on XAUUSD / XAGUSD
   (2003-2025 available). If it only works on EUR/USD, treat it as
   instrument-specific microstructure, not a general regime property.
3. **Router hardening** (only if 1-2 survive):
   - Implement the transition policy from the design doc §8 (grace period vs
     run-to-exit; currently positions resume instantly on re-enable, which
     flatters the filtered variants slightly).
   - Confidence-scaled sizing using the detector's `confidence` output.
4. **Stage 2 models** (design doc §5): HMM with Gaussian emissions over
   returns + vol features, fit on train years only, refit yearly. Must beat
   the frozen Stage 1 rules on the §7 metrics to replace them — the bar is
   the *inverted* routing result, not the naive one.
5. **Feature extensions** (second iteration, design doc §4): session-of-day
   features (Asian range vs London/NY), Hurst exponent, variance-ratio test.
   Evaluate each as an *added* feature against the frozen baseline.

## Known caveats to fix before trusting any of this with money

- Toy strategies only; spread-only costs (0.5 pip/side), no slippage or swap.
- Single instrument so far.
- The volatility circuit breaker (`vol_off`) was inconclusive — untested as a
  *combined* filter with the inverted direction mapping.
- 2025 was eyeballed with default thresholds before the tuning run (low
  contamination risk — defaults were not selected on it — but noted).
