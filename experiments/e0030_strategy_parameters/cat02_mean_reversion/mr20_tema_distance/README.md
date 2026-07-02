# MR-20 — TEMA Distance Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-20`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

TEMA (Triple EMA) removes most of the lag of a simple EMA. Fade price when
its distance from TEMA, measured in ATR units, exceeds `distance_thresh`:
short when price is too far above TEMA, long when too far below. Exit either
at TEMA itself (`tema_touch`) or a static half-distance level fixed at entry
(`half_distance`).

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| TEMA formula | `3×EMA1 − 3×EMA2 + EMA3` (chained EMAs), as specified |
| Exit: `tema_touch` | Dynamically-updated TEMA target |
| Exit: `half_distance` | Static target = entry ± half the ATR-distance observed at entry |
| Stop | `atr_stop_mult × ATR(atr_period)` from entry |
| Max holding period (not specified) | Forced exit at 100 bars (documented safety net) |

### Numerical stability fix (ATR floor)

The distance signal is `(close − TEMA) / ATR`. During extended flat-price
stretches in the resampled bars (weekend/holiday gaps where a bucket repeats
the last traded price with zero range), Wilder ATR decays exponentially
toward machine epsilon (observed as low as `2.1e-16` in this corpus) without
ever hitting exactly zero. A naive `ATR ≈ 0` guard (`< 1e-12`, matching
mr01's convention) does not catch this: `distance` explodes trivially past
any threshold, triggering entries with an economically meaningless
near-zero-risk stop, and a single such trade can then produce an R-multiple
in the millions, corrupting `total_return`/`profit_factor`/`max_drawdown`
for that grid cell while leaving Sharpe misleadingly close to normal (mean
and std scale together). Fixed by gating on a realistic floor, `ATR < 1e-6`
(EURUSD ATR is never legitimately below this), matching the `ATR_FLOOR`
guard already used in [`mr09_ema_distance`](../mr09_ema_distance/), which
has the same `distance = (close − ref) / ATR` shape. Verified: before the
fix, the top-10 by Sharpe had `profit_factor` up to 90 and
`max_drawdown_r` up to ~345,000 (versus O(1)–O(1,000) everywhere else in
this category) — all such rows disappeared after the fix, and Sharpe
rankings changed materially (see Result below for the corrected numbers).

## Parameter Search Space

```
tema_period      : [9, 14, 21, 30]
distance_thresh  : [1.0, 1.5, 2.0, 2.5]
atr_period       : [10, 14]
exit_type        : ["tema_touch", "half_distance"]
atr_stop_mult    : [0.75, 1.0, 1.5]
timeframe        : [5min, 15min]
```

Total combinations: **384** (192 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (17)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).

## Performance (measured 2026-07-02)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 384 combos) + walk-forward | **3.9 s** end-to-end |

## Result (research)

**The strongest full-history cluster found in this category — but it does
not survive walk-forward.** 81 / 384 combinations (21%) clear positive
Sharpe and PF > 1.0 — a broader cluster than MR-08's 11%. Best: Sharpe
**+0.457**, PF **2.64**, 3,513 trades, at `tema21`, `atr10`,
`distance_thresh=2.5`, `tema_touch` exit, `atr_stop=0.75×`, 5-min. Wider
distance thresholds are strongly better (avg Sharpe −0.23 at 2.5 ATR vs
−3.26 at 1.0 ATR); `tema_touch` beats `half_distance` (avg −0.69 vs −1.90);
15-min beats 5-min on average (−0.63 vs −1.97) even though the single best
cell is 5-min. However, walk-forward is negative in all 4 OOS windows
(−0.26 to −1.78), including window 3/4 which select a configuration from the
same good family (`tema21`, `dist2.5`, `atr_stop=0.75×`) — same pattern as
MR-08: a real, non-trivial full-history cluster that is not stable enough to
select from partial history and trade forward profitably. See
[`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-07-02. `uv run pytest` (17 tests) and
`uv run ruff check` pass. Grid search re-run after the ATR-floor fix
described above; all numbers in this document are post-fix.
