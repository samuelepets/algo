# MR-14 — Stochastic RSI Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-14`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

StochRSI applies the Stochastic %K formula to an RSI series instead of to
price, producing an oscillator in `[0, 1]` that reaches extremes far more
often than raw RSI. Long when the smoothed %K crosses below
`oversold_thresh`, short when it crosses above `overbought_thresh`, exiting
at the 0.5 midline.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| StochRSI formula | Stochastic %K formula applied to a rolling RSI window, in `[0, 1]` |
| K/D lines | Only %K (SMA-smoothed) drives entries/exits; `smooth_d` is recorded in the output for spec fidelity but the %D line is not otherwise used, per the simplified entry rule |
| Exit | %K crosses back through the 0.5 midline |
| Stop | `atr_stop_mult × ATR(14)` from entry |
| Max holding period (not specified) | Forced exit at 100 bars |

### Numerical stability fix (ATR floor)

Same class of bug as [`mr20_tema_distance`](../mr20_tema_distance/): during
extended low-volatility/flat-price stretches (weekend/holiday gaps in the
resampled bars), Wilder ATR decays toward machine epsilon. Unlike MR-20,
this strategy's entry signal does *not* divide by ATR — but StochRSI is
**scale-invariant** (built from relative RSI gains/losses), so it can still
register spurious extreme readings from sub-pip price noise during exactly
the same stretches where ATR has collapsed. An entry triggered there gets an
economically meaningless near-zero-risk stop, and the resulting trade's
R-multiple can reach into the tens of thousands. Initial (unfixed) results
showed a top-10 cluster with **positive** Sharpe (+0.17, PF 1.27); after
adding an `ATR < 1e-6` floor (matching `mr09_ema_distance`'s `ATR_FLOOR` and
the `mr20` fix), that cluster disappeared entirely — confirming it was an
artifact, not a real edge. All numbers in this document are post-fix.

## Parameter Search Space

```
rsi_period        : [10, 14]
stoch_period      : [10, 14]
smooth_k          : [3, 5]
smooth_d          : [3]              (fixed, not grid-searched independently)
oversold_thresh   : [0.05, 0.10, 0.15, 0.20]
overbought_thresh : [0.95, 0.90, 0.85, 0.80]
atr_stop_mult     : [0.75, 1.0, 1.5]
timeframe         : [5min, 15min]
```

Total combinations: **768** (384 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (19)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-02)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 768 combos) + walk-forward | **5.3 s** end-to-end |

## Result (research)

**No edge found (post-fix).** 0 / 768 combinations that clear the `≥ 50`
trades filter have positive Sharpe or PF > 1.0. Best: Sharpe −0.633 (PF
0.945, 16,536 trades) at `rsi10/stoch14/k5`, `os0.05/ob0.95`, `stop1.5×`,
15-min. 15-min beats 5-min heavily (avg Sharpe −2.41 vs −8.45); wider stops
help (avg −4.27 at 1.5× vs −6.49 at 0.75×); more extreme thresholds
(0.05/0.95) beat looser ones (0.20/0.80) — avg −4.74 vs −5.97. Walk-forward
selects the same `rsi10/stoch14/k5/os0.05/ob0.95/stop1.5×/15m` combo in
every window, with near-zero-to-negative IS Sharpe and negative OOS in all
4 windows (−0.61 to −1.77). See [`RESULTS.md`](./RESULTS.md) for the full
analysis.

## Status

Complete. Run date: 2026-07-02. `uv run pytest` (19 tests) and
`uv run ruff check` pass. Grid search re-run after the ATR-floor fix
described above; all numbers in this document are post-fix.
