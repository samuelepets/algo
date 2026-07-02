# MR-19 — Connors RSI (3-Component) Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-19`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

Connors RSI (CRSI) averages three components: RSI(rsi_period) of close, a
second RSI applied to the consecutive up/down "streak" length series
(`ud_rsi_period`), and a percentile rank of the 1-bar ROC over a trailing
window (`roc_rank_period`). Fades extremes: long when CRSI crosses below
`oversold_thresh` (optionally trend-filtered), short when it crosses above
`overbought_thresh`.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| CRSI | `(RSI(rsi_period) + UD_RSI(ud_rsi_period) + ROC_percentile(roc_rank_period)) / 3`, three components cached independently and combined per-bar |
| UD_RSI | Standard RSI formula applied to the streak-length series (not price) |
| ROC percentile | `100 × (count of ROC(1) values in the trailing window ≤ current) / window` |
| Exit | CRSI crosses back through `exit_level` (long) / `100 − exit_level` (short) |
| Trend filter | `close > SMA(trend_sma)` gates longs, `close < SMA(trend_sma)` gates shorts; `trend_sma = none` disables it |
| Stop | **Fixed** `1.5 × ATR(14)` — the strategy's own search-space table in the doc omits an `atr_stop_mult` dimension (unique among all MR strategies), so this is a constant, not grid-searched |
| Max holding period (not specified) | Forced exit at 50 bars |

### Numerical stability

Same `ATR_FLOOR` guard as mr09/mr14/mr15/mr18/mr20, set to `1e-5` (matching
`mr09_ema_distance`'s established floor). Verified this floor is not the
driver of the high-PF, low-trade-count rows discussed below — re-running
with a looser `1e-6` floor produced byte-identical top-10 results, so those
rows are a genuine (if statistically thin) property of the strategy, not a
numerical artifact.

## Parameter Search Space

```
rsi_period        : [2, 3, 4]
ud_rsi_period     : [2, 3]
roc_rank_period   : [50, 100, 200]
oversold_thresh   : [5, 10, 15, 20]
overbought_thresh : [95, 90, 85, 80]
exit_level        : [50, 55, 60]
trend_sma         : [None, 100, 200]
timeframe         : [5min, 15min]
```

Total combinations: **5,184** (2,592 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (21)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-02)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 5,184 combos) + walk-forward | **32–34 s** end-to-end |

## Result (research)

**By far the broadest full-history positive cluster found in
`cat02_mean_reversion` — but walk-forward shows the sharpest IS/OOS
divergence in the category.** 2,155 / 5,175 combinations (42%) that clear
the `≥ 50` trades filter have positive Sharpe and PF > 1.0. Best: Sharpe
**+0.380**, PF **1.13**, 2,102 trades (robust sample), at `rsi3/ud2/roc200`,
`os10/ob95`, `x60`, `trend100`, 15-min. Dominant drivers: 15-min over 5-min
(avg Sharpe −0.14 vs −1.72), longer `rsi_period`/`ud_rsi_period` (less
noisy), and a trend filter present beats no filter (avg −0.70/−0.67 with
`trend_sma=100/200` vs −1.39 with none). **Caveat:** a family of combos with
`trend_sma=none` and very selective thresholds (5/95) shows PF up to ~9–40
and average R/trade up to ~12–13, on trade counts of only 81–589 — these are
statistically thin (a handful of large winners riding the 50-bar hold can
dominate) and should not be read as a stronger edge than the broader,
higher-trade-count cluster. Walk-forward IS Sharpe is the strongest seen in
this category (+0.90 to +1.42 across all 4 windows, on 15-min with the trend
filter), yet **OOS is negative in every window** (−0.21 to −0.69) — the
widest IS/OOS gap found so far, consistent with substantial overfitting to
the in-sample period despite the broad full-history cluster. See
[`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-07-02. `uv run pytest` (21 tests) and
`uv run ruff check` pass.
