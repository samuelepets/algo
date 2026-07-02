"""Technical indicators for mr04_zscore_reversion.

SMA, generic rolling population std, Wilder ATR, log-returns, and rolling
z-score computations over two candidate input series: log-returns and
detrended close price.
"""

from __future__ import annotations

import numpy as np
from numba import njit

ATR_PERIOD = 14
ZSCORE_WINDOWS = [20, 30, 60, 120, 240]


@njit(cache=True)
def sma(close: np.ndarray, period: int) -> np.ndarray:
    """Rolling SMA using a sliding-window accumulator."""
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
def rolling_std(series: np.ndarray, period: int) -> np.ndarray:
    """Rolling population std (ddof=0) over an arbitrary input series.

    Recomputes each window from scratch (no sliding accumulator), so a single
    NaN sentinel outside the active window never poisons later outputs.
    """
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    if n < period or period < 1:
        return out
    for i in range(period - 1, n):
        mu = 0.0
        for j in range(period):
            mu += series[i - period + 1 + j]
        mu /= period
        var = 0.0
        for j in range(period):
            d = series[i - period + 1 + j] - mu
            var += d * d
        out[i] = (var / period) ** 0.5
    return out


@njit(cache=True)
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR."""
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


@njit(cache=True)
def log_returns(close: np.ndarray) -> np.ndarray:
    """Bar-over-bar log returns. ``out[0]`` is NaN (no prior bar)."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    out[0] = np.nan
    for i in range(1, n):
        out[i] = np.log(close[i] / close[i - 1])
    return out


@njit(cache=True)
def zscore_log_return(close: np.ndarray, window: int) -> np.ndarray:
    """Rolling z-score of log-returns: ``(r - SMA(r, w)) / std(r, w)``.

    ``log_returns`` has a NaN sentinel at index 0 (no prior bar). Feeding that
    NaN into ``sma``'s sliding-window accumulator would poison every
    subsequent output (NaN never clears from a running sum). To avoid this we
    feed ``sma``/``rolling_std`` a sanitized copy with index 0 set to 0.0 (a
    neutral placeholder that only ever contributes to the single earliest
    warm-up window) while the final z-score output still checks the
    *original* (unsanitized) return series for NaN, so ``out[0]`` is NaN as
    expected.
    """
    n = len(close)
    returns = log_returns(close)
    returns_clean = returns.copy()
    if n > 0:
        returns_clean[0] = 0.0
    mu = sma(returns_clean, window)
    sigma = rolling_std(returns_clean, window)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    for i in range(n):
        if np.isnan(returns[i]) or np.isnan(mu[i]) or np.isnan(sigma[i]) or sigma[i] < 1e-12:
            continue
        out[i] = (returns[i] - mu[i]) / sigma[i]
    return out


@njit(cache=True)
def zscore_close_detrended(close: np.ndarray, window: int) -> np.ndarray:
    """Rolling z-score of close price: ``(c - SMA(c, w)) / std(c, w)``."""
    n = len(close)
    mu = sma(close, window)
    sigma = rolling_std(close, window)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = np.nan
    for i in range(n):
        if np.isnan(mu[i]) or np.isnan(sigma[i]) or sigma[i] < 1e-12:
            continue
        out[i] = (close[i] - mu[i]) / sigma[i]
    return out


def build_zscore_cache(
    close: np.ndarray, windows: list[int]
) -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    """Precompute both z-score variants for all unique windows.

    Returns ``(log_return_matrix, close_detrended_matrix, window_index)``
    where each matrix row corresponds to one window and ``window_index[w]``
    gives the shared row index into both matrices.
    """
    unique_windows = sorted(set(windows))
    n = len(close)
    log_return_matrix = np.empty((len(unique_windows), n), dtype=np.float64)
    close_detrended_matrix = np.empty((len(unique_windows), n), dtype=np.float64)
    window_index: dict[int, int] = {}
    for row, w in enumerate(unique_windows):
        log_return_matrix[row] = zscore_log_return(close, w)
        close_detrended_matrix[row] = zscore_close_detrended(close, w)
        window_index[w] = row
    return log_return_matrix, close_detrended_matrix, window_index
