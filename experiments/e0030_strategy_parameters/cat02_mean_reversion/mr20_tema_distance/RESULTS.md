# RESULTS — MR-20 TEMA Distance Reversion

> Standardised results card for cross-strategy comparison.

---

## Identity

| Field | Value |
|---|---|
| Experiment | `e0030 / cat02_mean_reversion / mr20_tema_distance` |
| Strategy | TEMA Distance Reversion |
| Category | Mean-Reversion |
| Reference | `strategies/02_MEAN_REVERSION.md § MR-20` |
| Instrument | EURUSD |
| Data range | 2003-01-02 – 2025-12-31 (≈ 23.4 years) |
| Bar source | 1-min bars → resampled to 5-min and 15-min |
| Total 1-min bars | 8,490,235 |
| Implementation | Python — `uv run python main.py` ≈ 3.9 s end-to-end |
| Run date | 2026-07-02 (re-run after ATR-floor numerical fix — see README) |

---

## Grid Search Summary

| Parameter | Values tested |
|---|---|
| `tema_period` | 9, 14, 21, 30 (4 values) |
| `distance_thresh` | 1.0, 1.5, 2.0, 2.5 (4 values) |
| `atr_period` | 10, 14 (2 values) |
| `exit_type` | tema_touch, half_distance (2 values) |
| `atr_stop_mult` | 0.75, 1.0, 1.5 (3 values) |
| `tf_min` | 5, 15 (2 values) |
| **Total combinations** | **384** (192 per timeframe) |
| Min trades filter | ≥ 50 |
| Spread cost | 0.00008 (0.8 pip round-trip) |

---

## Best Combination (full history, min-trades filtered)

| Parameter | Value |
|---|---|
| `tema_period` | 21 |
| `distance_thresh` | 2.5 |
| `atr_period` | 10 |
| `exit_type` | tema_touch |
| `atr_stop_mult` | 0.75 |
| `tf_min` | 5 |

### Full-History Metrics (2003–2025)

| Metric | Value |
|---|---|
| **Sharpe Ratio** (annualised) | **+0.4573** |
| Profit Factor | 2.6393 |
| Max Drawdown (R, absolute) | 392.00 |
| Total Return (R) | 4,784.39 |
| Number of Trades | 3,513 |

> Top-10 by Sharpe are all clustered at `tema14/tema21`, `distance_thresh
> ∈ {2.0, 2.5}`, `tema_touch` exit, 5-min — a real cluster, not an isolated
> cell. Second-best (`tema21`, `stop=1.00×`): Sharpe +0.448, PF 2.43.

### Walk-Forward (anchored IS from 2003, 4 windows; IS-only parameter selection)

| Window | IS | OOS | Selected | IS Sharpe | OOS Sharpe | OOS PF | OOS Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2003–2014 | 2015–2018 | tema9/atr10 dist2.5 tema_touch stop0.75x 5m | +0.269 | −0.626 | 0.607 | 35 |
| 2 | 2003–2016 | 2017–2020 | tema30/atr10 dist1.5 tema_touch stop1.50x 15m | +0.211 | −1.781 | 0.891 | 4,783 |
| 3 | 2003–2018 | 2019–2022 | tema21/atr10 dist2.5 half_distance stop0.75x 5m | +0.149 | −0.262 | 0.956 | 653 |
| 4 | 2003–2020 | 2021–2025 | tema21/atr10 dist2.5 half_distance stop0.75x 5m | +0.129 | −0.593 | 0.899 | 871 |

IS Sharpe is positive in every window (consistent with the full-history
positive cluster existing throughout the sample), but OOS is negative in
every window. Windows 3–4 select the same `tema21`/`dist2.5` family as the
full-history best (only `exit_type` differs: `half_distance` vs
`tema_touch`) — this is closer to MR-13's "consistent selection, still
fails OOS" pattern than MR-08's "selection wanders to a different region."

---

## Key Finding

**Real, broad full-history cluster (21% of the grid) that fails walk-forward
in every window — currently the strongest, but still not tradable, result in
this category.** 81 / 384 combinations clear positive Sharpe and PF > 1.0,
concentrated at wide `distance_thresh` (2.0–2.5), longer `tema_period`
(14–21), `tema_touch` exit, tighter `atr_stop_mult` (0.75×). Unlike MR-08
(narrow 11% cluster, walk-forward selects a *different* region entirely),
MR-20's cluster is broader and walk-forward *does* select from within the
right family in 2 of 4 windows — yet OOS is still uniformly negative. This
suggests the edge, if any, is concentrated in specific historical periods
(e.g. a particular volatility regime) rather than being stationary across
the full 23-year span.

> **Implementation note:** this strategy initially showed even higher
> (spurious) Sharpe/PF due to a numerical bug — Wilder ATR decaying to
> near-machine-epsilon during flat-price data gaps, causing the
> `distance = (close−TEMA)/ATR` signal to trigger with an economically
> meaningless near-zero-risk stop. Fixed by raising the ATR validity floor
> from `1e-12` to `1e-6`; see README.md for details. All numbers above are
> post-fix.

---

## Parameter Insights

| Dimension | Observation |
|---|---|
| `distance_thresh` | Much less bad at wider thresholds (avg Sharpe −0.23 at 2.5 vs −3.26 at 1.0) — dominant driver |
| `exit_type` | `tema_touch` beats `half_distance` (avg −0.69 vs −1.90) |
| `tf_min` | 15-min better on average (avg −0.63 vs −1.97 for 5-min), though the single best cell is 5-min |
| `tema_period` | Shorter periods (9, 14) less bad on average (avg −0.71 to −0.98) than longer (30: avg −2.13) |
| `atr_stop_mult` | Wider stop less bad (avg −1.05 at 1.5× vs −1.51 at 0.75×) |
| `atr_period` | Weak effect (avg −1.22 at 10 vs −1.37 at 14) |

---

## Recommendation

**Do not implement MR-20 standalone, but it is the top follow-up candidate
in `cat02_mean_reversion` alongside MR-08.** The combination of (a) a broad
21%-of-grid positive full-history cluster, (b) walk-forward IS selection
landing inside that cluster's family in 2 of 4 windows, and (c) still
uniform OOS failure, points toward a regime-dependent edge rather than
random noise — worth investigating with a volatility or trend-regime overlay
(e.g. only trade the wide-distance-threshold setup when a longer-term ADX or
realized-vol filter confirms a mean-reverting regime) before dismissing it.

| Priority | Next step | Rationale |
|---|---|---|
| 1 | Check per-year Sharpe of the `tema21/dist2.5/tema_touch` combo | Identify which specific years drive the full-history edge; test if it concentrates in the 2003–2014 IS-only period |
| 2 | Add a regime filter (ADX or realized-vol percentile) | Same follow-up direction as MR-08's recommendation |

---

## Files

| File | Description |
|---|---|
| `outputs/results.csv` | All 384 combinations (not committed) |
| `outputs/walkforward.csv` | Walk-forward window metrics (not committed) |
| `main.py`, `backtest.py`, `indicators.py` | Python implementation |
