"""Regime features on resampled bars. All windows are trailing (no look-ahead)."""

import numpy as np
import pandas as pd

ATR_PERIOD = 14
ADX_PERIOD = 14
ER_PERIOD = 20
EMA_FAST = 20
EMA_SLOW = 50
SLOPE_LAG = 10
BB_PERIOD = 20
# Trailing window for the ATR percentile, expressed in days (24h forex sessions).
ATR_PCT_DAYS = 90
ATR_PCT_MIN_DAYS = 30


def _wilder(x: pd.Series, period: int) -> pd.Series:
    return x.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def adx(df: pd.DataFrame, period: int = ADX_PERIOD) -> pd.Series:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr = _wilder(true_range(df), period)
    plus_di = 100.0 * _wilder(plus_dm, period) / atr
    minus_di = 100.0 * _wilder(minus_dm, period) / atr
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return _wilder(dx, period)


def efficiency_ratio(close: pd.Series, period: int = ER_PERIOD) -> pd.Series:
    net = (close - close.shift(period)).abs()
    path = close.diff().abs().rolling(period).sum()
    return net / path


def compute_features(df: pd.DataFrame, bars_per_day: int = 24) -> pd.DataFrame:
    """Return the input bars augmented with the regime feature columns.

    `bars_per_day` scales the ATR-percentile window to the bar timeframe
    (24 for H1, 6 for H4).
    """
    out = df.copy()
    out["ret"] = np.log(out["close"] / out["close"].shift(1))
    out["atr"] = _wilder(true_range(out), ATR_PERIOD)
    out["adx"] = adx(out)
    out["er"] = efficiency_ratio(out["close"])
    out["ema_fast"] = out["close"].ewm(span=EMA_FAST, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=EMA_SLOW, adjust=False).mean()
    out["slope_norm"] = (out["ema_slow"] - out["ema_slow"].shift(SLOPE_LAG)) / out["atr"]
    sma = out["close"].rolling(BB_PERIOD).mean()
    std = out["close"].rolling(BB_PERIOD).std()
    out["bb_width"] = (4.0 * std) / sma
    out["atr_pct"] = (
        out["atr"]
        .rolling(ATR_PCT_DAYS * bars_per_day, min_periods=ATR_PCT_MIN_DAYS * bars_per_day)
        .rank(pct=True)
    )
    return out
