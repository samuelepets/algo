"""Vectorized backtest harness for experiment e0010_first_ensemble.

Execution convention (see ``RATIONALE.md``): a strategy emits a target position
``signal_t`` in ``[-1, 1]`` using information available up to and including
``Close(t)``; the trade is executed at ``Open(t+1)``. Concretely the position
held over the interval ``[Open(t), Open(t+1)]`` is ``signal_{t-1}`` (i.e.
``signal.shift(1)``), and the per-bar return is the open-to-open return
``Open(t+1) / Open(t) - 1``. This is look-ahead free.

The EUR/USD series is treated as one continuous stream: bars are assumed evenly
spaced and gaps from inactive periods are ignored (used only for annualization).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd

_SECONDS_PER_YEAR = 365.25 * 24 * 3600


class Strategy(Protocol):
    """Minimal strategy interface.

    Implementations map a bars frame (``open, high, low, close, volume`` indexed
    by time) to a target-position series in ``[-1, 1]`` aligned to the same index.
    The value at ``t`` must depend only on data up to and including ``Close(t)``.
    """

    name: str

    def generate_signal(self, bars: pd.DataFrame) -> pd.Series: ...


@dataclass
class BacktestResult:
    """Outcome of a single backtest."""

    returns: pd.Series  # per-bar net strategy returns
    equity: pd.Series  # cumulative equity, starts near 1.0
    position: pd.Series  # effective position held during each bar
    metrics: dict[str, float]


def infer_periods_per_year(index: pd.Index) -> float:
    """Estimate bars-per-year from the (assumed even) bar spacing of the index."""
    if isinstance(index, pd.DatetimeIndex) and len(index) >= 2:
        median_delta = index.to_series().diff().dropna().median()
        seconds = median_delta.total_seconds()
        if seconds and seconds > 0:
            return _SECONDS_PER_YEAR / seconds
    raise ValueError("Cannot infer periods_per_year; pass it explicitly.")


def compute_metrics(
    returns: pd.Series,
    position: pd.Series,
    turnover: pd.Series,
    periods_per_year: float,
) -> dict[str, float]:
    """Core performance metrics for a per-bar net return stream."""
    n = len(returns)
    if n == 0:
        return {}

    total_return = float((1.0 + returns).prod() - 1.0)
    log_growth = float(np.log1p(returns).sum())
    exp_arg = min(log_growth * periods_per_year / n, 700.0)
    ann_return = float(np.expm1(exp_arg))

    std = float(returns.std(ddof=0))
    ann_vol = std * np.sqrt(periods_per_year)
    sharpe = float(returns.mean() / std * np.sqrt(periods_per_year)) if std > 0 else 0.0

    equity = (1.0 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    max_drawdown = float(drawdown.min())

    active = position != 0.0
    hit_rate = float((returns[active] > 0).mean()) if bool(active.any()) else float("nan")
    ann_turnover = float(turnover.sum() * periods_per_year / n)

    return {
        "total_return": total_return,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "hit_rate": hit_rate,
        "ann_turnover": ann_turnover,
        "n_bars": float(n),
    }


def backtest(
    bars: pd.DataFrame,
    signal: pd.Series,
    cost_per_turnover: float = 0.0,
    periods_per_year: float | None = None,
) -> BacktestResult:
    """Run a vectorized backtest of ``signal`` on ``bars``.

    ``cost_per_turnover`` is the cost (in return terms) charged per unit of
    position change, capturing spread + slippage + fees. For example, paying a
    half-spread of ~0.5 bp to flip from flat to fully long costs ``0.00005``.
    """
    signal = signal.reindex(bars.index).clip(-1.0, 1.0)

    bar_ret = bars["open"].shift(-1) / bars["open"] - 1.0  # Open(t) -> Open(t+1)
    position = signal.shift(1).fillna(0.0)  # decided at Close(t-1), live at Open(t)
    turnover = (position - position.shift(1).fillna(0.0)).abs()

    gross = position * bar_ret
    net = gross - turnover * cost_per_turnover

    valid = bar_ret.notna()
    net = net[valid]
    position = position[valid]
    turnover = turnover[valid]

    equity = (1.0 + net).cumprod()
    ppy = periods_per_year if periods_per_year is not None else infer_periods_per_year(bars.index)
    metrics = compute_metrics(net, position, turnover, ppy)

    return BacktestResult(returns=net, equity=equity, position=position, metrics=metrics)
