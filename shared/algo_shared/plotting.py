"""Interactive price/indicator/trade visualization.

Renders an OHLC candlestick chart with optional overlay indicators (plotted on
the price panel, e.g. moving averages or bands) and panel indicators (plotted
in a separate sub-panel with its own scale, e.g. ADX or ATR), plus a set of
trades marked with entry/exit points, a connecting line, and win/loss coloring.

Built on Plotly so pan/zoom/hover come for free via the standard modebar and
mouse drag; call :func:`save_html` to write a standalone, offline-viewable
file (Plotly.js is embedded, no CDN/network access needed to open it).

Timestamp convention matches ``algo_shared.data``: ``ts`` arrays are epoch
seconds, naive labels treated as UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_WIN_COLOR = "#2ca02c"
_LOSS_COLOR = "#d62728"
_LONG_COLOR = "#1f77b4"
_SHORT_COLOR = "#ff7f0e"


@dataclass(frozen=True)
class Trade:
    """One round-trip trade to mark on the chart.

    ``entry_ts``/``exit_ts`` are epoch seconds. ``pnl`` drives win/loss
    coloring — sign is all that matters (R-multiple, price delta, or account
    currency, caller's choice); its value is shown in the hover text.
    """

    entry_ts: int
    exit_ts: int
    entry_price: float
    exit_price: float
    is_long: bool
    pnl: float


def _epoch_to_datetime64(values: np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype="int64").astype("datetime64[s]")


def plot_trades(
    ts: np.ndarray,
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    trades: list[Trade],
    overlay_indicators: dict[str, np.ndarray] | None = None,
    panel_indicators: dict[str, np.ndarray] | None = None,
    title: str = "Trades",
) -> go.Figure:
    """Build an interactive figure: candlesticks + indicators + trade markers.

    ``overlay_indicators`` are drawn on the price panel (must share ``ts``'s
    alignment, e.g. a Bollinger midline/bands). ``panel_indicators`` are drawn
    in a second, independently-scaled sub-panel below (e.g. ADX). Both are
    optional; pass ``{}`` or ``None`` to omit.
    """
    overlay_indicators = overlay_indicators or {}
    panel_indicators = panel_indicators or {}
    x = _epoch_to_datetime64(ts)

    has_panel = len(panel_indicators) > 0
    if has_panel:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.75, 0.25],
            vertical_spacing=0.03,
        )
    else:
        fig = make_subplots(rows=1, cols=1)

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=open_,
            high=high,
            low=low,
            close=close,
            name="Price",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    for name, values in overlay_indicators.items():
        fig.add_trace(
            go.Scatter(x=x, y=values, name=name, mode="lines", line=dict(width=1.2)),
            row=1,
            col=1,
        )

    for name, values in panel_indicators.items():
        fig.add_trace(
            go.Scatter(x=x, y=values, name=name, mode="lines", line=dict(width=1.2)),
            row=2,
            col=1,
        )

    _add_trade_traces(fig, trades, row=1, col=1)

    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        dragmode="zoom",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=80, b=40, l=60, r=20),
    )
    if has_panel:
        fig.update_xaxes(rangeslider_visible=False, row=2, col=1)

    return fig


def _add_trade_traces(fig: go.Figure, trades: list[Trade], row: int, col: int) -> None:
    win_x: list = []
    win_y: list = []
    loss_x: list = []
    loss_y: list = []
    entry_long_x: list = []
    entry_long_y: list = []
    entry_long_text: list = []
    entry_short_x: list = []
    entry_short_y: list = []
    entry_short_text: list = []
    exit_win_x: list = []
    exit_win_y: list = []
    exit_win_text: list = []
    exit_loss_x: list = []
    exit_loss_y: list = []
    exit_loss_text: list = []

    for tr in trades:
        entry_x = _epoch_to_datetime64(np.array([tr.entry_ts]))[0]
        exit_x = _epoch_to_datetime64(np.array([tr.exit_ts]))[0]
        is_win = tr.pnl >= 0.0
        side = "LONG" if tr.is_long else "SHORT"
        result = "WIN" if is_win else "LOSS"

        if is_win:
            win_x += [entry_x, exit_x, None]
            win_y += [tr.entry_price, tr.exit_price, None]
        else:
            loss_x += [entry_x, exit_x, None]
            loss_y += [tr.entry_price, tr.exit_price, None]

        entry_text = f"{side} entry<br>price={tr.entry_price:.5f}<br>pnl={tr.pnl:+.3f}"
        if tr.is_long:
            entry_long_x.append(entry_x)
            entry_long_y.append(tr.entry_price)
            entry_long_text.append(entry_text)
        else:
            entry_short_x.append(entry_x)
            entry_short_y.append(tr.entry_price)
            entry_short_text.append(entry_text)

        exit_text = f"{side} exit ({result})<br>price={tr.exit_price:.5f}<br>pnl={tr.pnl:+.3f}"
        if is_win:
            exit_win_x.append(exit_x)
            exit_win_y.append(tr.exit_price)
            exit_win_text.append(exit_text)
        else:
            exit_loss_x.append(exit_x)
            exit_loss_y.append(tr.exit_price)
            exit_loss_text.append(exit_text)

    if win_x:
        fig.add_trace(
            go.Scatter(
                x=win_x, y=win_y, mode="lines", name="Winning trade",
                line=dict(color=_WIN_COLOR, width=1.5, dash="dot"),
                hoverinfo="skip",
            ),
            row=row, col=col,
        )
    if loss_x:
        fig.add_trace(
            go.Scatter(
                x=loss_x, y=loss_y, mode="lines", name="Losing trade",
                line=dict(color=_LOSS_COLOR, width=1.5, dash="dot"),
                hoverinfo="skip",
            ),
            row=row, col=col,
        )
    if entry_long_x:
        fig.add_trace(
            go.Scatter(
                x=entry_long_x, y=entry_long_y, mode="markers", name="Entry (long)",
                marker=dict(symbol="triangle-up", size=9, color=_LONG_COLOR),
                text=entry_long_text, hoverinfo="text+x",
            ),
            row=row, col=col,
        )
    if entry_short_x:
        fig.add_trace(
            go.Scatter(
                x=entry_short_x, y=entry_short_y, mode="markers", name="Entry (short)",
                marker=dict(symbol="triangle-down", size=9, color=_SHORT_COLOR),
                text=entry_short_text, hoverinfo="text+x",
            ),
            row=row, col=col,
        )
    if exit_win_x:
        fig.add_trace(
            go.Scatter(
                x=exit_win_x, y=exit_win_y, mode="markers", name="Exit (win)",
                marker=dict(symbol="circle", size=7, color=_WIN_COLOR,
                             line=dict(width=1, color="white")),
                text=exit_win_text, hoverinfo="text+x",
            ),
            row=row, col=col,
        )
    if exit_loss_x:
        fig.add_trace(
            go.Scatter(
                x=exit_loss_x, y=exit_loss_y, mode="markers", name="Exit (loss)",
                marker=dict(symbol="x", size=7, color=_LOSS_COLOR,
                             line=dict(width=1, color="white")),
                text=exit_loss_text, hoverinfo="text+x",
            ),
            row=row, col=col,
        )


def save_html(fig: go.Figure, path: Path) -> None:
    """Write a standalone HTML file with Plotly.js embedded (no network needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(path), include_plotlyjs=True, full_html=True)
