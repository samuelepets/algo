# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, Copilot, and other LLM tools)
working in this repository. Written to follow the cross-tool
[AGENTS.md](https://agents.md) convention so it works regardless of the model.

## Project overview

`algo` is a repository for **algorithmic trading research and backtesting**.
It contains a historical market-data corpus plus isolated experiments under
`experiments/`. New code (data loaders, indicators, strategies, backtesters,
etc.) is added on top of the dataset, one self-contained experiment at a time.

- **License:** GNU GPL v2 (see `LICENSE`). Keep any new source files compatible
  with GPL-2.0.
- **Default branch:** `main`.

## Author preferences

- **Always generate content in English.** All committed artifacts — code,
  comments, identifiers, documentation, commit messages, and any generated files
  — must be written in English, regardless of the language used in the chat
  conversation.

## Repository layout

```
.
├── LICENSE              # GPL-2.0
├── README.md           # placeholder
├── AGENTS.md           # this file (canonical agent guidance)
├── CLAUDE.md           # imports AGENTS.md for Claude Code
├── .vscode/            # editor color customizations only
├── experiments/        # isolated trading-strategy research (see below)
│   └── <name>/         # one self-contained experiment per directory
└── data/
    └── bars/
        └── <SYMBOL>/<SYMBOL>_<YEAR>.csv.gz
```

> Note: `data/` (~445 MB) **is tracked by git** and committed to the repository
> as the canonical dataset. Files are pre-gzipped and each is well under
> GitHub's 100 MB per-file limit (largest ≈ 8 MB), so plain git is used (no LFS).
> Treat the corpus as **read-only input**: do not modify, rewrite, or delete
> these files. Do not commit *generated* artifacts (backtest outputs, caches,
> etc.) — add a `.gitignore` entry for those instead.

## Market data

The dataset is **1-minute OHLCV bars**, one gzipped CSV per symbol per year.

- **Path pattern:** `data/bars/<SYMBOL>/<SYMBOL>_<YEAR>.csv.gz`
- **Format:** UTF-8, **semicolon-delimited** (`;`), one header row.
- **Header:** `Time (EET);Open;High;Low;Close;Volume`
- **Timestamps:** `YYYY.MM.DD HH:MM:SS`, in **EET** (Eastern European Time).
- **Granularity:** 1 minute. Volume may be `0` for some instruments/periods.

Example (`data/bars/EURUSD/EURUSD_2024.csv.gz`):

```
Time (EET);Open;High;Low;Close;Volume
2024.01.02 00:00:00;1.10481;1.10481;1.10476;1.1048;5.9
2024.01.02 00:01:00;1.10477;1.10479;1.10477;1.10479;26.1
```

### Available symbols

| Symbol  | Asset class | Description       | Years covered |
| ------- | ----------- | ----------------- | ------------- |
| EURUSD  | Forex       | Euro / US Dollar  | 2003–2025     |
| XAUUSD  | Metals      | Gold / USD        | 2003–2025     |
| XAGUSD  | Metals      | Silver / USD      | 2003–2025     |
| BTCUSD  | Crypto      | Bitcoin           | 2020–2025     |
| ETHUSD  | Crypto      | Ethereum          | 2020–2025     |
| BATUSD  | Crypto      | Basic Attention   | 2020–2025     |
| ADAUSD  | Crypto      | Cardano           | 2021–2025     |
| AVEUSD  | Crypto      | Aave              | 2021–2025     |
| CMPUSD  | Crypto      | Compound          | 2021–2025     |

## Working with the data

Read gzipped CSVs directly without decompressing to disk.

Python (pandas):

```python
import pandas as pd

df = pd.read_csv(
    "data/bars/EURUSD/EURUSD_2024.csv.gz",
    sep=";",
    parse_dates=["Time (EET)"],
    date_format="%Y.%m.%d %H:%M:%S",
)
```

Shell (quick inspection):

```bash
zcat data/bars/BTCUSD/BTCUSD_2024.csv.gz | head
```

## Experiments

`experiments/` holds isolated research, each attempting to find an **edge** with a
different trading strategy. See [`experiments/README.md`](./experiments/README.md)
for full conventions. The non-negotiable rules:

- Each experiment is **fully self-contained** in `experiments/<name>/`.
- The **only** shared source of information between experiments is the root
  `data/` corpus. No cross-experiment imports, shared modules, or shared state —
  if two experiments need the same helper, copy it into each.
- Experiments read `data/` as read-only; generated artifacts stay inside the
  experiment folder and are gitignored.

## Conventions for new code

**Default language: Python.** New experiments and implementations should use
Python with [**uv**](https://docs.astral.sh/uv/) for environment and dependency
management (`pyproject.toml` + `uv.lock`). Do **not** start new Rust projects.

A small amount of **legacy Rust code** remains (e.g.
`experiments/e0020_fast_backtester_composer/`,
`experiments/e0030_strategy_parameters/.../tf01_ema_crossover/`). Keep it as-is
for reference and reproducibility; do not extend or replicate the Rust stack for
new work.

### Python performance playbook (canonical reference)

For compute-heavy backtests and parameter searches, follow the conventions
validated in
[`experiments/e0030_strategy_parameters/cat01_trend_following/tf01_ema_crossover_python/`](./experiments/e0030_strategy_parameters/cat01_trend_following/tf01_ema_crossover_python/):

- **uv-managed** project: Python 3.12, pinned deps, `pytest` + `ruff`.
- **Polars** for multithreaded CSV loading; hand off **struct-of-arrays NumPy
  buffers** (`float64`/`int64`) to the compute layer — no DataFrames in hot loops.
- **Numba `@njit`** for path-dependent backtest kernels and resampling; `cache=True`
  and a fixed `NUMBA_CACHE_DIR`.
- **`numba.prange`** (`parallel=True`) for embarrassingly parallel grid search.
- **Precompute indicators once** per timeframe; slice with `np.searchsorted` for
  walk-forward windows (no per-window recomputation).
- Separate modules: `data.py`, `indicators.py`, `backtest.py`, `main.py`; unit
  tests under `tests/`.

See that experiment's [`README.md`](./experiments/e0030_strategy_parameters/cat01_trend_following/tf01_ema_crossover_python/README.md),
[`ROADMAP.md`](./experiments/e0030_strategy_parameters/cat01_trend_following/tf01_ema_crossover_python/ROADMAP.md)
(Performance engineering section), and [`PERFORMANCE.md`](./experiments/e0030_strategy_parameters/cat01_trend_following/tf01_ema_crossover_python/PERFORMANCE.md).
Copy/adapt its patterns into each new experiment — never import across experiments.

General rules (all languages):

- Keep the data layer separate from strategy/backtest logic.
- Never hardcode absolute machine paths; resolve data relative to the repo root.
- The `data/` corpus is committed and read-only; do not commit *generated*
  artifacts (outputs, caches, downloaded extras) — add them to `.gitignore`.

## Build / test / run

Default workflow for new Python experiments (from the experiment directory):

```bash
uv sync                 # create .venv and install pinned deps
uv run python main.py   # run the experiment entry point
uv run pytest           # unit tests
uv run ruff check       # lint
```

Per-experiment `README.md` files may add flags or alternate entry points. Legacy
Rust experiments use `cargo build --release` / `cargo run --release` as documented
in their own directories.

## Safety notes for agents

- The `data/` corpus is large; avoid reading entire files into memory or context
  when a sample (`head`, `nrows=...`) suffices.
- Treat market data as **read-only**; do not modify or delete files under `data/`.
  The corpus is version-controlled, so unintended edits would pollute history.
