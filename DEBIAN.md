# DEBIAN.md — Development Environment Setup (Ubuntu / Debian)

Instructions for setting up a Linux development environment that supports all
experiments in this repository.

## 1. System packages

```bash
sudo apt update && sudo apt install -y \
  build-essential \
  pkg-config \
  libssl-dev \
  libffi-dev \
  zlib1g-dev \
  python3.12 \
  python3.12-dev \
  python3.12-venv \
  git \
  curl \
  wget \
  jq \
  ripgrep \
  fd-find \
  htop \
  tree
```

## 2. uv (Python environment and package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your shell (or `source ~/.bashrc`) so that `uv` is on your `PATH`.

## 3. Rust toolchain (legacy experiments only)

Required only if you need to build or run the legacy Rust code under
`experiments/e0020_fast_backtester_composer/`.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

## 4. Per-experiment Python setup

Each experiment manages its own isolated environment via `uv`. From inside any
experiment directory:

```bash
uv sync                 # create .venv and install pinned deps
uv run python main.py   # run the experiment
uv run pytest           # run unit tests
uv run ruff check       # lint
```

Python packages used across experiments (pinned in each `pyproject.toml`):

| Package  | Purpose                                      |
| -------- | -------------------------------------------- |
| polars   | Multithreaded CSV loading                    |
| numpy    | Struct-of-arrays buffers for compute kernels |
| numba    | JIT-compiled backtest and indicator kernels  |
| pandas   | General data wrangling (earlier experiments) |
| pytest   | Unit testing                                 |
| ruff     | Linting and formatting                       |

## 5. Optional quality-of-life tools

```bash
sudo apt install -y bat
cargo install git-delta   # requires Rust from step 3
```

Configure `git-delta` as your diff pager:

```bash
git config --global core.pager delta
git config --global interactive.diffFilter "delta --color-only"
```

## Notes

- `build-essential`, `python3.12-dev`, and `uv` are the critical prerequisites;
  Numba and Polars will fail to compile native extensions without them.
- `gzip` / `zcat` ship with `coreutils` and are already present on any standard
  Debian/Ubuntu install — no explicit installation needed.
- Do **not** install Python packages globally with `pip`; let `uv` manage
  per-experiment virtual environments.
