"""Shared data access layer for e0030 strategy parameter experiments.

Loads 1-minute OHLCV bars from the repository read-only ``data/`` corpus and
exposes them as struct-of-arrays NumPy buffers for Numba kernels.

Timestamp policy: naive ``YYYY.MM.DD HH:MM:SS`` labels are converted to epoch
seconds *as if UTC* (no real EET offset), keeping walk-forward year boundaries
consistent across experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl
from numba import njit

# shared/algo_shared/data.py -> algo_shared/ -> shared/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "bars"

_TIME_COLUMN = "Time (EET)"
_TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
_SOURCE_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


@dataclass(frozen=True)
class BarArrays:
    """Contiguous OHLCV arrays sorted ascending by ``ts``."""

    ts: np.ndarray  # int64 epoch seconds
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray


def year_start_ts(year: int) -> int:
    """Epoch seconds of ``year``-01-01 00:00:00 treated as UTC."""
    dt = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return int(dt.timestamp())


def ts_range(ts: np.ndarray, start_ts: int, end_ts: int) -> tuple[int, int]:
    """Return index range ``[start, end)`` for ``ts`` in ``[start_ts, end_ts)``."""
    s = int(np.searchsorted(ts, start_ts, side="left"))
    e = int(np.searchsorted(ts, end_ts, side="left"))
    return s, e


def _parse_epoch_seconds(labels: pl.Series) -> np.ndarray:
    return (
        labels.str.to_datetime(_TIME_FORMAT)
        .dt.epoch(time_unit="s")
        .cast(pl.Int64)
        .to_numpy()
    )


def _read_year(path: Path) -> BarArrays:
    frame = pl.read_csv(
        path,
        separator=";",
        columns=[_TIME_COLUMN, *_SOURCE_COLUMNS],
        schema_overrides={
            "Open": pl.Float64,
            "High": pl.Float64,
            "Low": pl.Float64,
            "Close": pl.Float64,
            "Volume": pl.Float64,
        },
    )
    ts = _parse_epoch_seconds(frame[_TIME_COLUMN])
    return BarArrays(
        ts=ts,
        open=frame["Open"].to_numpy(),
        high=frame["High"].to_numpy(),
        low=frame["Low"].to_numpy(),
        close=frame["Close"].to_numpy(),
        volume=frame["Volume"].to_numpy(),
    )


def load_symbol(symbol: str, data_dir: Path | None = None) -> BarArrays:
    """Load all yearly CSV.GZ files for ``symbol`` as a sorted struct-of-arrays.

    Scans ``data/bars/<symbol>/`` for files matching ``<symbol>_*.csv.gz``.
    Deduplicates timestamps and sorts ascending.
    """
    root = data_dir if data_dir is not None else DATA_DIR / symbol
    if not root.is_dir():
        raise FileNotFoundError(f"Data directory not found: {root}")

    paths = sorted(root.glob(f"{symbol}_*.csv.gz"))
    if not paths:
        raise FileNotFoundError(f"No bar files found under {root}")

    chunks = [_read_year(p) for p in paths]

    ts = np.concatenate([c.ts for c in chunks])
    open_ = np.concatenate([c.open for c in chunks])
    high = np.concatenate([c.high for c in chunks])
    low = np.concatenate([c.low for c in chunks])
    close = np.concatenate([c.close for c in chunks])
    volume = np.concatenate([c.volume for c in chunks])

    order = np.argsort(ts, kind="stable")
    ts = ts[order]
    open_ = open_[order]
    high = high[order]
    low = low[order]
    close = close[order]
    volume = volume[order]

    _, unique_idx = np.unique(ts, return_index=True)
    unique_idx.sort()
    return BarArrays(
        ts=ts[unique_idx],
        open=open_[unique_idx],
        high=high[unique_idx],
        low=low[unique_idx],
        close=close[unique_idx],
        volume=volume[unique_idx],
    )


def load_eurusd(data_dir: Path | None = None) -> BarArrays:
    """Load all EURUSD yearly files as a sorted struct-of-arrays."""
    return load_symbol("EURUSD", data_dir)


@njit(cache=True)
def _resample_core(
    ts: np.ndarray,
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    bucket_secs: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(ts)
    if n == 0:
        empty = np.empty(0, dtype=np.float64)
        empty_i = np.empty(0, dtype=np.int64)
        return empty_i, empty, empty, empty, empty, empty

    max_out = n // max(bucket_secs // 60, 1) + 2
    out_ts = np.empty(max_out, dtype=np.int64)
    out_open = np.empty(max_out, dtype=np.float64)
    out_high = np.empty(max_out, dtype=np.float64)
    out_low = np.empty(max_out, dtype=np.float64)
    out_close = np.empty(max_out, dtype=np.float64)
    out_volume = np.empty(max_out, dtype=np.float64)

    cur_bucket = (ts[0] // bucket_secs) * bucket_secs
    o = open_[0]
    h = high[0]
    lo = low[0]
    c = close[0]
    v = volume[0]
    out_idx = 0

    for i in range(1, n):
        b = (ts[i] // bucket_secs) * bucket_secs
        if b == cur_bucket:
            if high[i] > h:
                h = high[i]
            if low[i] < lo:
                lo = low[i]
            c = close[i]
            v += volume[i]
        else:
            out_ts[out_idx] = cur_bucket
            out_open[out_idx] = o
            out_high[out_idx] = h
            out_low[out_idx] = lo
            out_close[out_idx] = c
            out_volume[out_idx] = v
            out_idx += 1

            cur_bucket = b
            o = open_[i]
            h = high[i]
            lo = low[i]
            c = close[i]
            v = volume[i]

    out_ts[out_idx] = cur_bucket
    out_open[out_idx] = o
    out_high[out_idx] = h
    out_low[out_idx] = lo
    out_close[out_idx] = c
    out_volume[out_idx] = v
    out_idx += 1

    return (
        out_ts[:out_idx],
        out_open[:out_idx],
        out_high[:out_idx],
        out_low[:out_idx],
        out_close[:out_idx],
        out_volume[:out_idx],
    )


def resample(bars: BarArrays, minutes: int) -> BarArrays:
    """Resample 1-min bars to ``minutes``-minute OHLCV buckets."""
    bucket_secs = minutes * 60
    ts, o, h, lo, c, v = _resample_core(
        bars.ts, bars.open, bars.high, bars.low, bars.close, bars.volume, bucket_secs
    )
    return BarArrays(ts=ts, open=o, high=h, low=lo, close=c, volume=v)
