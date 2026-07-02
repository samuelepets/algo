# MR-02 — RSI(2) Ultra-Short Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-02`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`tf01_ema_crossover_python/`](../../cat01_trend_following/tf01_ema_crossover_python/)
performance conventions and using the shared `algo_shared` library.

## Strategy Summary

Larry Connors' RSI(2) system: a very short (2–4 period) RSI reaching an
extreme level (e.g. `< 5` or `> 95`) signals a short-term overextension that
tends to snap back within a handful of bars. Enter long when RSI dips below
`long_threshold`, enter short when RSI rises above `short_threshold`. An
optional SMA trend filter restricts longs to above the SMA and shorts to
below it. Exit on RSI crossing back through an exit threshold, on a fixed
1.5x ATR stop, or after a maximum holding period — whichever comes first.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Trend filter: "SMA(200)" text but table lists "Trend filter EMA" | Implemented as an SMA (simple moving average), not an EMA — the spec's own indicator section explicitly names `SMA(200)`, so the parameter is computed as SMA despite the "EMA" label in the parameter table. `trend_ema` grid values `{None, 100, 200}` select the SMA period; `None` is encoded as sentinel `0` (no filter), matching the `adx_filter=0` convention used in `mr01_bollinger_band`. |
| Stop: "Hard stop: 1.5x ATR from entry" | Implemented as a fixed constant `ATR_STOP_MULT = 1.5` in `backtest.py` — **not** a grid dimension, per the spec's own Brute-Force Parameter Search Space table (which does not list an ATR-stop dimension). |
| RSI(2) Wilder smoothing | Standard Wilder RS/RSI recursion. Differencing consumes the first bar, so the `period`-bar seed average is built from `gain[1..period]`/`loss[1..period]`, and the first valid RSI output lands at array index `period` — one bar later than a same-period ATR/SMA seed (which starts differencing at index 0 and seeds at index `period - 1`). |
| RSI edge cases | `avg_loss == 0 and avg_gain == 0` (flat/no movement) → RSI = 50.0 (neutral, not 100 or undefined). `avg_loss == 0 and avg_gain > 0` (strictly rising) → RSI = 100.0. Both cases fall out of the recursion naturally except the true `0/0` tie, which is special-cased. |
| Entry: "Price above SMA(200) AND RSI(2) < 5" | `long_sig = (trend_ema == 0 OR close > trend_sma) AND rsi < long_threshold`; symmetric for shorts. Entry price is the signal bar's close (consistent with "enter on bar close" in the spec). |
| Exit: "RSI crosses above 55 / below 45" | Implemented as a threshold **touch**, not a strict prior-bar/current-bar crossing check: `rsi[i] >= exit_rsi_long` (long) / `rsi[i] <= exit_rsi_short` (short) on the current bar, checked every bar while in position. This is simpler than tracking the previous RSI value and is consistent with `mr01`'s target-touch exit style. |
| Exit priority | Stop-loss checked first, then RSI exit, then max-hold forced exit — same ordering as `mr01_bollinger_band`. |
| Spread cost | `0.00008` (0.8 pip round-trip), consistent with `mr01`/cat01 conventions. |

## Parameter Search Space

```
rsi_period       : [2, 3, 4]                  — 3 values
long_threshold   : [2, 5, 10, 15]              — 4 values
short_threshold  : [98, 95, 90, 85]            — 4 values
exit_rsi_long    : [50, 55, 60, 65]            — 4 values
exit_rsi_short   : [50, 45, 40, 35]            — 4 values
trend_ema        : [none, 100, 200]            — 3 values (SMA period; none = no filter)
max_hold_bars    : [3, 5, 10, 15]              — 4 values
timeframe        : [5min, 15min]               — 2 values
```

Total combinations: **18,432** (9,216 per timeframe). `atr_stop_mult` is
fixed at `1.5` (not a grid dimension). Spread cost: `0.00008` (0.8 pip
round-trip). Min trades filter: `≥ 50`.

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
| Load 8,490,235 1-min bars | 2.7 s |
| Resample + cache indicators, 5-min | 0.31 s |
| Resample + cache indicators, 15-min | 0.04 s |
| Full grid, 5-min (9,216 combos) | 10.09 s |
| Full grid, 15-min (9,216 combos) | 3.50 s |
| Walk-forward (4 windows, IS re-search + OOS eval) | ≈ 37.1 s |
| **End-to-end** | **53.7 s** |

## Result (research)

**Weak, non-robust edge — not confirmed out-of-sample.** Of the 18,240
combinations that clear the `≥ 50` trades filter, 3,600 (19.7%) have a
positive Sharpe ratio (and, exactly matching, profit factor `> 1.0`). The
full-history best combination — `RSI(3)`, long `< 5`, short `> 98`, exit-long
`≥ 50`, exit-short `≤ 40`, SMA(100) trend filter, `max_hold=10`, 15-min —
reaches **Sharpe 0.85, profit factor 1.42, 848 trades, total return +98.3 R**.
That looks like a real signal on paper, and the SMA trend filter and 15-min
timeframe both clearly help (mean Sharpe across valid combos: 15-min −0.53 vs
5-min −3.26; SMA(100)/SMA(200) filter −1.35/−1.48 vs no filter −2.84).

However, walk-forward with anchored IS windows tells a different story for
the *same, consistently-selected* configuration family (`RSI(3)` / SMA(100) /
15-min was picked as the IS-best in all 4 windows): IS Sharpe is a strong
1.13–1.46 in every window, but OOS Sharpe is +0.665 (2015–2018), +0.017
(2017–2020, essentially flat), **−0.562** (2019–2022), and **−0.139**
(2021–2025). Only 1 of 4 OOS windows clears profit factor 1.0 by a meaningful
margin (1.10); the other three sit at 0.93–1.00. The edge, if any, has decayed
to roughly zero-to-negative over the last ~7 years of the sample — this is the
signature of in-sample overfitting on a low-persistence pattern, not a stable
statistical edge. See [`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (22 tests) and
`uv run ruff check` pass.
