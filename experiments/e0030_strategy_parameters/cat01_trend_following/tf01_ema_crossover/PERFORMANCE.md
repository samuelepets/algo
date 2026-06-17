# PERFORMANCE — TF-01 EMA Crossover

Detailed breakdown of all 3,150 parameter combinations tested on
EURUSD 2003–2025. Source: `outputs/results.csv`.

All P&L figures are in **R-multiples** (risk-adjusted units):
1 R = 1 × `atr_stop_mult × ATR(14)` of risk per trade.
A full stop-hit = −1R. A target hit = +`rr_ratio` R.

**Max Drawdown** is reported in **absolute R units** (`max_drawdown_r`): the
largest peak-to-trough decline of the cumulative-R equity curve, where the
curve starts at 0 R. It is always ≥ 0. Because every combination is net losing
over the full sample, the running peak stays pinned near the 0-R baseline, so
drawdown is on the same order as the total cumulative loss.

---

## 1. Overall Distribution

| Metric | Min | P10 | P25 | Median | P75 | P90 | Max | Mean |
|---|---|---|---|---|---|---|---|---|
| Sharpe | −43.10 | −14.21 | −6.89 | −4.28 | −2.20 | −1.23 | −0.56 | −7.37 |
| Profit Factor | 0.28 | 0.48 | 0.59 | 0.69 | 0.82 | 0.88 | 0.93 | 0.72 |
| Max Drawdown (R) | 388.7 | 901.8 | 1,637.6 | 5,864.3 | 11,066.4 | 26,430.0 | 75,780.0 | — |
| N Trades | 8,294 | 9,236 | 11,483 | 21,948 | 55,421 | 87,429 | 129,853 | 38,122 |

**Key statistics:**
- Combinations with Sharpe > 0: **0 / 3,150 (0%)**
- Combinations with Profit Factor > 1.0: **0 / 3,150 (0%)**
- Combinations with Sharpe > −1.0: **50 / 3,150 (1.6%)** — all on 15-min

---

## 2. Performance by Timeframe

| TF | Combinations | Mean Sharpe | Best Sharpe | Combinations Sharpe > −1.0 |
|---|---|---|---|---|
| **5-min** | 1,575 | −11.41 | −3.36 | 0 |
| **15-min** | 1,575 | −3.34 | −0.56 | 50 |

**Takeaway:** 15-min is consistently and significantly better than 5-min.
The higher-frequency 5-min bars generate ~3× more crossovers, most of which
are noise. Even the best 5-min combination (fast=12, slow=50, atr_m=2.5,
rr=3.0) achieves only Sharpe = −3.36.

---

## 3. Performance by R:R Ratio

| `rr_ratio` | Mean Sharpe | Best Sharpe | Mean Profit Factor |
|---|---|---|---|
| 1.0 | −9.61 | −0.91 | 0.56 |
| 1.5 | −7.91 | −0.69 | 0.67 |
| 2.0 | −6.98 | −0.64 | 0.75 |
| 2.5 | −6.40 | −0.66 | 0.80 |
| 3.0 | −5.96 | **−0.56** | 0.84 |

**Takeaway:** Higher R:R ratios consistently improve Sharpe. The strategy
requires a large R:R ratio to partially offset its low win rate. Even at
rr=3.0, no combination crosses zero.

---

## 4. Performance by ATR Stop Multiplier

| `atr_stop_mult` | Mean Sharpe | Best Sharpe | Mean Profit Factor | Mean Trades |
|---|---|---|---|---|
| 0.5 | −15.99 | −4.09 | 0.47 | 65,822 |
| 1.0 | −7.62 | −0.79 | 0.66 | 44,249 |
| 1.5 | −5.18 | −0.67 | 0.74 | 34,052 |
| 2.0 | −4.25 | −0.61 | 0.78 | 27,521 |
| 2.5 | **−3.83** | **−0.56** | 0.82 | 19,829 |

**Takeaway:** Wider stops dramatically improve performance. A 0.5× ATR stop
is extremely tight on EURUSD — it is hit by normal intrabar noise on nearly
every trade. At 2.5× ATR, the strategy can "breathe" more, producing fewer
trades and better PF. The monotonic improvement strongly suggests the ideal
stop may be even wider (> 3× ATR), which is outside the current search space.

---

## 5. Performance by EMA Period Pair (Top 20 by Sharpe, 15-min only)

