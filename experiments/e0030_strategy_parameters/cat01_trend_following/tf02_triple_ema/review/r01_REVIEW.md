# REVIEW — TF-02 Triple EMA Alignment

Date: 2026-06-18
Scope reviewed:
- `backtest.py`
- `data.py`
- `indicators.py`
- `main.py`
- `tests/test_backtest.py`
- `tests/test_data.py`
- `README.md`
- `RESULTS.md`
- `PERFORMANCE.md`
- `ROADMAP.md`

Runtime validation performed:
- `uv run pytest` (11/11 passing, reviewed output)
- `uv run ruff check` (clean)
- Manual trace of `backtest_core` entry/exit logic against crafted bar sequences
- Cross-check of walk-forward window boundary timestamps against `RESULTS.md`

---

## Findings

### 1) High — Alignment-break exit condition is too permissive

**Where**
- `backtest.py:146` (long) and `backtest.py:154` (short)

**What happens**
- A long trade exits on alignment break when `fast_now < slow_now`.
- The entry condition requires full triple alignment: `fast > mid > slow` with all
  three slopes positive.
- The exit only fires when `fast` crosses below `slow`, ignoring intermediate
  breakdown states where `fast < mid` but `fast > slow`. In that intermediate
  regime the alignment condition that justified the entry is already violated, but
  the exit does not fire.

**Why this matters**
- Positions can be held through partial alignment breakdowns, accumulating losses
  before the looser `fast < slow` crossing occurs.
- The real edge of the strategy — if any — comes from requiring strict triple
  alignment at all times; holding through partial breakdowns inflates drawdown
  and understates strategy frequency simultaneously.
- The discrepancy is silent: the test suite passes and the documentation does not
  flag this asymmetry between the entry filter and the exit trigger.

**Recommended fix**
- Change the long break condition to the full inverse of the bullish alignment
  check:
  ```python
  align_broken = not (fast_now > mid_now and mid_now > slow_now
                      and fast_now > fast_prev and mid_now > mid_prev
                      and slow_now > slow_prev)
  ```
  Or, if a slope-agnostic structural break is preferred:
  ```python
  align_broken = not (fast_now > mid_now and mid_now > slow_now)
  ```
  Either is tighter than the current `fast_now < slow_now`. Document the chosen
  definition in `README.md § Implementation Semantics`.

**Acceptance check**
- After fix, a scenario where `fast` crosses below `mid` (but stays above `slow`)
  should trigger an exit. Add a test for this exact path.

---

### 2) Medium — Entry-bar stop violation is not caught

**Where**
- `backtest.py:120–209` (main loop structure)

**What happens**
- The loop evaluates exit conditions first (`if in_pos`) and entry conditions
  second (`if not in_pos and not just_exited`). On the bar where an entry fires,
  no exit check runs for that bar.
- A pullback-entry bar can have `low[i] <= pb_ema[i]` (pullback condition) and
  `close[i] > pb_ema[i]` (rejection confirmation) while simultaneously having
  `low[i] <= entry - atr_mult * ATR` (stop already breached). In that case:
  - The entry is accepted at `close[i]`.
  - The stop is checked starting only from bar `i+1`.
  - The trade is entered even though in live trading the stop order would have
    filled before entry could be taken.

**Concrete scenario**
- `pb_ema = 1.0800`, `close[i] = 1.0820`, `low[i] = 1.0750`, `ATR = 0.006`,
  `atr_mult = 1.0` → `stop = 1.0760`. `low[i] = 1.0750 < 1.0760 = stop`. The
  bar's low already breached the stop, but the trade is entered.

**Why this matters**
- Creates ghost trades with a risk distance that was already violated on the
  signal bar. This biases performance slightly upward (entries survive an
  intrabar adverse move that would invalidate them live).
- Since all 720 combinations are net-negative, the research conclusion does not
  change, but the distortion should be corrected for future reuse of the engine.

**Recommended fix**
- Before opening a long position, guard with:
  ```python
  if low[i] > entry - dist:  # stop not breached on entry bar
      in_pos = True
  ```
  Symmetric check for short entries (`high[i] < entry + dist`).

