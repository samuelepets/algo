# MR-10 — RSI Divergence Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-10`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`tf01_ema_crossover_python/`](../../cat01_trend_following/tf01_ema_crossover_python/)
performance conventions and using the shared `algo_shared` library.

## Strategy Summary

Detect RSI divergence between the two most recently *confirmed* fractal swing
pivots: a bullish divergence is a lower price low paired with a higher (or
tolerance-band-equal) RSI low; a bearish divergence is a higher price high
paired with a lower RSI high. Enter on the bar the divergence is confirmed
(optionally gated by a directional confirmation candle), stop beyond the
divergence's most recent pivot (capped by an ATR multiple), and target a fixed
2:1 reward:risk.

## Implementation Semantics

The prose spec leaves several implementation details unspecified; the
"Implementation guidance" block in the task brief resolved most of them. This
table documents every choice actually made in code:

| Spec (strategies doc) | This implementation |
|---|---|
| Swing pivot detection, N bars each side | Fractal detector: `low[p]` (or `high[p]`) is the strict min/max of the `2*lookback+1`-bar window centred on `p`; ties broken toward the *last* bar achieving the extreme in the window (see `indicators.pivot_lows` / `pivot_highs`) |
| No-lookahead pivot confirmation | A pivot at index `p` is only used starting at bar `p + lookback` (the earliest bar at which the full window is known); the backtest loop re-derives `p = i - lookback` each bar |
| Bullish divergence: price lower low, RSI higher low (within tolerance) | `cur_low_price < prev_low_price AND cur_low_rsi > prev_low_rsi - div_tolerance`, evaluated only between the two most recently *confirmed* pivot lows |
| Bearish divergence: mirror | `cur_high_price > prev_high_price AND cur_high_rsi <= prev_high_rsi + div_tolerance` |
| Entry: confirmation candle after divergence | `any_bar` → enter at the confirmation bar's close (`i = k + lookback`). `bullish_candle` → additionally require `close[i] > open[i]` (long) / `close[i] < open[i]` (short) on that *same* confirmation bar; if not met, the setup is skipped outright (no waiting for a later bar — keeps the backtest lookahead-free, per the task brief) |
| Stop: below/above divergence pivot | `stop = entry ∓ dist` where `dist = min(pivot_distance, atr_stop_mult × ATR(14))` — the pivot-based stop is capped by an ATR multiple so a single very-old/far pivot cannot produce an unbounded risk. Pivot-distance is guaranteed ≥ 0 by construction: the pivot bar's low/high is, by definition, the extreme of a window that includes the confirmation bar |
| Exit target (unspecified in doc) | Fixed 2:1 reward:risk from entry (`target = entry ± 2 × dist`), documented as a pragmatic choice since the strategy doc gives no explicit target rule |
| Forced-exit safety net | 50 bars (`FORCED_EXIT_BARS`), applied identically at both timeframes |
| Both a bullish and bearish signal fire on the same bar (rare) | Setup skipped entirely (ambiguous) rather than picking one arbitrarily |
| Spread cost | `0.00008` (0.8 pip round-trip), consistent with MR-01 |

## Parameter Search Space

```
rsi_period       : [7, 10, 14]                — 3 values
swing_lookback   : [3, 5, 8, 10]              — 4 values
div_tolerance    : [0, 3, 5]                  — 3 values
confirmation     : [any_bar, bullish_candle]  — 2 values
atr_stop_mult    : [1.0, 1.5, 2.0]            — 3 values
timeframe        : [5min, 15min]              — 2 values
```

Total combinations: **432** (216 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`. Reward:risk target: fixed 2:1.

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests (22)
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost; compiled kernels
are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip it.

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Load 8,490,235 1-min bars | 2.1 s |
| Resample + cache indicators (both TFs) | 0.9 s |
| Full grid, 5-min (216 combos) | 1.9 s |
| Full grid, 15-min (216 combos) | 0.1 s |
| Walk-forward (4 windows) | included |
| **End-to-end** | **8.4 s** |

## Result (research)

**No edge found.** All 432 grid combinations clear the `≥ 50` trades filter
(divergence signals are frequent enough that the trade-count floor is not
binding), yet **zero of them has a positive Sharpe ratio or profit factor
above 1.0**. The best combination — `rsi14/lb5 tol0 bullish_candle stop2.0x
15m` — manages only Sharpe −0.313 (PF 0.952). The 15-minute timeframe is
markedly less bad than 5-minute (mean Sharpe −1.22 vs −4.31 across all valid
combos): tighter timeframes generate far more (lower-quality) divergence
signals and pay the fixed spread more often per unit of time. The
`bullish_candle` confirmation filter modestly outperforms `any_bar` (mean
Sharpe −2.33 vs −3.21) by rejecting weak confirmation bars, and wider ATR
stops (2.0×) and longer swing lookbacks (8–10 bars) are both "less bad" —
consistent with divergence quality improving as the swing definition gets
stricter and the stop gets more breathing room. None of these effects flips
the strategy positive. Walk-forward confirms the pattern: the IS-selected
configuration is OOS-negative in 3 of 4 windows (Sharpe −0.10 to −0.91), with
only one window (2015–2018) OOS-positive (+0.32) — consistent with noise
rather than a durable edge. See [`RESULTS.md`](./RESULTS.md) for the full
analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (22 tests) and
`uv run ruff check` pass.
