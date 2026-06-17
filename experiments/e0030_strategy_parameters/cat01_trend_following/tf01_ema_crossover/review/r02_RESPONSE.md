# FIXES — TF01 EMA Crossover (response to `r01_REVIEW.md`)

Date: 2026-06-17
Role: Programmer response to reviewer findings.

Validation run after all changes:
- `cargo build --release` — compiles, **zero warnings**.
- `cargo test --release` — **5/5 passing**.
- `cargo run --release` — full grid + walk-forward re-run (13.3 s), all
  `outputs/*` regenerated.
- Python sanity check on the regenerated `outputs/results.csv` (acceptance
  checks below).

Summary of status:

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | Critical | Max drawdown metric broken | **Fixed** |
| 2 | High | Walk-forward data leakage | **Fixed** |
| 3 | High | Docs say trailing stop, code is fixed stop | **Fixed** (docs aligned) |
| 4 | Medium | Drawdown semantics inconsistent | **Fixed** |
| 5 | Medium | Timezone shifts window boundaries | **Fixed** (clarified; no real drift) |

---

## 1) Critical — Max drawdown metric — **Fixed**

**What was wrong:** drawdown was computed as `(peak - cum_r) / peak` guarded by
`peak > 0` (else `0`). This made monotonic losers (which never set a positive
peak) report `max_drawdown == 0`, and produced explosive values when `peak` was
a small positive number.

**Change made:** drawdown is now tracked in **absolute R units** with no
division. The equity curve and the running peak both start at `0` R (the
initial baseline), so a strategy that never recovers above its start keeps its
peak pinned at 0 and its drawdown equals its deepest cumulative loss:

```rust
let mut cum_r  = 0.0;
let mut peak   = 0.0;
let mut max_dd = 0.0;
for &r in trades {
    cum_r += r;
    if cum_r > peak { peak = cum_r; }
    let dd = peak - cum_r;     // always ≥ 0, no divide-by-near-zero
    if dd > max_dd { max_dd = dd; }
}
```

**Files changed:** `src/backtest.rs` (`Metrics` field renamed
`max_drawdown` → `max_drawdown_r`, doc comment, `compute_metrics`).

**Behavioral impact:** drawdown is now always ≥ 0 and monotonically meaningful.
The two worst-5 rows that previously printed `0` (e.g. `3/25/0.5/1.0/5m` with
−65,214 R total) now correctly report ~65,216 R drawdown.

**Acceptance checks (regenerated `results.csv`, 3,150 rows):**
- Configurations with `total_return < 0` **and** `max_drawdown_r == 0`:
  **0** (was 1,344).
- Negative drawdown values: **0**.
- `max_drawdown_r` range: **388.7 → 75,780.0 R** (no zeros, no explosions to
  the old 2.9 M artifact).

---

## 2) High — Walk-forward data leakage — **Fixed**

**What was wrong:** `best_params` was selected from the full 2003–2025 sample
and then evaluated on every IS/OOS window — the parameter choice had already
seen all OOS years.

**Change made:** implemented a proper walk-forward protocol in `src/main.rs`.
For each window:
1. The **full grid is re-optimised on the IS slice only** (`search_range`
   over the IS time range, both timeframes).
2. The best IS set (max Sharpe, ≥ `MIN_TRADES`) is selected.
3. That exact set is evaluated, unchanged, on the OOS slice (`eval_params`).
4. The selected parameters are **logged per window** in
   `outputs/walkforward.csv` (new columns `sel_fast, sel_slow, sel_atr_mult,
   sel_rr, sel_tf`).

To support this efficiently, per-timeframe resampled bars + cached indicators
are built once into a `TfData` struct and reused by both the full-sample search
and each window's IS/OOS slicing (indicators are computed on the full series
and index-sliced; OOS indicators therefore warm up from past IS data only —
no look-ahead).

**Files changed:** `src/main.rs` (new `TfData`, `build_grid`, `search_range`,
`eval_params`; walk-forward block rewritten; removed the old `slice_window`).

**Behavioral impact (important):** under honest selection, **all 4 OOS windows
are now negative** (−0.202, −0.700, −1.799, −1.730). The previously reported
**+0.092** on Window 1 (2015–2018) was a selection-leak artifact: when the IS
optimum for that window (`13/50, 2.5×, rr2.5`) is chosen honestly, its OOS
Sharpe is **−0.202**. This strengthens the "no edge" conclusion rather than
weakening it.

---

## 3) High — Trailing stop vs fixed stop — **Fixed (documentation aligned)**