| Rank | fast | slow | atr_m | rr | Sharpe | PF | Max DD (R) | Total R | Trades |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 13 | 50 | 2.5 | 3.0 | −0.5631 | 0.9274 | 394.8 | −335.3 | 8,294 |
| 2 | 12 | 34 | 2.5 | 3.0 | −0.5677 | 0.9326 | 412.2 | −356.8 | 10,198 |
| 3 | 13 | 34 | 2.5 | 3.0 | −0.5851 | 0.9299 | 399.1 | −366.1 | 9,900 |
| 4 | 12 | 50 | 2.5 | 3.0 | −0.6468 | 0.9178 | 434.1 | −385.0 | 8,527 |
| 5 | 13 | 50 | 2.5 | 2.5 | −0.6590 | 0.9200 | 418.8 | −372.2 | 8,475 |
| 6 | 12 | 34 | 2.5 | 2.5 | −0.7023 | 0.9214 | 454.9 | −417.5 | 10,381 |
| 7 | 10 | 50 | 2.5 | 3.0 | −0.7101 | 0.9117 | 465.5 | −426.0 | 9,067 |
| 8 | 13 | 30 | 2.5 | 3.0 | −0.7125 | 0.9172 | 500.9 | −450.7 | 10,493 |
| 9 | 9  | 34 | 2.5 | 3.0 | −0.7234 | 0.9173 | 553.1 | −458.4 | 11,348 |
| 10 | 9 | 50 | 2.5 | 3.0 | −0.7335 | 0.9102 | 494.2 | −442.5 | 9,446 |
| 11 | 13 | 34 | 2.5 | 2.5 | −0.7460 | 0.9160 | 481.7 | −441.2 | 10,088 |
| 12 | 10 | 34 | 2.5 | 3.0 | −0.7492 | 0.9136 | 526.1 | −472.5 | 10,919 |
| 13 | 12 | 50 | 2.5 | 2.5 | −0.7592 | 0.9092 | 471.9 | −428.9 | 8,712 |
| 14 | 12 | 50 | 2.0 | 3.0 | −0.7709 | 0.9110 | 573.9 | −529.3 | 9,429 |
| 15 | 13 | 50 | 2.0 | 3.0 | −0.7745 | 0.9098 | 583.7 | −527.5 | 9,170 |
| 16 | 12 | 30 | 2.5 | 3.0 | −0.7793 | 0.9106 | 530.4 | −493.3 | 10,825 |
| 17 | 13 | 20 | 2.5 | 3.0 | −0.7879 | 0.9145 | 542.5 | −511.4 | 12,559 |
| 18 | 12 | 26 | 2.5 | 3.0 | −0.7991 | 0.9104 | 556.8 | −512.1 | 11,559 |
| 19 | 13 | 26 | 2.5 | 3.0 | −0.8054 | 0.9091 | 546.8 | −514.4 | 11,200 |
| 20 | 8  | 50 | 2.5 | 3.0 | −0.8134 | 0.9018 | 537.6 | −490.5 | 9,819 |

---

## 6. Worst Combinations (Bottom 5)

These are dominated by very tight stops (0.5× ATR) on 5-min bars — the stop
is hit constantly by intrabar noise, generating loss after loss. Because the
equity curve only ever sinks, max drawdown (absolute R) tracks the total loss:

| fast | slow | atr_m | rr | tf | Sharpe | PF | Max DD (R) | Total R | Trades |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 18 | 0.5 | 1.0 | 5 | −43.10 | 0.297 | 75,780 | −75,779 | 129,853 |
| 3 | 20 | 0.5 | 1.0 | 5 | −42.06 | 0.297 | 72,105 | −72,105 | 123,391 |
| 3 | 21 | 0.5 | 1.0 | 5 | −41.65 | 0.296 | 70,523 | −70,522 | 120,393 |
| 3 | 25 | 0.5 | 1.0 | 5 | −40.25 | 0.293 | 65,216 | −65,214 | 110,568 |
| 3 | 26 | 0.5 | 1.0 | 5 | −39.90 | 0.292 | 64,024 | −64,024 | 108,437 |

---

## 7. Walk-Forward Analysis (true IS-only parameter selection)

Protocol: for each window the **full grid is re-optimised on the in-sample
slice only**; the single best IS parameter set (max Sharpe, ≥ 50 trades) is then
evaluated, unchanged, on the out-of-sample slice. Parameters are *not* selected
from the full history, so no future information leaks into the choice. The
selected set is logged per window (`outputs/walkforward.csv`).

