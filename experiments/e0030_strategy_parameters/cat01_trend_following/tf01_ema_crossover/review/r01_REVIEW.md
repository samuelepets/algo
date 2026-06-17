# REVIEW — TF01 EMA Crossover

Date: 2026-06-17
Scope reviewed:
- `src/main.rs`
- `src/backtest.rs`
- `src/data.rs`
- `src/indicators.rs`
- `README.md`
- `RESULTS.md`
- `PERFORMANCE.md`

Runtime validation performed:
- `cargo test` (5/5 passing)
- `cargo run --release` (reproduced documented outputs)
- Sanity check on `outputs/results.csv` with Python

---

## Findings

### 1) Critical — Max drawdown metric is conceptually and mathematically broken

**Where**
- `src/backtest.rs` (`compute_metrics`, drawdown section)

**What happens**
- Drawdown is computed as `(peak - cum_r) / peak` only when `peak > 0`, else `0`.
- This causes two invalid behaviors:
  1. Strategies that never make a new equity high report `max_drawdown = 0` even with catastrophic losses.
  2. Drawdown can explode to very large numbers when `peak` is small positive and equity later goes deeply negative.

**Evidence**
- From current run (`outputs/results.csv`):
  - `max_drawdown` range: `0.0` to `2,927,359.972354`
  - `1344` parameter sets have `max_drawdown == 0.0` while `total_return < 0`

**Why this is a problem**
- Reported risk is unreliable and can invert reality (worst systems can appear to have zero drawdown).
- Any ranking/filtering using this metric is invalid.
- Documentation currently states contradictory semantics (normalized vs R-based).

**Recommended fix**
- Track drawdown in equity units (`R`) or percent, but consistently:
  - If using absolute drawdown in `R`: `dd_r = peak - cum_r` (no division).
  - If using percentage drawdown: define proper equity baseline and avoid divide-by-near-zero artifacts.
- Update docs and output column names accordingly (e.g., `max_drawdown_r`).

---

### 2) High — Walk-forward implementation has data leakage (not true walk-forward optimization)

**Where**
- `src/main.rs` (selection of `best_params` before walk-forward block)

**What happens**
- The code picks `best_params` from the full 2003–2025 sample, then evaluates that same parameter set on each IS/OOS window.
- This is not a proper walk-forward optimization protocol.

**Why this is a problem**
- OOS results are contaminated by future information because parameter selection already saw all years.
- Conclusions about robustness/generalization are overstated.

**Recommended fix**
- For each window:
  1. Re-run grid search on IS only.
  2. Select best params from IS.
  3. Evaluate selected params on OOS.
  4. Log selected params per window.

---

### 3) High — Strategy description says trailing stop, implementation uses fixed stop

**Where**
- `README.md` (strategy summary: “ATR-based trailing stop”)
- `src/backtest.rs` (entry sets `stop`; stop is never updated afterward)

**What happens**
- Current engine uses a fixed ATR stop set at entry, plus target and opposite-crossover exit.
- No trailing mechanism is implemented.

**Why this is a problem**
- Documentation and code behavior diverge.
- Research conclusions may be misinterpreted as “trailing-stop EMA crossover failed,” when that variant was never tested.

**Recommended fix**
- Either:
  - Implement trailing stop logic (e.g., long: `stop = max(stop, close - atr_mult * ATR)`; short symmetric), or
  - Update docs/results text to explicitly say “fixed ATR stop.”

---

### 4) Medium — Drawdown semantics are inconsistent across code and reports

**Where**
- `src/backtest.rs` comment: “normalised to [0,1]”
- `RESULTS.md` / `PERFORMANCE.md`: labels like “Max Drawdown (R)” and values > 1 (sometimes huge)

**What happens**
- Metric naming/units are not aligned with implementation or observed values.

**Why this is a problem**
- Makes cross-strategy comparison unreliable.
- Readers cannot interpret risk numbers consistently.

**Recommended fix**
- Standardize one definition and unit across:
  - metric computation,
  - CSV headers,
  - `README.md`, `RESULTS.md`, `PERFORMANCE.md`.

---

### 5) Medium — Timezone treatment can shift window slicing boundaries

**Where**
- `src/data.rs`:
  - Input timestamps are labeled EET.
  - Parsed as naive datetime then converted “as-if UTC”.
  - Window boundaries are generated in UTC (`year_start_ts`).

**What happens**
- Bars are treated as UTC timestamps even though source data is EET.
- Window slicing can be shifted by timezone offset around boundaries.

**Why this is a problem**
- Not catastrophic for long windows, but conceptually incorrect and can move bars across IS/OOS edges.

**Recommended fix**
- Normalize to a single explicit timezone policy:
  - either store source timestamps in EET-consistent epoch,
  - or convert correctly to UTC with known offset rules.
- Document chosen policy and boundary semantics.

---

## Positive notes

- Core indicator calculations (`EMA`, `ATR`) are clean and have unit tests.
- Resampling logic is straightforward and deterministic.
- Backtest runtime is efficient (parallel grid with cached indicators).
- Results are reproducible (`cargo run --release` matched documented values).

---

## Priority order to address

1. Fix drawdown metric definition and implementation.
2. Correct walk-forward protocol (IS optimization per window).
3. Align strategy spec with implementation (trailing vs fixed stop).
4. Unify metric naming/units in all reports.
5. Clarify/fix timestamp timezone handling.

---

## Suggested acceptance checks after fixes

- No configuration with `total_return < 0` should have `max_drawdown == 0`.
- Drawdown values should stay within expected range for chosen definition.
- Walk-forward output should include per-window selected parameters.
- Docs (`README.md`, `RESULTS.md`, `PERFORMANCE.md`) should exactly match implemented exits and metric units.
