# regime_detector

Stage 1 implementation of [`../MARKET_REGIME_DETECTION.md`](../MARKET_REGIME_DETECTION.md):
rule-based EUR/USD regime detector (direction x volatility) with hysteresis,
plus the walk-forward tuning and §7.3 economic validation.

## Usage

```bash
uv sync
uv run python main.py --symbol EURUSD --year 2025   # label a year, print §7 sanity metrics
uv run python tune.py                               # walk-forward threshold search
uv run python economic.py                           # §7.3 strategy-filter validation
uv run pytest                                       # unit tests (incl. no-look-ahead)
```

Outputs land in `out/` (gitignored).

## Findings (as of 2026-07, data 2003-2025)

Protocol: tune on 2003-2015, confirm on 2016-2020, test 2021-2025.

1. **Stability: good.** Tuned detector (H4, ADX 28/23, ER 0.40, confirm 5)
   produces persistent labels (~0.08 direction changes/day, median duration
   ~200h). The volatility axis is strongly coherent out-of-sample
   (VOL_HIGH realized vol ~2.6x VOL_LOW in 2025).
2. **Naive directional edge: rejected.** Following the trend label on the
   next bar earned +3.2%/yr on train but -0.2%/yr on validation and -2.2%/yr
   on test. Classic FX trend decay post-2015; do not trade the label directly.
3. **§7.3 routing-table test: the naive mapping is inverted.** With 0.5 pip/side
   costs, the *matched* variants (trend strategy in TREND, mean reversion in
   RANGE) were the worst in every period, while the *negative controls* won:
   - **Bollinger fade enabled only during TREND regimes** was the single
     variant positive in all three periods: +0.2%/yr train, +1.6%/yr val
     (Sharpe 0.46), +2.8%/yr test (Sharpe 0.88), max DD ~3%. Economically this
     is pullback-fading inside H4 trends.
   - EMA crossover only in RANGE was mildly positive on val/test (Sharpe
     0.09/0.23) — weak, not actionable alone.

   Interpretation: EUR/USD intraday has been mean-reverting for two decades;
   the detector's labels do stratify behavior, but the profitable mapping is
   *fade extremes inside trends*, not the textbook routing table. Since the
   inverted mapping was also the best variant on train, selecting it under the
   walk-forward protocol was legitimate (not a post-hoc flip on test data).

Caveats: toy strategies, single instrument, spread-only costs, positions
resume instantly when a filter re-enables. Next step per ROADMAP: promote the
"fade-in-trend" hypothesis to a proper experiment under `experiments/`.
