"""Data access layer for experiment e0010_first_ensemble.

Loads 1-minute OHLCV bars from the repository's read-only ``data/`` corpus and
exposes them as pandas DataFrames. The price series is treated as a single
**continuous stream**: bars are concatenated in chronological order and we do not
insert rows for the gaps left by inactive periods (overnight/weekends). See
``RATIONALE.md`` for why.

The corpus is read-only; nothing here ever writes into ``data/``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# experiments/e0010_first_ensemble/data.py -> repo root is two levels up.
REPO_ROOT = Path(__file__).resolve().parents[2]
BARS_DIR = REPO_ROOT / "data" / "bars"

#: Source header (semicolon-delimited) -> canonical lowercase column names.
_SOURCE_COLUMNS = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}
OHLCV_COLUMNS = list(_SOURCE_COLUMNS.values())
_TIME_COLUMN = "Time (EET)"
_TIME_FORMAT = "%Y.%m.%d %H:%M:%S"


def _year_file(symbol: str, year: int) -> Path:
    return BARS_DIR / symbol / f"{symbol}_{year}.csv.gz"


def available_years(symbol: str) -> list[int]:
    """Return the sorted list of years available for ``symbol`` in the corpus."""
    symbol_dir = BARS_DIR / symbol
    if not symbol_dir.is_dir():
        raise FileNotFoundError(f"No data directory for symbol {symbol!r}: {symbol_dir}")
    prefix = f"{symbol}_"
    years = [
        int(p.name[len(prefix) :].split(".", 1)[0])
        for p in symbol_dir.glob(f"{symbol}_*.csv.gz")
    ]
    return sorted(years)


def _read_year(symbol: str, year: int) -> pd.DataFrame:
    path = _year_file(symbol, year)
    if not path.is_file():
        raise FileNotFoundError(f"Missing bars file: {path}")
    df = pd.read_csv(
        path,
        sep=";",
        usecols=[_TIME_COLUMN, *_SOURCE_COLUMNS.keys()],
        dtype={col: "float64" for col in _SOURCE_COLUMNS},
    )
    df[_TIME_COLUMN] = pd.to_datetime(df[_TIME_COLUMN], format=_TIME_FORMAT)
    df = df.rename(columns={_TIME_COLUMN: "time", **_SOURCE_COLUMNS})
    return df.set_index("time")[OHLCV_COLUMNS]


def load_bars(
    symbol: str,
    start_year: int | None = None,
    end_year: int | None = None,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Load 1-minute OHLCV bars for ``symbol`` as a continuous, time-sorted frame.

    Select the period either with an explicit ``years`` list or with an inclusive
    ``start_year``/``end_year`` range; with no arguments, every available year is
    loaded. The result has a ``DatetimeIndex`` named ``time`` and the columns
    ``open, high, low, close, volume``. Duplicate timestamps are dropped (first
    kept) and the index is sorted ascending; no rows are inserted for inactive
    periods, so consecutive rows form the continuous stream.
    """
    if years is None:
        all_years = available_years(symbol)
        lo = start_year if start_year is not None else (all_years[0] if all_years else 0)
        hi = end_year if end_year is not None else (all_years[-1] if all_years else 0)
        years = [y for y in all_years if lo <= y <= hi]
    else:
        years = sorted(years)

    if not years:
        raise ValueError(f"No years selected for symbol {symbol!r}")

    frame = pd.concat([_read_year(symbol, y) for y in years])
    frame = frame[~frame.index.duplicated(keep="first")].sort_index()
    return frame


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample 1-minute OHLCV bars to a coarser ``rule`` (e.g. ``"5min"``, ``"1h"``).

    Empty buckets (which a calendar resample would create over inactive periods)
    are dropped so the output stays a continuous stream of populated bars.
    """
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    out = df.resample(rule).agg(agg)
    return out.dropna(subset=["open"])
