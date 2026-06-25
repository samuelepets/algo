"""Unit tests for algo_shared.metrics."""

from __future__ import annotations

import math

import numpy as np
import pytest

from algo_shared.metrics import Metrics, compute_metrics


def _trades(*values: float) -> tuple[np.ndarray, int]:
    arr = np.array(values, dtype=np.float64)
    buf = np.empty(len(arr) + 10, dtype=np.float64)
    buf[: len(arr)] = arr
    return buf, len(arr)


def test_zero_trades() -> None:
    buf, n = _trades()
    sharpe, pf, mdd, ret, nt = compute_metrics(buf, 0, 0, 1_000_000)
    assert nt == 0
    assert sharpe == 0.0


def test_one_trade() -> None:
    buf, n = _trades(1.0)
    sharpe, pf, mdd, ret, nt = compute_metrics(buf, n, 0, 1_000_000)
    assert nt == 1
    assert sharpe == 0.0


def test_all_wins_profit_factor_inf() -> None:
    buf, n = _trades(1.0, 2.0, 1.5)
    _, pf, _, _, _ = compute_metrics(buf, n, 0, int(365.25 * 24 * 3600))
    assert math.isinf(pf)


def test_all_losses_profit_factor_zero() -> None:
    buf, n = _trades(-1.0, -2.0)
    _, pf, _, ret, _ = compute_metrics(buf, n, 0, int(365.25 * 24 * 3600))
    assert pf == 0.0
    assert ret == pytest.approx(-3.0)


def test_total_return_sum() -> None:
    trades_vals = (1.0, -0.5, 2.0, -1.0, 0.5)
    buf, n = _trades(*trades_vals)
    _, _, _, ret, nt = compute_metrics(buf, n, 0, int(365.25 * 24 * 3600))
    assert nt == len(trades_vals)
    assert ret == pytest.approx(sum(trades_vals))


def test_max_drawdown_known() -> None:
    # equity curve: +2, -3 -> drawdown of 3 from peak of 2
    buf, n = _trades(2.0, -3.0)
    _, _, mdd, _, _ = compute_metrics(buf, n, 0, int(365.25 * 24 * 3600))
    assert mdd == pytest.approx(3.0)


def test_profit_factor_ratio() -> None:
    buf, n = _trades(2.0, -1.0)
    _, pf, _, _, _ = compute_metrics(buf, n, 0, int(365.25 * 24 * 3600))
    assert pf == pytest.approx(2.0)


def test_metrics_dataclass() -> None:
    m = Metrics(sharpe=1.5, profit_factor=2.0, max_drawdown_r=0.5, total_return=3.0, n_trades=10)
    assert m.sharpe == 1.5
    assert m.n_trades == 10
