# MR-05 — Stochastic %K/%D Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-05`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

Enter on a Stochastic %K/%D crossover confirmation inside an extreme zone:
long when %K is below the oversold threshold and crosses above %D; short when
%K is above the overbought threshold and crosses below %D. `slowing` is the
SMA-smoothing period applied to raw %K before computing %K/%D ("slow
stochastic").

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Entry trigger | %K crosses %D while %K is beyond the oversold/overbought threshold, evaluated at bar close |
| Exit target (not specified in doc) | %K/%D crosses back through the midline (50), OR `max_hold_bars`, whichever first |
| Stop | `atr_stop_mult × ATR(14)` from entry |

## Parameter Search Space

```
k_period         : [5, 9, 14, 21]
d_period         : [3, 5]
slowing          : [1, 3]
oversold_thresh  : [15, 20, 25]
overbought_thresh: [85, 80, 75]
atr_stop_mult    : [0.75, 1.0, 1.5]
max_hold_bars    : [5, 10, 15, 20]
timeframe        : [5min, 15min]
```

Total combinations: **3,456** (1,728 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest            # unit tests (20)
uv run ruff check        # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 3,456 combos) + walk-forward | **16.0 s** end-to-end |

## Result (research)

**No edge found.** All 3,456 combinations that clear the `≥ 50` trades filter
have negative Sharpe — best is −2.13 (PF 0.86, 25,591 trades). Crossover-based
Stochastic reversion overtrades badly: the best combo still generates over
25,000 trades across 23 years, and transaction costs dominate. 15-min is
materially less bad than 5-min (avg Sharpe −4.60 vs −15.04); wider ATR stops
help slightly (−8.02 at 1.5× vs −11.60 at 0.75×). Walk-forward confirms the
picture: IS Sharpe is already strongly negative in every window (−1.48 to
−2.03), and OOS is worse in every window (−2.46 to −3.08). See
[`RESULTS.md`](./RESULTS.md) for details.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (20 tests) and
`uv run ruff check` pass.
