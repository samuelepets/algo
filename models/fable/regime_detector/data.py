"""Load 1-minute OHLCV bars from the repo data corpus and resample to H1."""

from pathlib import Path

import pandas as pd

RESAMPLE_RULE = "1h"


def repo_root() -> Path:
    """Locate the repository root by searching upward for the data corpus."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "bars").is_dir():
            return parent
    raise FileNotFoundError("could not locate repo root containing data/bars/")


def load_minute_bars(symbol: str, years: list[int]) -> pd.DataFrame:
    """Load 1-minute bars for the given years, indexed by bar open time (EET, naive)."""
    frames = []
    for year in years:
        path = repo_root() / "data" / "bars" / symbol / f"{symbol}_{year}.csv.gz"
        frames.append(
            pd.read_csv(
                path,
                sep=";",
                parse_dates=["Time (EET)"],
                date_format="%Y.%m.%d %H:%M:%S",
            )
        )
    df = pd.concat(frames, ignore_index=True)
    df = df.rename(
        columns={
            "Time (EET)": "time",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    df = df.drop_duplicates(subset="time").sort_values("time").set_index("time")
    return df


def resample_bars(minute_bars: pd.DataFrame, rule: str = RESAMPLE_RULE) -> pd.DataFrame:
    """Aggregate 1-minute bars to a slower timeframe.

    The index keeps the bar *open* time; `time_close` marks when the bar's
    information becomes available (leakage-safe consumption point).
    """
    out = minute_bars.resample(rule, label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    out = out.dropna(subset=["open"])  # drop empty periods (weekends, holidays)
    out["time_close"] = out.index + pd.Timedelta(rule)
    return out


def resample_h1(minute_bars: pd.DataFrame) -> pd.DataFrame:
    return resample_bars(minute_bars, RESAMPLE_RULE)
