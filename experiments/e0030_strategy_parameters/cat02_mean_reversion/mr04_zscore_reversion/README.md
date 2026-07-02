# MR-04 — Z-Score Statistical Reversion Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-04`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`tf01_ema_crossover_python/`](../../cat01_trend_following/tf01_ema_crossover_python/)
performance conventions and using the shared `algo_shared` library.

## Strategy Summary

The rolling z-score of a return/price series measures how far the current
value sits from its recent statistical mean, in units of standard deviation.
`|Z|` exceeding a threshold flags a statistical extreme that tends to correct
toward zero. Two candidate z-score definitions are tested: the z-score of
bar-over-bar **log-returns**, and the z-score of **close price detrended** by
its own rolling mean. Entries fade the extreme; exits target reversion back
inside a (looser) exit threshold, an ATR-based stop, or a fixed-bar
forced-exit safety net.

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| Entry: `\|Z\| > entry_threshold` | `zscore_log_return` or `zscore_close_detrended`, selected per grid row via `input_type` |
| Exit: Z reverts toward 0 | `exit_threshold` grid dimension (`z[i] >= -exit_threshold` for longs, mirrored for shorts) |
| Stop: statistical extreme "extends further" | Static stop at entry, `atr_stop_mult × ATR(14)`, distance = `dist`; skipped if `dist <= 1e-10` |
| Max holding period | No `max_hold_bars` grid dimension exists for MR-04. Instead a **fixed** (not grid-searched) `MAX_HOLD_SAFETY = 200` bars forces an exit at close, bounding worst-case holding time regardless of the chosen thresholds. |
| Two z-score definitions | `input_type ∈ {log_return, close_detrended}`; both precomputed once per `(window, timeframe)` pair into two cache matrices sharing a row index |
| `log_returns` warm-up NaN vs SMA accumulator | `log_returns(close)[0]` is NaN (no prior bar). Feeding that NaN into `sma`'s sliding-window accumulator would poison every later output (a NaN never clears from a running sum), so `zscore_log_return` feeds `sma`/`rolling_std` a sanitized copy with index 0 set to `0.0`, while the final z-score output still checks the *original* return series for NaN — `z[0]` is still NaN as expected. |
| Spread cost | `0.00008` (0.8 pip round-trip), consistent with cat01/MR-01 |

## Parameter Search Space

```
zscore_window    : [20, 30, 60, 120, 240]              — 5 values
entry_threshold  : [1.5, 2.0, 2.5, 3.0]                 — 4 values
exit_threshold   : [0.0, 0.5]                            — 2 values
atr_stop_mult    : [0.75, 1.0, 1.5, 2.0]                — 4 values
input_type       : [log_return, close_detrended]         — 2 values
timeframe        : [5min, 15min]                         — 2 values
```

Total combinations: **640** (320 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`. Fixed forced-exit safety net:
`MAX_HOLD_SAFETY = 200` bars (not grid-searched).

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests (19)
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The
first invocation pays a one-time Numba JIT compilation cost; compiled kernels
are cached on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip it.

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Load 8,490,235 1-min bars | 2.1 s |
| Resample + cache z-score indicators (both TFs) | 4.76 s (5-min 4.03 s, 15-min 0.73 s) |
| Full grid, 5-min (320 combos) | 1.49 s |
| Full grid, 15-min (320 combos) | 0.13 s |
| Walk-forward (4 windows) + CSV writes | ≈ 1.2 s |
| **End-to-end (script-reported)** | **9.7 s** |

## Result (research)

**No edge found.** All 640 grid combinations clear the `≥ 50` trades filter
(the lowest trade count observed is well above 50), and **none has a
positive Sharpe ratio or profit factor above 1.0**. The best combination —
`zscore_window=20, entry=3.0, exit=0.0, atr_stop=1.5×, close_detrended, 15-min`
— has Sharpe **−0.2215** and profit factor **0.9716** over 6,470 trades. The
worst combination (5-min, tight `entry=1.5`, tight `exit=0.5`, tight
`atr_stop=0.75×`, log-return input) has Sharpe −18.08 across 188,913 trades —
extreme overtrading dominated by the spread. Averaged across all valid
combos, `close_detrended` clearly outperforms `log_return` as an input
(mean Sharpe −2.07 vs −4.58), 15-min clearly outperforms 5-min (mean Sharpe
−1.86 vs −4.78), and wider entry thresholds are systematically less bad
(mean Sharpe −1.80 at `entry=3.0` vs −5.34 at `entry=1.5`) — but the
direction of "least bad" never crosses into positive territory. Walk-forward
confirms the pattern: the same IS-selected configuration
(`w20 entry2.5 exit0.0 stop1.5x/2.0x close_detrended 15m`) is OOS-negative in
all 4 windows (Sharpe −0.29 to −0.87), and OOS Sharpe is consistently worse
than IS Sharpe in every window. See [`RESULTS.md`](./RESULTS.md) for the full
analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (19 tests) and
`uv run ruff check` pass.
