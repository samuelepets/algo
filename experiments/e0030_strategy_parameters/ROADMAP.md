# Roadmap — e0030_strategy_parameters

Top-level progress tracker for the strategy parameter search experiment.
Each category maps to a sub-experiment; each strategy maps to a Python (uv) project.
Legacy Rust in `tf01_ema_crossover/` is complete and retained for reference only.
New strategies follow [`tf01_ema_crossover_python/`](./cat01_trend_following/tf01_ema_crossover_python/).

---

## Cat 1 — Trend-Following (20 strategies)

Strategy research: [`strategies/01_TREND_FOLLOWING.md`](../../strategies/01_TREND_FOLLOWING.md)
Sub-experiment: [`cat01_trend_following/`](./cat01_trend_following/)

| Strategy | Folder | Status |
|---|---|---|
| TF-01 EMA Crossover | `tf01_ema_crossover/` (+ Python ref `tf01_ema_crossover_python/`) | Complete |
| TF-02 Triple EMA | `tf02_triple_ema/` | Complete |
| TF-03 MACD Crossover | `tf03_macd_crossover/` | Structure defined |
| TF-04 MACD + 200 EMA | `tf04_macd_200ema/` | Structure defined |
| TF-05 EMA + RSI | `tf05_ema_rsi/` | Structure defined |
| TF-06 ADX + EMA | `tf06_adx_ema/` | Structure defined |
| TF-07 SuperTrend | `tf07_supertrend/` | Structure defined |
| TF-08 SuperTrend + VWAP + ADX | `tf08_supertrend_vwap_adx/` | Structure defined |
| TF-09 VWAP Trend Bias | `tf09_vwap_trend/` | Structure defined |
| TF-10 Parabolic SAR | `tf10_parabolic_sar/` | Structure defined |
| TF-11 Ichimoku Cloud | `tf11_ichimoku/` | Structure defined |
| TF-12 Williams Alligator | `tf12_alligator/` | Structure defined |
| TF-13 EMA Ribbon | `tf13_ema_ribbon/` | Structure defined |
| TF-14 Hull MA (HMA) | `tf14_hma/` | Structure defined |
| TF-15 EMA Pullback | `tf15_ema_pullback/` | Structure defined |
| TF-16 LinReg Channel | `tf16_linreg_channel/` | Structure defined |
| TF-17 Donchian Breakout | `tf17_donchian/` | Structure defined |
| TF-18 N-Bar Breakout | `tf18_nbar_breakout/` | Structure defined |
| TF-19 ROC Breakout | `tf19_roc_breakout/` | Structure defined |
| TF-20 Elder Impulse | `tf20_elder_impulse/` | Structure defined |

---

## Cat 2 — Mean-Reversion (20 strategies)

Strategy research: [`strategies/02_MEAN_REVERSION.md`](../../strategies/02_MEAN_REVERSION.md)
Sub-experiment: [`cat02_mean_reversion/`](./cat02_mean_reversion/)