**Acceptance check**
- Add a test where `low[i] <= entry - atr_mult * ATR` on the signal bar:
  no trade should be opened.

---

### 3) Medium — Single-trade results are silently zeroed

**Where**
- `backtest.py:28–29` (`_compute_metrics`)

**What happens**
- When `n_trades < 2`, the function returns `(0.0, 0.0, 0.0, 0.0, n_trades)`.
- A parameter combination that generates exactly one trade across a walk-forward
  OOS window reports `sharpe=0.0` and `total_return=0.0`, indistinguishable from
  a combination that generated no trades at all (except via `n_trades`).

**Why this matters**
- `outputs/walkforward.csv` can contain OOS rows with one trade; those rows show
  zero Sharpe and zero return, which a reader could mistake for neutral performance
  rather than censored data.
- The min-trades filter (`MIN_TRADES = 50`) screens these out of `top_params.json`
  but not out of `walkforward.csv`.

**Recommended fix**
- Option A: Compute metrics normally for `n_trades >= 1` (std is undefined for 1
  trade → Sharpe stays 0 per population variance, but return and max_dd are valid).
- Option B: Return a sentinel value (e.g., `sharpe = np.nan`) for `n_trades < 2`
  so downstream consumers can distinguish "no trades" from "bad trades".
- Update the CSV header comment or add a `RESULTS.md` footnote to document the
  censoring.

**Acceptance check**
- A backtest producing exactly one losing trade should have `total_return < 0`
  and `max_drawdown_r > 0` in the returned tuple, not zeros.

---

### 4) Medium — Test coverage gaps in backtest engine

**Where**
- `tests/test_backtest.py` (4 tests, all long-only or no-trade scenarios)

**What happens**
- The existing tests cover: no trades on flat bars, tiny input, one long stop exit,
  and no trades when alignment is wrong. The following paths have no test:

  | Path | Risk |
  |---|---|
  | Short (bearish) entry and exit | Asymmetric bugs in `bear_align` branch |
  | Target (2:1) exit | Target exit arithmetic `(target - entry - SPREAD) / risk_r` is untested |
  | Alignment-break exit | The third exit branch is never triggered in any test |
  | Two-trade sequence | `_compute_metrics` is exercised only for 0 or 1 trade; Sharpe and return formulas are not validated against known values |
  | Entry-bar stop guard (once fixed) | Ensures fix from finding 2 is permanent |

- `test_long_entry_and_stop_exit_with_crafted_signals` asserts `n_trades == 1`
  and then asserts `sharpe == 0.0` and `ret == 0.0` as proof-of-stop, but those
  zeros come from the `n_trades < 2` censoring (finding 3), not from actual
  metric computation. The test does not verify the stop exit R-value.

**Why this matters**
- The short path (`bear_align` branch in `backtest_core:199–209`) and the
  alignment-break exit (`backtest_core:151–152`, `159–160`) are production code
  paths exercised on every real run but never regression-tested. Any future
  refactoring could silently break them.

**Recommended fix**
- Add at minimum:
  1. `test_short_entry_and_target_exit` — bearish alignment, bar touches pb_ema
     from below, rejected downward; next bar hits target; verify `n_trades == 1`.
  2. `test_long_alignment_break_exit` — bullish alignment established, then
     `fast_now < slow_now` forced; verify trade closes via alignment break.
  3. `test_metrics_two_trades` — craft two trades with known R outcomes (+2, −1);
     verify Sharpe, profit_factor, and total_return against hand-computed values.

**Acceptance check**
- `uv run pytest` passes with the new tests included.

---

### 5) Low — Full-history grid search uses undocumented sentinel timestamps

**Where**
- `main.py:300`

**What happens**
```python
results = _run_search(tf, -(2**62), 2**62)
```
- The sentinel values `-(2**62)` and `2**62` are magic numbers relied upon to
  exceed any real epoch-second timestamp in the dataset.
- `ts_range` uses `np.searchsorted` which returns `0` and `n` respectively,
  so the behavior is correct, but the intent is not visible to a reader.

**Why this matters**
- If `ts` dtype ever changes (e.g., nanoseconds instead of seconds), the
  sentinels could overflow or become reachable, silently slicing a subset of
  bars. No test or assertion guards against this.