| Window | In-Sample | Out-of-Sample | Selected (fast/slow, atr_m, rr, tf) | IS Sharpe | IS PF | IS Trades | OOS Sharpe | OOS PF | OOS Max DD (R) | OOS Trades |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | 13/50, 2.5×, rr2.5, 15m | −0.133 | 0.983 | 4,297 | −0.202 | 0.974 | 71.1 | 1,426 |
| 2 | 2003–2016 | 2017–2020 | 12/34, 2.5×, rr3.0, 15m | −0.110 | 0.986 | 6,057 | −0.700 | 0.920 | 112.7 | 1,834 |
| 3 | 2003–2018 | 2019–2022 | 13/50, 2.5×, rr3.0, 15m | −0.089 | 0.988 | 5,593 | −1.799 | 0.795 | 194.8 | 1,540 |
| 4 | 2003–2020 | 2021–2025 | 13/50, 2.5×, rr3.0, 15m | −0.227 | 0.970 | 6,377 | −1.730 | 0.800 | 251.0 | 1,916 |

**Notes:**
- IS Sharpe is negative in all 4 windows — the IS-optimal combination is the
  "least bad", never genuinely profitable.
- **All 4 OOS windows are now negative.** Under the previous (leaky) protocol,
  which forced the full-history best combination onto every window, Window 1 OOS
  looked marginally positive (+0.092). With honest IS-only selection the IS
  optimum for that window is `rr2.5` and its OOS Sharpe is **−0.202** — the
  apparent edge was an artifact of the selection leak.
- IS selection consistently lands on the same "least-bad" region (15-min, slow
  MAs, wide 2.5× stop, high R:R), confirming the parameter-direction findings.
- OOS drawdown grows across later windows, peaking in 2021–2025 (251 R),
  consistent with structural degradation in higher-volatility regimes.
- There is no evidence of a consistent OOS edge in any 4-year sub-period.

---

## 8. Sensitivity Analysis

### Sharpe vs. `slow_ema` (15-min, fixed fast=13, atr_m=2.5, rr=3.0)

| slow_ema | Sharpe | PF | Trades |
|---|---|---|---|
| 18 | −0.867 | 0.909 | 14,038 |
| 20 | −0.898 | 0.904 | 13,263 |
| 21 | −0.856 | 0.906 | 13,186 |
| 25 | −0.840 | 0.912 | 12,278 |
| 26 | −0.805 | 0.909 | 11,200 |
| 30 | −0.712 | 0.917 | 10,493 |
| 34 | −0.585 | 0.930 | 9,900 |
| 50 | **−0.563** | 0.927 | 8,294 |

Monotonic improvement as `slow_ema` increases — slower MA produces fewer
trades and higher quality signals.

### Sharpe vs. `fast_ema` (15-min, fixed slow=50, atr_m=2.5, rr=3.0)

| fast_ema | Sharpe | PF | Trades |
|---|---|---|---|
| 3 | −1.189 | 0.886 | 11,218 |
| 5 | −1.097 | 0.890 | 10,638 |
| 7 | −0.894 | 0.899 | 9,707 |
| 8 | −0.836 | 0.906 | 9,428 |
| 9 | −0.733 | 0.910 | 9,446 |
| 10 | −0.710 | 0.912 | 9,067 |
| 12 | −0.647 | 0.918 | 8,527 |
| 13 | **−0.563** | 0.927 | 8,294 |

Same pattern: slower fast EMAs are consistently better. The optimal region
of the parameter space is slow MAs (13/50 at 15-min) — implying the strategy
would benefit from moving to even longer periods, or to daily bars.

---

## 9. Conclusion

The complete parameter search provides strong evidence that **EMA crossover
as a standalone system has no edge on EURUSD**:

1. **Universal losses:** 0% of 3,150 combinations are profitable (Sharpe > 0,
   PF > 1.0).
2. **Parameter direction:** Performance monotonically improves with slower MAs,
   wider stops, and higher R:R — but never crosses into positive territory.
   This suggests the information ratio of raw crossovers is inherently negative
   on this instrument/period.
3. **Regime sensitivity:** Under honest IS-only walk-forward selection, **all
   four OOS windows are negative** (−0.20, −0.70, −1.80, −1.73). The previously
   reported positive 2015–2018 window was an artifact of selection leakage. OOS
   drawdown worsens through 2019–2025, suggesting model breakdown in
   high-volatility regimes.
4. **Signal quality:** The high trade frequency (8,000–130,000 trades depending
   on parameters) indicates the strategy generates many low-quality signals.
   Filtering — either by trend regime (ADX), momentum confirmation (RSI), or
   time-of-day — is the natural next step.

**Next experiment:** `tf06_adx_ema` — adding ADX > 25 as a regime filter before
taking crossover signals. The prior analysis in `strategies/01_TREND_FOLLOWING.md`
predicts ADX filtering should significantly reduce false crossovers.
