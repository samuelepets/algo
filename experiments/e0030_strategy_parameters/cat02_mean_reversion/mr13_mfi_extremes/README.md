# MR-13 — Money Flow Index (MFI) Extremes Parameter Search

**Strategy reference:** [`strategies/02_MEAN_REVERSION.md § MR-13`](../../../../strategies/02_MEAN_REVERSION.md)
**Instrument:** EURUSD 2003–2025 (1-min → 5-min and 15-min)
**Implementation:** Python (uv-managed; Numba hot loops), following the
[`mr01_bollinger_band/`](../mr01_bollinger_band/) conventions and using the
shared `algo_shared` library.

## Strategy Summary

MFI is a volume-weighted RSI: Typical Price × Volume classified as positive
or negative money flow based on the Typical Price direction, then combined
into an RSI-style ratio. Fades extremes: long when MFI crosses below
`oversold_thresh`, short when it crosses above `overbought_thresh`, exiting
when MFI crosses back through `exit_level` (50).

## Implementation Semantics

| Spec (strategies doc) | This implementation |
|---|---|
| MFI formula | Standard: `100 - 100/(1 + sum_pos/sum_neg)` over a rolling window |
| Exit: MFI crosses back through `exit_level` | Implemented as specified |
| Stop | `atr_stop_mult × ATR(14)` from entry |
| Max holding period (not specified) | Forced exit at 100 bars — MFI can stay pinned at an extreme through a strong trend, so a bar-count cap avoids unbounded holds |

## Parameter Search Space

```
mfi_period       : [7, 10, 14, 20]
oversold_thresh  : [10, 15, 20, 25]
overbought_thresh: [90, 85, 80, 75]
exit_level       : [50]
atr_stop_mult    : [1.0, 1.5]
timeframe        : [5min, 15min]
```

Total combinations: **256** (128 per timeframe). Spread cost: `0.00008`
(0.8 pip round-trip). Min trades filter: `≥ 50`.

## How to Run

```bash
uv sync
uv run python main.py   # full run: load + grid + walk-forward
uv run pytest             # unit tests (15)
uv run ruff check         # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus).
EURUSD's Volume field is a synthetic tick-count proxy (not real traded
volume), but it is non-zero and consistent, which is what MFI requires.

## Performance (measured 2026-07-01)

| Stage | Measured |
|---|---|
| Full grid (both TFs, 256 combos) + walk-forward | **2.7 s** end-to-end |

## Result (research)

**No edge, but the closest-to-breakeven result in this category so far.**
0 / 256 combinations that clear the `≥ 50` trades filter have positive
Sharpe or PF > 1.0, but the best (`mfi14`, `os10/ob90`, `stop1.0×`, 15-min)
is nearly flat: Sharpe **−0.012**, PF **0.997**, 1,565 trades. Volume
weighting (vs. plain RSI/CCI-style price oscillators elsewhere in this
category) appears to filter out some of the worst false signals. Walk-forward
is genuinely mixed: the same configuration is selected in-sample in all 4
windows with strongly positive IS Sharpe (+0.17 to +0.48), and **window 1's
OOS Sharpe is positive** (+0.114, PF 1.04, 214 trades) — the first
OOS-positive window found in this category — but windows 2–4 are OOS-negative
(−0.61 to −1.49). See [`RESULTS.md`](./RESULTS.md) for the full analysis.

## Status

Complete. Run date: 2026-07-01. `uv run pytest` (15 tests) and
`uv run ruff check` pass.
