# experiments

Isolated trading research. Each experiment lives in its own subdirectory and is a
self-contained attempt to find an **edge** with a given strategy idea.

## Core rule: experiments are isolated

- Every experiment is **fully self-contained** in `experiments/<name>/`.
- The **only** shared source of information between experiments is the root
  [`data/`](../data) corpus (read-only market data).
- An experiment MUST NOT import from, depend on, read outputs of, or otherwise
  reference another experiment. No cross-experiment imports, shared modules, or
  shared state.
- If two experiments need the same helper code, **copy it** into each experiment
  (duplication is preferred over coupling here) or promote it to a shared library
  *outside* `experiments/` only once it is genuinely stable and general.

This isolation keeps every result independently reproducible and prevents one
experiment's assumptions from silently leaking into another.

## Layout

```
experiments/
├── README.md
└── <experiment-name>/        # one directory per experiment, self-contained
    ├── README.md             # hypothesis, method, results, conclusion
    ├── ...                   # code, configs, notebooks for this experiment
    └── outputs/              # generated artifacts (gitignored)
```

## Conventions

- **Naming:** use a short, descriptive, kebab-case name, optionally prefixed with
  a date or index (e.g. `2026-06-mean-reversion-eurusd`, `001-momentum-btc`).
- **Read-only data:** load bars from the root `data/` directory; resolve the path
  relative to the repo root, never with absolute machine paths. Never modify,
  rewrite, or write into `data/`.
- **Document the edge:** each experiment's `README.md` should state the
  hypothesis, the data window/instruments used, the method, the results, and a
  clear conclusion (edge found / not found / inconclusive).
- **Outputs are disposable:** write generated artifacts (metrics, plots, cached
  computations) under the experiment's own folder and keep them out of git via
  `.gitignore`. Only commit the code and the written-up findings.
