# Reference strategy — Dual SMA crossover

This document specifies the **canonical test strategy** for experiment
`e0020_fast_backtester_composer`. Use it as the single source of truth when
re-implementing the backtester in another language, refactoring the engine, or
checking parity between implementations.

The reference implementation lives in:

- Strategy: `src/strategy.rs` (`DualSmaCrossover`)
- Indicators: `src/indicators.rs` (`sma`)
- Backtest harness: `src/backtest.rs` (`backtest`)
- Benchmark entry point: `src/bin/benchmark_sma_crossover.rs`

Run the reference benchmark:

```bash
cargo run --release --bin benchmark-sma-crossover
```

---

## Purpose

`DualSmaCrossover` is **not** meant to find a trading edge. It exists because it is:

1. **Simple** — one indicator, three parameters, deterministic state machine.
2. **Deterministic** — no randomness, no external inputs beyond the bar stream.
3. **Sensitive** — small look-ahead or off-by-one bugs materially change metrics.
4. **Fast to run** — signal generation is cheap relative to I/O on the full corpus.

Any new backtester implementation should reproduce the metrics below (within
floating-point tolerance) before adding new strategies.

---

## Scope

| Item | Value |
| ---- | ----- |
| Instrument | **EUR/USD** (`data/bars/EURUSD/`) |
| Years | All available years (currently **2003–2025**, 23 files) |
| Bar size | 1 minute OHLCV |
| Series treatment | **One continuous stream** (see [Data loading](#data-loading)) |
| Strategy | Dual SMA crossover with **fixed holding period** |
| Fast period | **50** bars |
| Slow period | **200** bars |
| Hold period | **60** bars (flat after each trade) |
| Transaction cost | **0.0** (no spread, slippage, or fees) |

Periods are expressed in **bars**, not clock time. On 1-minute data, `hold_bars =
60` keeps a position open for 60 consecutive bars (~1 hour of available bars).

---

## Data loading

Load every yearly file for the symbol, concatenate, then normalize:

1. Read `data/bars/EURUSD/EURUSD_<YEAR>.csv.gz` for each available year in
   ascending order.
2. Parse semicolon-delimited rows with header
   `Time (EET);Open;High;Low;Close;Volume`.
3. Concatenate all bars into one vector.
4. **Sort ascending** by timestamp.
5. **Drop duplicate timestamps**, keeping the **first** occurrence.

Do **not**:

- Insert synthetic bars for overnight/weekend gaps.
- Reset indicators at day, session, or year boundaries.
- Modify files under `data/`.

The resulting stream is treated as one uninterrupted sequence of bars. Indicator
windows and open-to-open returns span calendar gaps as if those bars were
adjacent (same convention as `e0010_first_ensemble`).

At the time of writing the reference run loads **8,490,235** bars. That count may
change only if the root corpus changes.

---

## Indicators

### Simple moving average (SMA)

Given a price series `close[0..n)` and integer period `P ≥ 1`:

```
SMA(P, t) = (1/P) * sum(close[t - P + 1 .. t])   for t >= P - 1
SMA(P, t) = NaN                                   for t < P - 1
```

Implementation notes:

- Use **`Close`** only; ignore Open, High, Low, Volume for this strategy.
- Rolling window: O(n) cumulative sum; arithmetic mean (not EMA/Wilder).

### Crossover events

At bar `t > 0`, when both SMAs are defined at `t` and `t - 1`:

```
bull_cross[t] = fast[t] > slow[t]  AND  fast[t-1] <= slow[t-1]
bear_cross[t] = fast[t] < slow[t]  AND  fast[t-1] >= slow[t-1]
```

---

## Signal generation

**One position at a time.** The strategy is flat most of the time. When flat, a
crossover opens a single fully invested position (+1 long or −1 short) for exactly
`hold_bars` bars, then returns to flat. New crossovers are **ignored while a
position is open**.

State machine (processed left to right, 0-based index `t`):

```
position = 0
bars_left = 0

for t in 0 .. n-1:
    if bars_left > 0:
        if bars_left == 1:
            position = 0          # close on the last bar of the hold window
            bars_left = 0
        else:
            bars_left -= 1
    elif hold_bars > 0 and t > 0 and SMAs defined at t and t-1:
        if bull_cross[t]:
            position = +1
            bars_left = hold_bars
        elif bear_cross[t]:
            position = -1
            bars_left = hold_bars

    signal[t] = position
```

Properties:

- **Event-driven**, not a continuous regime. Being above/below the slow SMA
  alone does not keep a position open; only the fixed hold window after a
  crossover does.
- **At most one open trade.** No pyramiding, no overlapping long and short.
- **Fixed exit.** There is no stop-loss, take-profit, or opposite-crossover exit;
  the position closes solely because `bars_left` reaches zero.
- `signal[t]` must depend **only** on closes up to and including bar `t`.

Before backtesting, clip each signal to `[-1, 1]` (already satisfied by the
rules above).

---

## Execution model

Aligned with `e0010_first_ensemble` / `backtest.py`:

| Concept | Definition |
| ------- | ---------- |
| Decision time | End of bar `t`, using data through `Close(t)` |
| Held position | `position[t] = signal[t - 1]` for `t > 0`; `position[0] = 0` |
| Bar return | `bar_ret[t] = Open(t+1) / Open(t) - 1` |
| Gross return | `position[t] * bar_ret[t]` |
| Turnover | `abs(position[t] - position[t - 1])` |
| Net return | `gross - turnover * cost_per_turnover` |

Additional rules:

- The **last bar** contributes no return (no `Open(t+1)`), so the return series
  has length `n_bars - 1`.
- **`cost_per_turnover = 0.0`** for the reference benchmark.
- Positions are **fully invested** at `+1` or `-1` while open; otherwise `0`.

This model is **look-ahead free**: the signal computed at `t` affects PnL no
earlier than the open of bar `t + 1`.

---

## Performance metrics

Computed on the net per-bar return stream. Let `n` be the number of return bars.

**Annualization:** infer bar spacing as the **median** of positive consecutive
timestamp deltas (seconds), then:

```
periods_per_year = 365.25 * 24 * 3600 / bar_spacing_secs
```

| Metric | Formula |
| ------ | ------- |
| `total_return` | `prod(1 + r_i) - 1` |
| `ann_return` | `expm1( log1p(r_i).sum() * periods_per_year / n )` (clamp exp arg ≤ 700) |
| `ann_vol` | `std(r, ddof=0) * sqrt(periods_per_year)` |
| `sharpe` | `mean(r) / std(r, ddof=0) * sqrt(periods_per_year)` (0 if std = 0) |
| `max_drawdown` | min of `equity / cummax(equity) - 1` |
| `hit_rate` | fraction of bars with `position != 0` and `r > 0` (NaN if never active) |
| `ann_turnover` | `sum(turnover) * periods_per_year / n` |
| `n_bars` | `n` (return bars, not input bars) |

---

## Reference output

Produced by `cargo run --release --bin benchmark-sma-crossover` on the full EURUSD
continuous stream with default parameters. Timings are machine-dependent; **metrics
must match** within reasonable float tolerance (~1e-4 relative).

```
strategy=DualSmaCrossover fast=50 slow=200 hold_bars=60
bars=8490235
total_return=-0.146512
ann_return=-0.009766
ann_vol=0.066019
sharpe=-0.1156
max_drawdown=-0.324686
hit_rate=0.4674
ann_turnover=5369.1045
n_bars=8490234
```

The strategy is a **correctness fixture**, not a profitable hypothesis.

---

## Parity checklist

When porting the backtester, verify each item independently:

- [ ] Bar count after load equals **8,490,235** (with current corpus).
- [ ] Return count equals **8,490,234** (`bars - 1`).
- [ ] Every non-zero signal run has length exactly **60** (`hold_bars`).
- [ ] While flat, only **crossover bars** open a new trade.
- [ ] Crossovers during an open trade are **ignored**.
- [ ] First return bar uses **position = 0** regardless of `signal[0]`.
- [ ] `total_return` matches reference within **1e-4**.
- [ ] `sharpe` matches reference within **1e-3**.
- [ ] `max_drawdown` matches reference within **1e-4**.
- [ ] Unit test: flat price → all signals `0`.
- [ ] Unit test: flat signal → all returns ≈ 0.

---

## Minimal pseudocode

```
bars = load_continuous("EURUSD")
closes = [b.close for b in bars]

fast = sma(closes, 50)
slow = sma(closes, 200)

signal = []
position = 0
bars_left = 0

for t in 0 .. len(bars)-1:
    if bars_left > 0:
        if bars_left == 1:
            position = 0
            bars_left = 0
        else:
            bars_left -= 1
    elif hold_bars > 0 and t > 0:
        if bull_cross(fast, slow, t):
            position = +1
            bars_left = hold_bars
        elif bear_cross(fast, slow, t):
            position = -1
            bars_left = hold_bars
    signal.append(position)

result = backtest(bars, signal, cost_per_turnover=0.0)
```

---

## Related documents

- Experiment overview: [`README.md`](./README.md)
- e0010 execution convention: [`../e0010_first_ensemble/backtest.py`](../e0010_first_ensemble/backtest.py)
- Root data format: [`../../AGENTS.md`](../../AGENTS.md)
