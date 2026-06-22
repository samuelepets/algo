# TF-11 — Ichimoku Cloud System Parameter Search

**Strategy reference:** [`strategies/01_TREND_FOLLOWING.md § TF-11`](../../../../strategies/01_TREND_FOLLOWING.md)
**Instrument:** EURUSD 2003–2025 (1-min → 15-min and 1-h)
**Implementation:** Python (uv-managed; Numba hot loops). Follow [`../tf01_ema_crossover_python/`](../tf01_ema_crossover_python/) — see its [`README.md`](../tf01_ema_crossover_python/README.md) and [`ROADMAP.md`](../tf01_ema_crossover_python/ROADMAP.md) (Performance engineering section).

## Strategy Summary

Complete trend system based on five lines. Full signal requires: TK bullish cross,
price above the cloud, Chikou Span above past price, and a bullish (green) cloud.
A simplified variant uses only the TK cross direction + price vs. cloud.

## Indicator Components

- **Tenkan-sen:** `(max_high(n1) + min_low(n1)) / 2`
- **Kijun-sen:** `(max_high(n2) + min_low(n2)) / 2`
- **Senkou Span A:** `(Tenkan + Kijun) / 2` displaced `n2` bars forward
- **Senkou Span B:** `(max_high(n3) + min_low(n3)) / 2` displaced `n2` bars forward
- **Chikou Span:** current close displaced `n2` bars backward

## Implementation Semantics

Same backtester conventions as the rest of the family (entries at bar close, stop
checked first intrabar, P&L in R units, spread `0.00008`). Displacement = Kijun
period `n2` (traditional). The Kijun-sen is the trailing stop.

| Spec (strategies doc) | This implementation |
|---|---|
| `tk_cross` | Tenkan crosses above Kijun AND `close` above the cloud (long); reversed short |
| `full_signal` | TK cross AND above/below cloud AND green/red cloud (Span A vs B) AND Chikou (`close > close[i−n2]`) |
| `cloud_break` | `close` crosses outward through the cloud top (long) / bottom (short) |
| Stop / initial risk R | The Kijun-sen; `R = |entry − Kijun at entry|` |
| Target | Fixed 2:1 reward-to-risk (`RR_RATIO = 2.0`) |
| Exit | Kijun touched intrabar, target reached, or an opposite TK cross |

Valid combinations: **288** (144 per timeframe). The `senkou_b ≈ 2·kijun` relation
is noted as *preferred* in the spec but **not enforced** — the full grid is searched.
Min trades filter: `≥ 50`.

## Parameter Search Space

```
tenkan      : [7, 9, 10, 13]                        — 4 values
kijun       : [20, 22, 26, 30]                      — 4 values
senkou_b    : [44, 52, 60]                           — 3 values
signal_type : [full_signal, tk_cross, cloud_break]   — 3 values
timeframe   : [15min, 1h]                            — 2 values
```

Approximate combinations: ~288 (constraint: senkou_b ≈ 2×kijun preferred).

## Expected Outputs

- `outputs/results.csv`
- `outputs/top_params.json`
- `outputs/walkforward.csv`

## How to Run

```bash
# From this directory. Requires uv (https://docs.astral.sh/uv/).
uv sync                 # create .venv and install pinned deps
uv run python main.py   # full run: load + grid + walk-forward

# Tooling
uv run pytest           # unit tests
uv run ruff check       # lint
```

Data path `../../../../data/bars/EURUSD/` must exist (read-only corpus). The first
invocation pays a one-time Numba JIT compilation cost; compiled kernels are cached
on disk (`NUMBA_CACHE_DIR=.numba_cache`) so subsequent runs skip it.

## Performance (2026-06-22 run)

| Phase | Time |
|---|---|
| **End-to-end** | **2.8 s** |

## Expected Result (research)

**No edge found on full history** — all 288 combinations net-losing. Best Sharpe -0.55. All 4 oos windows negative.
See [`RESULTS.md`](./RESULTS.md) for the full analysis and cross-strategy comparison card.

## Status

Complete. Run date: 2026-06-22. `uv run pytest` and `uv run ruff check` pass.
Full-history parameter search completed; outputs in `outputs/` (gitignored).
