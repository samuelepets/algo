"""Unit tests for algo_shared.plotting."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from algo_shared.plotting import Trade, plot_trades, save_html


def _make_bars(n: int, step_secs: int = 60) -> tuple:
    ts = np.arange(n, dtype=np.int64) * step_secs
    price = 1.0 + 0.001 * np.sin(np.arange(n, dtype=np.float64) / 5.0)
    open_ = price
    close = price + 0.0005
    high = np.maximum(open_, close) + 0.0003
    low = np.minimum(open_, close) - 0.0003
    return ts, open_, high, low, close


def test_plot_trades_returns_figure() -> None:
    ts, open_, high, low, close = _make_bars(50)
    trades = [
        Trade(entry_ts=int(ts[5]), exit_ts=int(ts[10]), entry_price=close[5],
              exit_price=close[10], is_long=True, pnl=1.0),
        Trade(entry_ts=int(ts[20]), exit_ts=int(ts[25]), entry_price=close[20],
              exit_price=close[25], is_long=False, pnl=-0.5),
    ]
    fig = plot_trades(ts, open_, high, low, close, trades, title="test")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    trace_names = {t.name for t in fig.data}
    assert "Winning trade" in trace_names
    assert "Losing trade" in trace_names
    assert "Entry (long)" in trace_names
    assert "Entry (short)" in trace_names


def test_plot_trades_no_trades() -> None:
    ts, open_, high, low, close = _make_bars(30)
    fig = plot_trades(ts, open_, high, low, close, trades=[])
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1  # candlestick only


def test_plot_trades_with_overlay_and_panel_indicators() -> None:
    ts, open_, high, low, close = _make_bars(60)
    sma = np.convolve(close, np.ones(5) / 5, mode="same")
    adx = np.abs(np.sin(np.arange(60, dtype=np.float64) / 7.0)) * 50.0
    fig = plot_trades(
        ts, open_, high, low, close,
        trades=[],
        overlay_indicators={"SMA": sma},
        panel_indicators={"ADX": adx},
    )
    trace_names = {t.name for t in fig.data}
    assert "SMA" in trace_names
    assert "ADX" in trace_names
    # two rows: price panel + indicator panel
    assert fig.layout.xaxis2 is not None


def test_save_html_writes_file(tmp_path: Path) -> None:
    ts, open_, high, low, close = _make_bars(20)
    trades = [
        Trade(entry_ts=int(ts[2]), exit_ts=int(ts[6]), entry_price=close[2],
              exit_price=close[6], is_long=True, pnl=0.3),
    ]
    fig = plot_trades(ts, open_, high, low, close, trades)
    out = tmp_path / "chart.html"
    save_html(fig, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "plotly" in content.lower()
    assert len(content) > 10_000  # embedded plotly.js, not just a stub
