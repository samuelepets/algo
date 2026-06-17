# Strategies

This folder documents **trading strategies** under research and development for
the `algo` project.

## Purpose

Each strategy documented here describes an approach to generating trading signals
from market data. The goal is to maintain a structured library of ideas,
hypotheses, and findings that can eventually be implemented and validated inside
the `experiments/` folder.

## Scope

- Strategies operate on **1-minute OHLCV bars** (or bars derived from them, e.g.
  5-minute, 15-minute, hourly) sourced from the `data/bars/` corpus.
- Covered instruments: Forex (EURUSD), Metals (XAUUSD, XAGUSD), and Crypto
  (BTCUSD, ETHUSD, BATUSD, ADAUSD, AVEUSD, CMPUSD).
- Each strategy entry should describe its **hypothesis**, the **signals** it
  produces, and any **known risks or limitations**.

## Structure

```
strategies/
├── README.md          # this file
├── ROADMAP.md         # research roadmap
└── <strategy-name>/   # one folder per strategy (added as research progresses)
    └── README.md      # hypothesis, signals, parameters, references
```

## Relationship to Experiments

Strategies documented here are candidates for implementation. Once a strategy is
mature enough to backtest, a corresponding experiment is created under
`experiments/` following the conventions in that folder's README.
