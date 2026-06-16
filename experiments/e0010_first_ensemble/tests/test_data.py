"""Tests for the e0010 data access layer (run against the real EUR/USD corpus)."""

from __future__ import annotations

import pandas as pd
import pytest

import data


def test_available_years_eurusd() -> None:
    years = data.available_years("EURUSD")
    assert years, "expected at least one year of EUR/USD data"
    assert years == sorted(years)
    assert min(years) <= 2003 and max(years) >= 2024


def test_available_years_unknown_symbol_raises() -> None:
    with pytest.raises(FileNotFoundError):
        data.available_years("NOPE123")


def test_load_bars_single_year() -> None:
    df = data.load_bars("EURUSD", years=[2024])
    assert list(df.columns) == data.OHLCV_COLUMNS
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.name == "time"
    assert len(df) > 100_000  # a full year of 1-minute bars
    assert df.index.is_monotonic_increasing
    assert not df.index.has_duplicates
    assert df["close"].notna().all()
    assert (df["high"] >= df["low"]).all()


def test_load_bars_range_is_continuous_concat() -> None:
    df = data.load_bars("EURUSD", start_year=2023, end_year=2024)
    only_2024 = data.load_bars("EURUSD", years=[2024])
    only_2023 = data.load_bars("EURUSD", years=[2023])
    assert len(df) == len(only_2023) + len(only_2024)
    assert df.index.is_monotonic_increasing


def test_load_bars_requires_years() -> None:
    with pytest.raises(ValueError):
        data.load_bars("EURUSD", years=[])


def test_resample_to_hourly() -> None:
    minute = data.load_bars("EURUSD", years=[2024])
    hourly = data.resample(minute, "1h")
    assert len(hourly) < len(minute)
    assert list(hourly.columns) == data.OHLCV_COLUMNS
    assert hourly["open"].notna().all()  # empty buckets dropped
    assert (hourly["high"] >= hourly["low"]).all()
