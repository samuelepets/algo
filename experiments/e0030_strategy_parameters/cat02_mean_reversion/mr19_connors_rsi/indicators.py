"""Technical indicators for mr19_connors_rsi.

Connors RSI (CRSI) combines three components: (1) RSI(rsi_period) of close,
(2) RSI(ud_rsi_period) of the consecutive up/down "streak" series, (3) a
percentile rank of the 1-bar ROC over a trailing window. Plus SMA for the
trend filter and Wilder ATR for stop sizing.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
RSI_PERIODS = [2, 3, 4]
UD_RSI_PERIODS = [2, 3]
ROC_RANK_PERIODS = [50, 100, 200]
TREND_SMA_PERIODS = [100, 200]

# Same numerical-stability guard used in mr09/mr14/mr15/mr18/mr20, matching
# mr09's established floor (0.1 pip on EURUSD) -- see README for why 1e-6
# was insufficient here specifically.
ATR_FLOOR = 1e-5


@njit(cache=True)
def rsi(close: np.ndarray, period: int) -> np.ndarray:
    """Wilder RSI (identical formulation to mr13/mr14)."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period + 1 or period < 1:
        return out

    gains = np.empty(n, dtype=np.float64)
    losses = np.empty(n, dtype=np.float64)
    gains[0] = 0.0
    losses[0] = 0.0
    for i in range(1, n):
        delta = close[i] - close[i - 1]
        gains[i] = delta if delta > 0.0 else 0.0
        losses[i] = -delta if delta < 0.0 else 0.0

    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(1, period + 1):
        avg_gain += gains[i]
        avg_loss += losses[i]
    avg_gain /= period
    avg_loss /= period

    def _rsi_from(ag: float, al: float) -> float:
        if al < 1e-12:
            return 100.0
        rs = ag / al
        return 100.0 - (100.0 / (1.0 + rs))

    out[period] = _rsi_from(avg_gain, avg_loss)
    k = 1.0 / period
    for i in range(period + 1, n):
        avg_gain = avg_gain + k * (gains[i] - avg_gain)
        avg_loss = avg_loss + k * (losses[i] - avg_loss)
        out[i] = _rsi_from(avg_gain, avg_loss)

    return out


@njit(cache=True)
def streak(close: np.ndarray) -> np.ndarray:
    """Consecutive up/down streak length series.

    ``streak[i] = streak[i-1] + 1`` on a higher close (or ``+1`` if the
    prior streak was not itself positive -- direction reset); mirrored for
    lower closes; ``0`` on an unchanged close. First bar has no prior close
    to compare, so ``streak[0] = 0``.
    """
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    out[0] = 0.0
    for i in range(1, n):
        prev = out[i - 1]
        if close[i] > close[i - 1]:
            out[i] = prev + 1.0 if prev > 0.0 else 1.0
        elif close[i] < close[i - 1]:
            out[i] = prev - 1.0 if prev < 0.0 else -1.0
        else:
            out[i] = 0.0
    return out


@njit(cache=True)
def roc_percentile_rank(close: np.ndarray, period: int) -> np.ndarray:
    """Percentile rank of the 1-bar ROC within a trailing ``period`` window.

    ``ROC(1)[i] = close[i]/close[i-1] - 1``. The percentile rank at ``i`` is
    the fraction (as a 0-100 value) of the trailing ``period`` ROC values
    (including the current bar) that are ``<=`` the current ROC. First valid
    ROC is at index 1; first valid percentile rank needs ``period`` valid ROC
    values, i.e. index ``period``.
    """
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period + 1 or period < 1:
        return out

    roc = np.empty(n, dtype=np.float64)
    roc[0] = np.nan
    for i in range(1, n):
        roc[i] = close[i] / close[i - 1] - 1.0

    for i in range(period, n):
        current = roc[i]
        count = 0
        for j in range(i - period + 1, i + 1):
            if roc[j] <= current:
                count += 1
        out[i] = 100.0 * count / period

    return out


@njit(cache=True)
def sma(close: np.ndarray, period: int) -> np.ndarray:
    """Rolling SMA using a sliding-window accumulator (identical to mr01)."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out
    s = 0.0
    for i in range(period):
        s += close[i]
    out[period - 1] = s / period
    for i in range(period, n):
        s += close[i] - close[i - period]
        out[i] = s / period
    return out


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR (identical formulation to mr01/mr03/mr13)."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < 2 or period == 0:
        return out
    tr = np.empty(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)
    if n < period:
        return out
    seed = 0.0
    for i in range(period):
        seed += tr[i]
    seed /= period
    out[period - 1] = seed
    k = 1.0 / period
    for i in range(period, n):
        out[i] = out[i - 1] + k * (tr[i] - out[i - 1])
    return out


def build_rsi_cache(close: np.ndarray, periods: list[int]) -> tuple[np.ndarray, dict[int, int]]:
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = rsi(close, p)
        period_index[p] = row
    return matrix, period_index


def build_ud_rsi_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    streak_vals = streak(close)
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = rsi(streak_vals, p)
        period_index[p] = row
    return matrix, period_index


def build_roc_rank_cache(
    close: np.ndarray, periods: list[int]
) -> tuple[np.ndarray, dict[int, int]]:
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = roc_percentile_rank(close, p)
        period_index[p] = row
    return matrix, period_index


def build_sma_cache(close: np.ndarray, periods: list[int]) -> tuple[np.ndarray, dict[int, int]]:
    unique_periods = sorted(set(periods))
    n = len(close)
    matrix = np.empty((len(unique_periods), n), dtype=np.float64)
    period_index: dict[int, int] = {}
    for row, p in enumerate(unique_periods):
        matrix[row] = sma(close, p)
        period_index[p] = row
    return matrix, period_index
