"""Ensemble aggregation of base strategies S1–S3."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _stack_signals(signals: list[pd.Series]) -> pd.DataFrame:
    if not signals:
        raise ValueError("signals must not be empty")
    index = signals[0].index
    for sig in signals[1:]:
        if not sig.index.equals(index):
            raise ValueError("all signals must share the same index")
    return pd.concat(signals, axis=1)


def majority_vote(signals: list[pd.Series], quorum: int | None = None) -> pd.Series:
    """Combine discrete {-1, 0, 1} signals by majority vote.

    With three strategies the default quorum is 2 (strict majority).
    """
    votes = _stack_signals(signals).sum(axis=1)
    n = len(signals)
    q = quorum if quorum is not None else (n // 2 + 1)
    out = pd.Series(0.0, index=votes.index)
    out[votes >= q] = 1.0
    out[votes <= -q] = -1.0
    return out


def averaged_signal(signals: list[pd.Series]) -> pd.Series:
    """Equal-weight average of signals, clipped to [-1, 1]."""
    return _stack_signals(signals).mean(axis=1).clip(-1.0, 1.0)


def inverse_vol_weighted_signal(
    signals: list[pd.Series],
    returns: list[pd.Series],
    window: int = 1440,
    min_periods: int = 100,
) -> pd.Series:
    """Weight each strategy's signal by inverse rolling volatility of its returns.

    ``window`` defaults to 1440 bars (~one day on 1-minute data). Rows with
    insufficient history fall back to equal weights.
    """
    if len(signals) != len(returns):
        raise ValueError("signals and returns must have the same length")

    index = signals[0].index
    inv_vols = []
    for ret in returns:
        vol = ret.reindex(index).rolling(window, min_periods=min_periods).std()
        inv_vols.append(1.0 / vol.replace(0.0, np.nan))

    weights = pd.concat(inv_vols, axis=1)
    weights = weights.div(weights.sum(axis=1), axis=0)
    weights = weights.fillna(1.0 / len(signals))

    sigs = _stack_signals(signals)
    combined = (sigs * weights).sum(axis=1)
    return combined.clip(-1.0, 1.0)


def return_correlation_matrix(
    returns: dict[str, pd.Series],
) -> pd.DataFrame:
    """Pearson correlation between per-strategy return streams."""
    frame = pd.DataFrame(returns)
    return frame.corr()


ENSEMBLE_METHODS = ("majority_vote", "averaged", "inverse_vol")
