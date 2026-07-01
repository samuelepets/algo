import numpy as np
import pandas as pd

from strategies import bollinger_fade_positions, ema_crossover_positions, strategy_returns


def series(values) -> pd.Series:
    return pd.Series(
        values, index=pd.date_range("2025-01-01", periods=len(values), freq="1h"), dtype=float
    )


def test_ema_crossover_long_in_uptrend_short_in_downtrend():
    up = series(np.linspace(1.0, 1.2, 200))
    assert (ema_crossover_positions(up).iloc[60:] == 1.0).all()
    down = series(np.linspace(1.2, 1.0, 200))
    assert (ema_crossover_positions(down).iloc[60:] == -1.0).all()


def test_bollinger_fade_enters_short_on_spike_and_exits_at_mid():
    # Flat series, one upward spike: fade should go short, then exit once
    # price is back at/below the rolling mean.
    values = np.full(60, 1.0)
    values[40] = 1.05
    pos = bollinger_fade_positions(series(values), period=20, k=2.0)
    assert pos.iloc[40] == -1.0
    assert pos.iloc[41] == 0.0  # back at mid -> flat
    assert (pos.iloc[:40] == 0.0).all()


def test_strategy_returns_uses_next_bar_and_charges_turnover():
    close = series([1.0, 1.0, 1.1, 1.21])
    pos = series([0.0, 1.0, 1.0, 1.0])
    r = strategy_returns(close, pos, half_spread_pips=0.0)
    # Position opened at bar 1 earns bar 2's and bar 3's returns only.
    assert r.iloc[:2].fillna(0).eq(0).all()
    assert np.isclose(r.iloc[2], np.log(1.1 / 1.0))
    assert np.isclose(r.iloc[3], np.log(1.21 / 1.1))
    # With costs, the entry bar is charged once per unit of position change.
    r_cost = strategy_returns(close, pos, half_spread_pips=1.0)
    assert np.isclose((r - r_cost).iloc[2], 1e-4 / 1.1)
    assert np.isclose((r - r_cost).iloc[3], 0.0)
