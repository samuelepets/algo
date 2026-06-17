# RESPONSE — TF01 EMA Crossover (response to `r03_REVIEW.md`)

Date: 2026-06-17
Role: Programmer response to the reviewer's verification report.

The reviewer confirmed all five `r01_REVIEW.md` findings as **Fixed** and left a
single **Low** documentation item. This response addresses it.

---

## Low — Stale runtime note in `README.md` — **Fixed**

**What was wrong:** `README.md` still advertised a typical runtime of
`~8.5 seconds`, which predates the walk-forward refactor. The honest
walk-forward now re-optimises the full grid on each of the 4 IS windows
(in addition to the full-sample grid), so end-to-end runtime is higher
(`Total elapsed: 13.3s` in the last `cargo run --release`).

**Change made:** updated the runtime note to a realistic range with a breakdown
and an explicit caveat that timing depends on CPU and caching:

> Typical runtime: **~12–15 seconds** end-to-end on a modern multi-core CPU
> (~3.5 s data load + full-sample grid of 3,150 combinations + per-window
> IS-only re-optimisation for the 4 walk-forward windows, all rayon-parallel).
> Exact timing depends on CPU core count and filesystem/page caching.

**Also updated for consistency** (same stale fact on other surfaces; finding #4
of `r01` asked for cross-surface consistency):
- `RESULTS.md` identity line: `≈ 8.5 s` → `≈ 12–15 s end-to-end`.
- `ROADMAP.md` Phase 5: replaced `total 8.4s` with current grid-search timing
  (~3 s) plus the ~12–15 s end-to-end figure.

**Files changed:** `README.md`, `RESULTS.md`, `ROADMAP.md`.

**Behavioral impact:** documentation only; no code or results change.

**Validation:** `cargo build --release` (zero warnings), `cargo test --release`
(5/5). Runtime figure cross-checked against the prior `cargo run --release`
("Total elapsed: 13.3s"), which falls inside the documented 12–15 s range.

---

## Status summary

| # | Severity | Finding | Status |
|---|---|---|---|
| r03 Low | Low | Stale `~8.5 s` runtime note | **Fixed** |

No `Critical`/`High` findings remain open across the cycle. With this `Low` item
resolved, the acceptance/stop condition from `review/README.md` is met:
- No open `Critical`/`High` findings.
- Acceptance checks from `r01_REVIEW.md` passing (re-verified in `r03`).

## Remaining risks / open questions

- None for this review cycle. Out-of-scope items noted in `r02_RESPONSE.md`
  (trade-frequency Sharpe scaling; IS selection criterion) remain as future
  considerations, not blockers.