**Recommended fix**
```python
ALL_BARS_START = -(2**62)
ALL_BARS_END   =   2**62
...
results = _run_search(tf, ALL_BARS_START, ALL_BARS_END)
```
Or, more robustly, add a `full_range` helper to `data.py`:
```python
def full_ts_range(ts: np.ndarray) -> tuple[int, int]:
    return ts[0], ts[-1] + 1
```

**Acceptance check**
- The sentinel or helper is documented in `data.py` or `main.py` with a brief
  comment explaining the convention.

---

### 6) Low — Test name misrepresents the exercised condition

**Where**
- `tests/test_backtest.py:85` (`test_no_long_trades_without_bullish_alignment`)

**What happens**
- The test builds EMAs with `fast = linspace(1.12 → 1.00)`, `mid = linspace(1.10 → 0.98)`,
  `slow = linspace(1.08 → 0.96)`. This gives `fast > mid > slow` (correct bullish
  ordering) but all slopes are negative (descending). Bullish alignment fails
  because the slope condition (`fast_now > fast_prev`) is false.
- The test name says "without bullish alignment" but the actual condition exercised
  is "bullish ordering with negative slopes," not the more obvious case of
  inverted ordering. Bearish alignment (`fast < mid < slow`, all descending) is
  also absent here, so the test does not cover no-short-trades either.

**Why this matters**
- A future reader implementing a different slope condition might change the test
  setup without realizing that the slope direction is the operative variable.
- The test would pass for any engine that checks slopes, but pass for the wrong
  reason for an engine that only checks ordering.

**Recommended fix**
- Rename to `test_no_trades_when_emas_descending_despite_correct_ordering` and
  add a docstring:
  ```python
  """Slopes are negative (all EMAs declining) so alignment is never confirmed
  even though the ordering fast > mid > slow holds throughout."""
  ```

**Acceptance check**
- Docstring added; no behavioral change required; `uv run pytest` still passes.

---

## Positive notes

- **Drawdown metric is correct**: absolute peak-to-trough in R with `peak`
  initialized to 0 — strategies that never go positive still accumulate correct
  drawdown (`dd = 0 - cum_r` when `cum_r < 0`). This was the critical bug in
  TF-01 Rust and is resolved here.
- **Walk-forward IS-only re-optimization is correct**: each window re-runs the
  full grid on the IS slice before selecting params. No full-history leakage
  (contrast with TF-01 Rust `r01` finding 2).
- **EMA cache deduplication**: `build_ema_cache` deduplicates periods, ensuring
  that overlapping grids (e.g., `slow_ema=34` shared across multiple triples) do
  not recompute the same EMA.
- **Spread applied symmetrically**: round-trip cost `SPREAD` is deducted from
  all exit R-values for both long and short, including alignment-break exits.
- **Resample and data tests**: `test_resample_5min_two_buckets` and
  `test_resample_empty` confirm boundary behavior of the Numba resampling kernel.
- **RESULTS.md is well-structured**: the standardised card format, the
  explicit implementation-semantics table, and the cross-strategy comparison to
  TF-01 make the research conclusions auditable without re-running the experiment.

---

## Priority order to address

1. Tighten alignment-break exit to match entry condition (finding 1).
2. Guard entry-bar stop violation (finding 2).
3. Fix or document single-trade metric censoring (finding 3).
4. Add missing test paths for short, target, alignment-break, and multi-trade metrics (finding 4).
5. Replace sentinel timestamps with named constants or helper (finding 5).
6. Rename and document ambiguous test (finding 6).

---

## Suggested acceptance checks after fixes

- A scenario where `fast` falls below `mid` (but stays above `slow`) must
  trigger a long exit.
- A signal bar whose `low <= entry - stop_distance` must produce zero new trades.
- A single-trade run must return non-zero `total_return` and `max_drawdown_r`.
- `uv run pytest` passes with new short-path, target-exit, alignment-break-exit,
  and two-trade metric tests.
- `uv run ruff check` clean after renaming and adding docstrings.
- Full `uv run python main.py` output is numerically unchanged (findings 5 and 6
  are non-behavioral).