**What was wrong:** `README.md` described an "ATR-based trailing stop", but the
engine sets the stop once at entry and never moves it.

**Decision & rationale:** I aligned the **docs to the implementation** (fixed
ATR stop) rather than implementing trailing logic. Reasons:
- The entire result set, the `strategies/01_TREND_FOLLOWING.md § TF-01`
  reference and this experiment's conclusions were all produced with a fixed
  ATR stop; changing the exit rule would invalidate every number here and
  conflate two distinct strategy variants.
- A trailing-stop EMA crossover is a genuinely different system and belongs in
  its own experiment, so the negative result here is not mislabeled as
  "trailing-stop crossover failed".

**Change made:** `README.md` strategy summary now states explicitly that exits
are a **fixed ATR stop** (set at entry, never moved), a fixed R:R target, or an
opposite EMA crossover, and notes that a trailing variant is left for a future
experiment.

**Files changed:** `README.md`.

---

## 4) Medium — Drawdown semantics inconsistent — **Fixed**

**What was wrong:** the code comment said "normalised to [0,1]" while reports
labeled values "Max Drawdown (R)" and showed numbers far above 1.

**Change made:** standardised on a single definition and unit — **absolute R
peak-to-trough** — across every surface:
- `src/backtest.rs`: field `max_drawdown_r` + clarified doc comment.
- `src/main.rs`: CSV header `max_drawdown` → `max_drawdown_r`; JSON key
  `max_drawdown_r`; stdout column `max_dd_r`; walk-forward column
  `oos_max_drawdown_r`.
- `README.md`, `RESULTS.md`, `PERFORMANCE.md`, `ROADMAP.md`: column headers,
  metric labels and the distribution/top-20/worst-5/walk-forward tables all
  regenerated with absolute-R values and an explicit definition note.

**Files changed:** `src/backtest.rs`, `src/main.rs`, `README.md`, `RESULTS.md`,
`PERFORMANCE.md`, `ROADMAP.md`.

---

## 5) Medium — Timezone treatment / window boundaries — **Fixed (clarified; no real drift)**

**Reviewer concern:** bars are parsed from EET labels but stored as-if UTC,
while window boundaries are generated "in UTC", potentially shifting bars
across IS/OOS edges.

**Analysis:** there is in fact **no boundary drift**, because both sides use the
*same* convention. `Bar::ts` is `NaiveDateTime(EET label).and_utc().timestamp()`
and `year_start_ts(y)` is `NaiveDate(y,1,1).and_utc().timestamp()` — i.e. the
boundary is built with the identical naive→UTC interpretation. A bar labeled
`2015.01.01 00:00:00` maps to exactly the same epoch as the `2015` boundary, so
IS/OOS splits land precisely on the calendar boundary the data labels imply.
The only consequence of skipping the real EET↔UTC offset is a constant shift in
absolute epoch values vs true UTC, which is irrelevant for sorting, resampling
and year-aligned slicing (all relative operations).

**Decision & rationale:** rather than introduce real EET↔UTC + DST conversion
(which would re-bucket every bar and change all results for no analytical
benefit on year-aligned windows), I made the policy **explicit and documented**,
which is what the finding's correction criterion asks for ("document chosen
policy and boundary semantics").

**Change made:** added a "Timezone / timestamp policy" doc block to
`Bar` in `src/data.rs` and a clarifying comment on `year_start_ts`, stating that
both use one consistent exchange clock and therefore align at boundaries.

**Files changed:** `src/data.rs`.

---

## Acceptance checks from the review

| Check | Result |
|---|---|
| No `total_return < 0` config with `max_drawdown == 0` | ✅ 0 such configs (was 1,344) |
| Drawdown values within expected range for the definition | ✅ all ≥ 0, 388.7–75,780 R, ≈ cumulative loss for monotonic losers |
| Walk-forward output includes per-window selected params | ✅ `sel_*` columns in `walkforward.csv` |
| Docs match implemented exits and metric units | ✅ fixed ATR stop + absolute-R drawdown across README/RESULTS/PERFORMANCE/ROADMAP |

## Remaining risks / open questions

- The core conclusion is **unchanged and slightly stronger**: 0/3,150
  combinations are profitable, and all 4 honest OOS windows are negative.
- Annualised Sharpe uses a trade-frequency scaling that is fine for ranking but
  is not a calendar-return Sharpe; out of scope for this review but worth noting
  for cross-strategy comparisons.
- Walk-forward still selects purely by IS Sharpe; alternative selection
  criteria (e.g. PF, or robustness across neighbors) were not explored — also
  out of scope here.
