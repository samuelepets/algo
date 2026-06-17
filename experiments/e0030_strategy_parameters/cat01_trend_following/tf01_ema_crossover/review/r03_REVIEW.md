# REVIEW — TF01 EMA Crossover (verification of `r02_RESPONSE.md`)

Date: 2026-06-17
Reviewer: Validation of programmer response against `r01_REVIEW.md`.

Scope validated:
- `review/r02_RESPONSE.md`
- `src/backtest.rs`
- `src/main.rs`
- `src/data.rs`
- `README.md`
- `RESULTS.md`
- `PERFORMANCE.md`
- `ROADMAP.md`

Runtime validation executed:
- `cargo test --release` (5/5 passing)
- `cargo run --release` (full grid + walk-forward rerun)
- Python sanity check on regenerated `outputs/results.csv`

---

## Findings (ordered by severity)

### Low — Runtime note in README is stale after walk-forward refactor

**What is wrong**
- `README.md` still states a typical runtime of `~8.5 seconds`, but current full execution is now around `~13s` due to per-window IS-only re-optimisation.

**Where**
- `README.md` (`Typical runtime` line).

**Why it matters**
- This can mislead future reviewers/users about expected execution cost and may cause confusion when validating performance regressions.

**Expected correction criteria**
- Update the runtime note to reflect current end-to-end behavior (for example, a realistic range and a short note that exact timing depends on CPU and caching).

---

## Status of `r01_REVIEW.md` requests

### 1) Critical — Max drawdown metric broken
**Status: Fixed**

Validated in code and outputs:
- `src/backtest.rs` now computes drawdown as absolute `R` (`peak - cum_r`) and stores it as `max_drawdown_r`.
- Regenerated `outputs/results.csv` satisfies acceptance checks:
  - `total_return < 0 && max_drawdown_r == 0` -> `0` configs.
  - Negative drawdowns -> `0`.
  - Range observed: `388.706679` to `75780.001589`.

### 2) High — Walk-forward data leakage
**Status: Fixed**

Validated in code and outputs:
- `src/main.rs` now re-optimises the full grid on each IS window and evaluates selected params on OOS (`search_range` + `eval_params` flow).
- `outputs/walkforward.csv` includes per-window selected parameter columns (`sel_fast`, `sel_slow`, `sel_atr_mult`, `sel_rr`, `sel_tf`).
- Current run shows all OOS windows negative (consistent with non-leaky protocol).

### 3) High — Trailing stop in docs vs fixed stop in implementation
**Status: Fixed (documentation aligned)**

Validated in docs/code consistency:
- `README.md` now explicitly states fixed ATR stop (static after entry), fixed target, and opposite-crossover exit.
- `src/backtest.rs` behavior remains fixed-stop, matching documentation.

### 4) Medium — Drawdown semantics inconsistent across surfaces
**Status: Fixed**

Validated in naming/units:
- `max_drawdown_r` naming is consistently used in `src/backtest.rs`, `src/main.rs` outputs, and reports (`README.md`, `RESULTS.md`, `PERFORMANCE.md`, `ROADMAP.md`).
- Tables and prose now describe drawdown as absolute `R` units.

### 5) Medium — Timezone/window-boundary policy unclear
**Status: Fixed (policy clarified and documented)**

Validated in documentation:
- `src/data.rs` now contains an explicit timestamp policy and boundary semantics.
- `year_start_ts` comment clarifies it uses the same convention as `Bar::ts`, eliminating ambiguity in IS/OOS slicing interpretation.

---

## Review conclusion

- No open `Critical` or `High` findings remain from `r01_REVIEW.md`.
- One `Low` documentation item remains (runtime note drift in `README.md`).
- After fixing that low item, this review cycle can be considered complete from a correctness/traceability perspective.
