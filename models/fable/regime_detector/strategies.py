"""Toy strategies for the §7.3 economic validation of the regime detector.

Positions are decided on each bar's close and must be applied to the *next*
bar's return by the caller. Values are +1 (long), -1 (short), 0 (flat).
"""

import numpy as np
import pandas as pd


def ema_crossover_positions(close: pd.Series, fast: int = 20, slow: int = 50) -> pd.Series:
    """Always-in trend follower: long while EMA(fast) > EMA(slow), else short."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    pos = np.sign(ema_fast - ema_slow)
    pos.iloc[: slow] = 0.0  # warmup
    return pos


def bollinger_fade_positions(close: pd.Series, period: int = 20, k: float = 2.0) -> pd.Series:
    """Mean reverter: long below the lower band, short above the upper band,
    exit when price crosses back through the middle band."""
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = (sma + k * std).to_numpy()
    lower = (sma - k * std).to_numpy()
    mid = sma.to_numpy()
    c = close.to_numpy()

    pos = np.zeros(len(c))
    state = 0.0
    for i in range(len(c)):
        if np.isnan(mid[i]):
            pos[i] = 0.0
            continue
        if state == 0.0:
            if c[i] < lower[i]:
                state = 1.0
            elif c[i] > upper[i]:
                state = -1.0
        elif state == 1.0 and c[i] >= mid[i]:
            state = 0.0
        elif state == -1.0 and c[i] <= mid[i]:
            state = 0.0
        pos[i] = state
    return pd.Series(pos, index=close.index)


def strategy_returns(
    close: pd.Series, pos: pd.Series, half_spread_pips: float = 0.5
) -> pd.Series:
    """Next-bar log returns of a position series, net of spread costs.

    The position decided at bar t earns bar t+1's return; each unit of
    position change pays `half_spread_pips` (so a full round trip costs 2x).
    """
    ret = np.log(close / close.shift(1))
    held = pos.shift(1).fillna(0.0)
    turnover = (held - held.shift(1)).abs().fillna(0.0)
    cost = turnover * (half_spread_pips * 1e-4) / close
    return held * ret - cost
