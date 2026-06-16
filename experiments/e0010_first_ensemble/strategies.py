"""Base strategies S1–S3 for experiment e0010_first_ensemble.

Each class implements ``backtest.Strategy`` and maps OHLCV bars to a target
position in ``[-1, 1]`` using only information up to and including ``Close(t)``.
Rules match ``RATIONALE.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int) -> pd.Series:
    """Wilder RSI on ``close``."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def crossed_above(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossed_below(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a < b) & (a.shift(1) >= b.shift(1))


def _run_state_machine(
    index: pd.Index,
    long_entry: np.ndarray,
    short_entry: np.ndarray,
    long_exit: np.ndarray,
    short_exit: np.ndarray,
) -> pd.Series:
    """Map boolean entry/exit arrays to a position series (0 / 1 / -1)."""
    n = len(index)
    position = np.zeros(n, dtype=np.float64)
    state = 0.0

    for i in range(n):
        if state == 1.0 and long_exit[i]:
            state = 0.0
        elif state == -1.0 and short_exit[i]:
            state = 0.0

        if state == 0.0:
            if long_entry[i]:
                state = 1.0
            elif short_entry[i]:
                state = -1.0

        position[i] = state

    return pd.Series(position, index=index, dtype=float)


@dataclass
class ConnorsRsi2:
    """S1 — Connors RSI(2) mean-reversion with SMA regime filter."""

    name: str = "S1_connors_rsi2"
    sma_regime: int = 200
    sma_exit: int = 5
    rsi_period: int = 2
    rsi_oversold: float = 10.0
    rsi_overbought: float = 90.0

    def generate_signal(self, bars: pd.DataFrame) -> pd.Series:
        close = bars["close"]
        regime = sma(close, self.sma_regime)
        exit_ma = sma(close, self.sma_exit)
        rsi_val = rsi(close, self.rsi_period)

        long_entry = ((close > regime) & (rsi_val < self.rsi_oversold)).fillna(False).to_numpy()
        short_entry = ((close < regime) & (rsi_val > self.rsi_overbought)).fillna(False).to_numpy()
        long_exit = (close > exit_ma).fillna(False).to_numpy()
        short_exit = (close < exit_ma).fillna(False).to_numpy()

        return _run_state_machine(bars.index, long_entry, short_entry, long_exit, short_exit)


@dataclass
class EmaCrossRsi:
    """S2 — Dual EMA crossover with RSI momentum filter."""

    name: str = "S2_ema_cross_rsi"
    fast_period: int = 9
    slow_period: int = 21
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0

    def generate_signal(self, bars: pd.DataFrame) -> pd.Series:
        close = bars["close"]
        fast = ema(close, self.fast_period)
        slow = ema(close, self.slow_period)
        rsi_val = rsi(close, self.rsi_period)

        bull_cross = crossed_above(fast, slow).fillna(False)
        bear_cross = crossed_below(fast, slow).fillna(False)

        long_entry = (bull_cross & (rsi_val < self.rsi_overbought)).fillna(False).to_numpy()
        short_entry = (bear_cross & (rsi_val > self.rsi_oversold)).fillna(False).to_numpy()
        long_exit = bear_cross.to_numpy()
        short_exit = bull_cross.to_numpy()

        return _run_state_machine(bars.index, long_entry, short_entry, long_exit, short_exit)


@dataclass
class RsiCenterlineEma:
    """S3 — RSI 50-centerline crossover with EMA trend filter."""

    name: str = "S3_rsi_centerline_ema"
    ema_period: int = 50
    rsi_period: int = 14
    centerline: float = 50.0

    def generate_signal(self, bars: pd.DataFrame) -> pd.Series:
        close = bars["close"]
        trend = ema(close, self.ema_period)
        rsi_val = rsi(close, self.rsi_period)

        rsi_up = crossed_above(rsi_val, pd.Series(self.centerline, index=bars.index)).fillna(False)
        rsi_down = crossed_below(rsi_val, pd.Series(self.centerline, index=bars.index)).fillna(False)

        long_entry = (rsi_up & (close > trend)).fillna(False).to_numpy()
        short_entry = (rsi_down & (close < trend)).fillna(False).to_numpy()
        long_exit = rsi_down.to_numpy()
        short_exit = rsi_up.to_numpy()

        return _run_state_machine(bars.index, long_entry, short_entry, long_exit, short_exit)


ALL_STRATEGIES: list[ConnorsRsi2 | EmaCrossRsi | RsiCenterlineEma] = [
    ConnorsRsi2(),
    EmaCrossRsi(),
    RsiCenterlineEma(),
]

STRATEGY_KEYS: dict[str, type[ConnorsRsi2] | type[EmaCrossRsi] | type[RsiCenterlineEma]] = {
    "S1_connors_rsi2": ConnorsRsi2,
    "S2_ema_cross_rsi": EmaCrossRsi,
    "S3_rsi_centerline_ema": RsiCenterlineEma,
}


def strategy_from_key(
    key: str,
    params: dict[str, int | float] | None = None,
) -> ConnorsRsi2 | EmaCrossRsi | RsiCenterlineEma:
    """Instantiate a strategy by registry key, optionally overriding parameters."""
    cls = STRATEGY_KEYS[key]
    return cls(**params) if params else cls()


def default_strategy(key: str) -> ConnorsRsi2 | EmaCrossRsi | RsiCenterlineEma:
    return strategy_from_key(key)
