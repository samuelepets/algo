# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, Copilot, and other LLM tools)
working in this repository. Written to follow the cross-tool
[AGENTS.md](https://agents.md) convention so it works regardless of the model.

## Project overview

`algo` is an early-stage repository for **algorithmic trading research and
backtesting**. At the moment it contains only the historical market-data corpus;
there is no application, library, build system, or test suite yet. New code
(data loaders, indicators, strategies, backtester, etc.) is expected to be added
on top of this dataset.

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
└── data/
    └── bars/
        └── <SYMBOL>/<SYMBOL>_<YEAR>.csv.gz
```

> Note: `data/` is ~445 MB and is **not tracked by git** (only `LICENSE` and
> `README.md` are committed). Treat it as a local, read-only data source. If you
> add code that generates artifacts, do not commit large data files; add a
> `.gitignore` entry instead.

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

## Conventions for new code

There is no established stack yet, so when introducing one:

- Pick the language/tooling that best fits the task and **document the chosen
  commands here** (install, run, lint, test) so future agents can discover them.
- For Python, prefer a virtual environment and a pinned dependency file
  (`requirements.txt` or `pyproject.toml`).
- Keep the data layer separate from strategy/backtest logic.
- Never hardcode absolute machine paths; resolve data relative to the repo root.
- Do not commit generated artifacts or the contents of `data/`.

## Build / test / run

_None defined yet._ Update this section as soon as a build, test, or run command
exists, so it stays the single source of truth for how to work in the repo.

## Safety notes for agents

- The `data/` corpus is large; avoid reading entire files into memory or context
  when a sample (`head`, `nrows=...`) suffices.
- Treat market data as **read-only**; do not modify or delete files under `data/`.
- Avoid committing anything in `data/` to git.