All 20 strategies are implemented, tested, and run on EURUSD full history
(2003–2025) with 4-window walk-forward validation. **None clears the bar for
live/paper trading** (every walk-forward run has at least one OOS-negative
window), but 7 strategies show a real, non-trivial full-history positive
Sharpe cluster worth further research — flagged below and ranked in the
[cross-strategy priority list](#cat-2-follow-up-priority).

| Strategy | Folder | Best Sharpe | Status |
|---|---|---|---|
| MR-01 Bollinger Band Mean Reversion | [`mr01_bollinger_band/`](./cat02_mean_reversion/mr01_bollinger_band/) | −0.15 | No edge |
| MR-02 RSI(2) Ultra-Short Reversion | [`mr02_rsi2_reversion/`](./cat02_mean_reversion/mr02_rsi2_reversion/) | **+0.85** | Weak edge, decays with time — not confirmed OOS |
| MR-03 VWAP Standard Deviation Bands | [`mr03_vwap_bands/`](./cat02_mean_reversion/mr03_vwap_bands/) | −1.28 | No edge |
| MR-04 Z-Score Statistical Reversion | [`mr04_zscore_reversion/`](./cat02_mean_reversion/mr04_zscore_reversion/) | −0.22 | No edge |
| MR-05 Stochastic %K/%D Reversion | [`mr05_stochastic_reversion/`](./cat02_mean_reversion/mr05_stochastic_reversion/) | −2.13 | No edge (comprehensive failure) |
| MR-06 CCI Extreme Reversion | [`mr06_cci_reversion/`](./cat02_mean_reversion/mr06_cci_reversion/) | **+0.56** | IS-overfit — fails OOS in 3/4 windows |
| MR-07 Williams %R Reversion | [`mr07_williams_r/`](./cat02_mean_reversion/mr07_williams_r/) | −3.72 | No edge (comprehensive failure) |
| MR-08 Keltner Channel Reversion | [`mr08_keltner_channel/`](./cat02_mean_reversion/mr08_keltner_channel/) | **+0.20** | Narrow cluster (11%) — fails OOS |
| MR-09 Price/EMA Distance (Rubber Band) | [`mr09_ema_distance/`](./cat02_mean_reversion/mr09_ema_distance/) | +0.12 | No edge (only 0.2% of grid positive) |
| MR-10 RSI Divergence Reversion | [`mr10_rsi_divergence/`](./cat02_mean_reversion/mr10_rsi_divergence/) | −0.31 | No edge |
| MR-11 Double Bollinger Band System | [`mr11_double_bollinger/`](./cat02_mean_reversion/mr11_double_bollinger/) | −0.27 | No edge |
| MR-12 Pivot Point Reversion | [`mr12_pivot_point/`](./cat02_mean_reversion/mr12_pivot_point/) | −0.01 | No edge, near-breakeven, 1 OOS-positive window |
| MR-13 Money Flow Index (MFI) Extremes | [`mr13_mfi_extremes/`](./cat02_mean_reversion/mr13_mfi_extremes/) | −0.01 | No edge, near-breakeven, 1 OOS-positive window |
| MR-14 Stochastic RSI Reversion | [`mr14_stochrsi/`](./cat02_mean_reversion/mr14_stochrsi/) | −0.63 | No edge (post numerical-stability fix) |
| MR-15 DeMarker Oscillator Reversion | [`mr15_demarker/`](./cat02_mean_reversion/mr15_demarker/) | **+0.18** | Thin cluster (6 cells), strongest IS Sharpe — fails OOS |
| MR-16 Opening Range Mean Reversion | [`mr16_opening_range_reversion/`](./cat02_mean_reversion/mr16_opening_range_reversion/) | −0.37 | No edge, 1 OOS-positive window |
| MR-17 EMA Touch Return | [`mr17_ema_touch_return/`](./cat02_mean_reversion/mr17_ema_touch_return/) | −0.21 | No edge |
| MR-18 High-Low Channel Fade | [`mr18_hl_channel_fade/`](./cat02_mean_reversion/mr18_hl_channel_fade/) | −0.25 | No edge |
| MR-19 Connors RSI (3-Component) Reversion | [`mr19_connors_rsi/`](./cat02_mean_reversion/mr19_connors_rsi/) | **+0.38** | Broadest cluster (42%) — fails OOS |
| MR-20 TEMA Distance Reversion | [`mr20_tema_distance/`](./cat02_mean_reversion/mr20_tema_distance/) | **+0.46** | Broad cluster (21%, post numerical-stability fix) — fails OOS |

### Cat 2 follow-up priority

Ranked by strength/robustness of the full-history signal (all fail
walk-forward as implemented; this ranks where deeper work is most likely to
pay off):

1. **MR-19** — broadest cluster (42% of grid), strongest and most
   consistent IS walk-forward Sharpe (+0.90 to +1.42) of any strategy in the
   category; robust OOS trade counts rule out a small-sample explanation.
2. **MR-02** — largest single-cell Sharpe (+0.85) and a broad 19.7% cluster,
   but the edge visibly decays across walk-forward windows.
3. **MR-20** — broad 21% cluster with a clear parameter-family reachable
   from IS-only selection in 2/4 windows.
4. **MR-06** — real 8.3% cluster, but a textbook IS-overfitting signature
   (strong IS, negative-to-flat OOS in all 4 windows).
5. **MR-08 / MR-15** — narrower clusters (11% / 6 cells); MR-15 has the
   single strongest IS Sharpe among thin-sample results.
6. **MR-12 / MR-13** — no cluster, but the only two strategies with a
   genuinely OOS-positive walk-forward window and near-breakeven full-history
   Sharpe.

### Notable implementation finding: ATR near-zero numerical bug

Three strategies (MR-14, MR-19 partially, MR-20) initially showed spurious
positive results caused by Wilder ATR decaying toward machine epsilon during
flat-price data gaps (weekend/holiday stretches in the resampled bars),
producing an economically meaningless near-zero-risk stop and an
astronomically large single-trade R-multiple. Fixed with a realistic
`ATR_FLOOR` guard (`1e-5`, matching `mr09_ema_distance`'s existing
convention) in the affected strategies' `backtest.py`. All numbers in the
table above are post-fix. See each affected strategy's README.md
"Numerical stability" section for details.

---

## Cat 3 — Volatility-Based

Strategy research: `strategies/03_VOLATILITY.md` *(pending)*
Sub-experiment: `cat03_volatility/` *(pending)*

---

## Cat 4 — Pattern-Based

Strategy research: `strategies/04_PATTERNS.md` *(pending)*
Sub-experiment: `cat04_patterns/` *(pending)*

---

## Cat 5 — Time-Based

Strategy research: `strategies/05_TIME_BASED.md` *(pending)*
Sub-experiment: `cat05_time_based/` *(pending)*

---

## Cat 6 — Statistical & Quantitative

Strategy research: `strategies/06_STATISTICAL.md` *(pending)*
Sub-experiment: `cat06_statistical/` *(pending)*

---

## Cat 7 — Multi-Timeframe

Strategy research: `strategies/07_MULTI_TIMEFRAME.md` *(pending)*
Sub-experiment: `cat07_multi_timeframe/` *(pending)*

---

## Cat 8 — Volume-Based

Strategy research: `strategies/08_VOLUME_BASED.md` *(pending)*
Sub-experiment: `cat08_volume_based/` *(pending)*

---

## Cat 9 — Machine Learning–Assisted

Strategy research: `strategies/09_ML_ASSISTED.md` *(pending)*
Sub-experiment: `cat09_ml_assisted/` *(pending — may add ML-specific deps on top of the Python stack)*
