# e0010_first_ensemble

First experiment: build a baseline **ensemble** of simple trading strategies and
test whether combining them yields a more robust edge than any single component.

This experiment is **self-contained** (see [`../README.md`](../README.md)). Its
only external dependency is the root [`data/`](../../data) corpus, which is
**read-only**.

- **Rationale:** see [`RATIONALE.md`](./RATIONALE.md).
- **Implementation roadmap:** see [`ROADMAP.md`](./ROADMAP.md).

## Tech stack & conventions

- **Language:** all code in this experiment is **Python** (no other languages).
- **Environment & dependencies:** managed exclusively with
  [**uv**](https://docs.astral.sh/uv/). Do not use bare `pip`, `venv`,
  `virtualenv`, or `conda` here.

### uv workflow (best practices)

```bash
# From this experiment directory: experiments/e0010_first_ensemble/

# 1. Initialize the project (creates pyproject.toml + pins a Python version)
uv init --python 3.12

# 2. Add dependencies (updates pyproject.toml AND uv.lock; creates .venv)
uv add pandas numpy

# Dev-only tools go in a dev group
uv add --dev pytest ruff

# 3. Run code through uv (auto-syncs the env from the lockfile first)
uv run python main.py
uv run pytest

# 4. Reproduce the exact environment elsewhere
uv sync            # local
uv sync --frozen   # CI: fail if the lockfile is out of date
```

Guidelines:

- **Commit** `pyproject.toml` and `uv.lock` for reproducibility; **never commit**
  `.venv/` (it is gitignored).
- Always declare deps with `uv add` (which updates the lockfile), not ad-hoc
  installs into the active environment.
- Pin the Python version via `.python-version` / `requires-python` in
  `pyproject.toml` so results are reproducible.
- Run everything via `uv run ...` so the environment is always in sync.
- Use `uvx <tool>` for one-off tools you don't want as project dependencies.

## Data access

Load bars from the root corpus using a path resolved relative to the repo root,
e.g. `../../data/bars/<SYMBOL>/<SYMBOL>_<YEAR>.csv.gz`. Never write into `data/`.

## Outputs

Generated artifacts (metrics, plots, cached computations) go under `outputs/` and
are gitignored. Only commit code, configs, and the written-up findings.
