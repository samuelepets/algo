# RESULTS — MR-09 Price/EMA Distance (Rubber Band)

> Standardised results card for cross-strategy comparison.
> All `RESULTS.md` files across `e0030_strategy_parameters` follow the
> same schema so they can be merged into a comparison table later.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr09_ema_distance` |
| Strategy | Price/EMA Distance (Rubber Band) |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-09` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 1-min (native), 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 24.5 s end-to-end |
| Run date | 2026-07-01 |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `ema_period` | 10, 20, 50, 100 (4 values) |
| `atr_period` | 10, 14 (2 values) |
| `distance_thresh` | 1.0, 1.5, 2.0, 2.5, 3.0 (5 values) |
| `exit_target` | ema, half_distance (2 values) |
| `adx_filter` | none, <20, <25 (3 values) |
| `atr_stop_mult` | 1.0, 1.5, 2.0 (3 values) |
| `tf_min` | 1, 5, 15 (3 values) |
| **Total combinations** | **2,160** (720 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |
| Forced-exit safety net | 100 bars (no `max_hold_bars` dimension in this grid) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `ema_period` | 50 |
| `atr_period` | 14 |
| `distance_thresh` | 2.5 |
| `exit_target` | ema |
| `adx_filter` | <20 |
| `atr_stop_mult` | 1.5 |
| `tf_min` | 15 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **0.1236** |
| Profit Factor | 1.0196 |
| Max Drawdown (R, absolute) | 85.81 |
| Total Return (R) | 54.58 |
| Number of Trades | 4,265 |

> Max Drawdown is the largest peak-to-trough decline of the cumulative-R
> equity curve in absolute R (curve starts at 0 R, value always ≥ 0).

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

Each window re-optimises the full grid on the IS slice only and evaluates the
selected set on OOS — no full-history leakage.

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | ema50/atr14 d2.5 ema adx<20 stop1.5x 15m | 0.044 | +0.242 | 1.036 | 852 |
| 2 | 2003–2016 | 2017–2020 | ema50/atr14 d2.5 ema adx<20 stop1.5x 15m | 0.215 | −0.639 | 0.910 | 833 |
| 3 | 2003–2018 | 2019–2022 | ema20/atr10 d1.5 ema adx<20 stop1.5x 15m | 0.111 | −0.687 | 0.936 | 1,972 |
| 4 | 2003–2020 | 2021–2025 | ema50/atr14 d2.5 ema adx<20 stop1.5x 15m | 0.000 | +0.494 | 1.073 | 1,150 |

2 of 4 windows are OOS-positive, 2 are OOS-negative — the sign flips across
windows with the same selected configuration, indicating an unstable,
non-reproducible effect rather than a persistent edge. IS Sharpe is itself
always close to zero (0.00 to 0.22).

---

## Key Finding

**No edge found.** Of the 2,160 combinations (all clear the `≥ 50` trades
filter):

- 4 / 2,160 (0.2%) with Sharpe > 0
- 4 / 2,160 (0.2%) with Profit Factor > 1.0 (the same 4 combinations)
- Best Sharpe: 0.1236 (15-min, ema50/atr14, distance 2.5, ADX<20, stop 1.5×)
- Mean Sharpe by timeframe: 1-min −23.61, 5-min −2.92, 15-min −0.98

A data-quality issue was found and fixed during development: EURUSD 1-min
ATR can decay to near-zero (down to ~1e-37) during illiquid, fully-flat
stretches, and dividing the distance signal / stop distance by such values
produced pathological outlier trades (multi-million-R total returns, PF > 9)
that were pure numerical artifacts, not signal. An `ATR_FLOOR = 1e-5`
(~0.1 pip) guard was added to both the distance calculation and the stop
sizing; all numbers in this report are post-fix.

Even after the fix, the strategy is essentially breakeven at its best corner
and net-losing everywhere else in the grid — 99.8% of tested configurations
have negative Sharpe.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| Timeframe | 15-min is clearly the least bad (mean Sharpe −0.98) vs 5-min (−2.92) and 1-min (−23.61) — higher-frequency EMA-distance trading is dominated by spread and by the ATR-floor-filtered noise regime |
| `distance_thresh` | Wider threshold is monotonically less bad (mean −16.02 at 1.0 → −4.15 at 3.0) — shallow deviations are not exploitable, only large ones approach breakeven |
| `atr_stop_mult` | Wider stops reduce loss (mean −11.29 at 1.0× → −7.33 at 2.0×) |
| `ema_period` | Shortest period (10) is least bad on average (−7.97) but the single best combo uses period 50 — no clean monotonic relationship |
| `exit_target` | `ema` (dynamic target) beats `half_distance` on average (mean −8.01 vs −10.33) |
| `adx_filter` | `<20` is least bad (mean −7.67) vs `<25` (−9.25) and no filter (−10.60) — the regime gate has a real but small effect |

Direction of "least bad": 15-min timeframe, wide distance threshold (2.5–3.0),
wide ATR stop (2.0×), dynamic EMA exit target, ADX<20 filter. Even at the
single best point in the grid, Sharpe is only marginally positive and does
not hold up consistently out-of-sample.

---

## Recommendation

**Do not implement MR-09 standalone.**

The EMA-distance rubber-band signal is essentially breakeven at its best and
net-losing across 99.8% of the grid on EURUSD. The one positive corner
(15-min, wide threshold, ADX filter) does not survive walk-forward — half the
OOS windows are negative with the identical selected configuration, which is
inconsistent with a genuine, persistent statistical edge rather than
in-sample noise. As implemented, the raw distance signal is too weak on its
own; a viable version would likely need a session/liquidity filter (this
research surfaced that raw EURUSD 1-min ATR itself is unreliable during
illiquid hours) or a materially different reference (e.g. VWAP or a
volatility-regime-conditioned EMA) rather than a plain fixed-period EMA.

| Priority | Next strategy | Key addition |
|---|---|---|
| 1 | MR-14 StochRSI Reversion | Double-smoothed oscillator, structurally different signal construction from a raw price/EMA ratio |
| 2 | MR-15 DeMarker Reversion | Rolling-mean based oscillator, bounded [0,1], no ATR-division fragility |
| 3 | MR-03 VWAP Deviation (if implemented) | Session-anchored institutional reference instead of a rolling EMA |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 2,160 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
