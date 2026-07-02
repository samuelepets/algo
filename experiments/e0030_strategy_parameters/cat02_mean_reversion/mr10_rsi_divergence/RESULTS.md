# RESULTS — MR-10 RSI Divergence Reversion

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr10_rsi_divergence` |
| Strategy | RSI Divergence Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-10` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 8.4 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `rsi_period` | 7, 10, 14 (3 values) |
| `swing_lookback` | 3, 5, 8, 10 (4 values) |
| `div_tolerance` | 0, 3, 5 RSI points (3 values) |
| `confirmation` | any_bar, bullish_candle (2 values) |
| `atr_stop_mult` | 1.0, 1.5, 2.0 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **432** (216 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |
| Reward:risk target | Fixed 2:1 (not part of the grid — see Implementation Semantics in README) |
| Forced exit | 50 bars |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `rsi_period` | 14 |
| `swing_lookback` | 5 |
| `div_tolerance` | 0 |
| `confirmation` | bullish_candle |
| `atr_stop_mult` | 2.0 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **−0.3131** |
| Profit Factor | 0.9522 |
| Max Drawdown (R, absolute) | 156.51 |
| Total Return (R) | −129.79 |
| Number of Trades | 4,268 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage. The same configuration
(`rsi14/lb5 tol0 bullish_candle stop2.0x 15m`) was selected in all 4 windows.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | rsi14/lb5 tol0 bullish_candle stop2.0x 15m | −0.498 | +0.323 | 1.052 | 746 |
| 2 | 2003–2016 | 2017–2020 | rsi14/lb5 tol0 bullish_candle stop2.0x 15m | −0.262 | −0.751 | 0.891 | 771 |
| 3 | 2003–2018 | 2019–2022 | rsi14/lb5 tol0 bullish_candle stop2.0x 15m | −0.279 | −0.913 | 0.867 | 749 |
| 4 | 2003–2020 | 2021–2025 | rsi14/lb5 tol0 bullish_candle stop2.0x 15m | −0.375 | −0.105 | 0.984 | 971 |

IS Sharpe is negative in every window (the "best" IS configuration is already
losing in-sample), and 3 of 4 OOS windows are negative too. The lone positive
OOS window (+0.323, PF 1.052) is not corroborated by the other three and is
consistent with sampling noise rather than a durable edge.

---

## Key Finding

**No edge found.** Of the 432 grid combinations (all clear the `≥ 50` trades
filter — divergence setups are frequent, so the floor is never binding):

- 0 / 432 with Sharpe > 0
- 0 / 432 with Profit Factor > 1.0
- Best Sharpe: −0.3131 (15-min, RSI(14), swing lookback 5, no tolerance,
  bullish-candle confirmation, 2.0× ATR stop)
- Worst Sharpe: −9.71 (5-min, swing lookback 3, tolerance 5, `any_bar`
  confirmation, 1.0× ATR stop — 64,531 trades, spread-dominated)

RSI divergence, as specified (fractal-pivot detection + RSI comparison +
fixed 2:1 target), has no exploitable edge on EURUSD across the full 23-year
history at either timeframe tested.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min clearly outperforms 5-min (mean Sharpe −1.22 vs −4.31) — more frequent 5-min divergence signals are lower quality and pay the fixed 0.8-pip spread more often |
| `confirmation` | `bullish_candle` beats `any_bar` on average (mean Sharpe −2.33 vs −3.21) — filtering out confirmation bars that close against the trade direction removes some of the weakest setups |
| `swing_lookback` | Longer lookbacks are less bad (mean −3.76 at 3 bars → −2.18 at 10 bars) — stricter swing-pivot definitions produce cleaner, less noisy divergences |
| `atr_stop_mult` | Wider stops reduce loss (mean −3.63 at 1.0× → −2.13 at 2.0×) — tight stops get clipped by noise before the reversion plays out |
| `div_tolerance` | Tighter tolerance (0 RSI points, i.e. requiring a strictly higher/lower RSI) is marginally better (mean −2.48 at 0 → −3.01 at 5) — looser tolerance admits weaker, non-divergent pairs as false positives |
| `rsi_period` | Weak effect; RSI(14) marginally best (mean −2.73 vs −2.76 at 10, −2.81 at 7) |

Direction of "least bad": 15-min, RSI(14), swing lookback 8–10, no tolerance,
bullish-candle confirmation, wide (2.0×) ATR stop. Even at these settings
expectancy stays firmly negative — the search narrows the loss, it does not
flip it positive.

---

## Recommendation

**Do not implement MR-10 standalone.**

Fractal-pivot RSI divergence, even filtered by a directional confirmation
candle and a strict (zero-tolerance) divergence definition, is net-losing on
EURUSD across the full grid and every walk-forward window bar one noisy OOS
outlier. The fixed 2:1 reward:risk target may itself be a weak assumption —
divergence signals often mark exhaustion rather than a move large enough to
reach 2R before reverting again; a tighter or ATR-adaptive target could be
worth testing in a follow-up, but is out of scope for this grid.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | MR-13 MFI Extremes | Volume-weighted oscillator instead of pure momentum — may reduce false-positive divergences seen here |
| 2 | MR-14 StochRSI | Faster, bounded oscillator; compare divergence responsiveness against RSI |
| 3 | MR-15 DeMarker | Alternative exhaustion oscillator with its own extremes definition |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 432 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
