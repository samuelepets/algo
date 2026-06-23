# Category 7 — Multi-Timeframe (MTF): Top 10 Strategies

Detailed research document for the **Multi-Timeframe** strategy family.
Each strategy is documented with: core hypothesis, indicators and their mechanics,
standard parameters used in practice, entry/exit rules, and a **brute-force
parameter search space** suitable for exhaustive or grid-search optimization over
the `data/bars/` corpus.

MTF strategies are built by resampling 1-minute bars into higher timeframes
(5 min, 15 min, 1 h, 4 h) and combining signals across timeframe levels.
All resampling must be done without look-ahead: a 15-min bar at time T is
only complete at T+14 minutes on the 1-min base.

---

## Table of Contents

| # | Strategy | Complexity | Entry TF / Filter TF |
|---|---|---|---|
| MT-01 | Higher-TF Trend + Lower-TF EMA Entry | Medium | 1-min entry / 15-min, 1-h filter |
| MT-02 | Multi-TF Confluence Signal | High | 5-min entry / 15-min + 1-h filter |
| MT-03 | HTF Support/Resistance + LTF Entry | Medium | 5-min entry / 1-h, 4-h filter |
| MT-04 | MTF RSI Alignment | Low | 5-min entry / 15-min + 1-h filter |
| MT-05 | Daily Trend + Intraday Signal | Low | 5-min entry / 1-h daily filter |
| MT-06 | MTF Ichimoku Cloud | High | 15-min entry / 1-h filter |
| MT-07 | MTF MACD Alignment | Medium | 5-min entry / 15-min + 1-h filter |
| MT-08 | Weekly Bias + Daily + 1H Trigger | High | 15-min entry / 1-h + daily filter |
| MT-09 | MTF Bollinger Band Position | Medium | 5-min entry / 15-min filter |
| MT-10 | MTF Volume Confirmation | Medium | 5-min entry / 15-min filter |

---

## MT-01 — Higher-TF Trend + Lower-TF EMA Entry

### Hypothesis

The most common and robust MTF framework: determine the prevailing trend
direction on a higher timeframe (HTF) and only take signals in that direction
on the lower timeframe (LTF). By filtering out counter-trend entries, the
approach eliminates a large fraction of losing trades while preserving most
winning ones. The HTF acts as a trend direction gate; the LTF provides precise
entry timing.

### Structure

- **HTF (15-min or 1-h):** EMA(200) or EMA(50) slope determines trend direction.
  Price above HTF EMA → bull regime; below → bear regime.
- **LTF (1-min or 5-min):** EMA crossover (e.g. EMA(9)/EMA(21)) as entry
  trigger. Only take long signals when HTF = bull; short when HTF = bear.

### Standard Parameters

| Layer | Timeframe | Indicator | Signal |
|---|---|---|---|
| HTF trend | 15-min or 1-h | EMA(200) | Price above = bull |
| LTF entry | 1-min or 5-min | EMA(9)/EMA(21) | Crossover in trend direction |
| Stop | LTF | ATR(14) | 1.0–2.0× ATR below/above entry |
| Target | LTF | R:R | 1.5:1 to 2.5:1 |

### Entry Rules

- **Long:** HTF price above EMA(200) AND LTF EMA(9) crosses above EMA(21).
- **Short:** HTF price below EMA(200) AND LTF EMA(9) crosses below EMA(21).

### Brute-Force Parameter Search Space

```
htf              : ["15min", "1h", "4h"]
htf_ema          : [50, 100, 200]
ltf              : ["1min", "5min"]
ltf_fast_ema     : [5, 8, 9, 12]
ltf_slow_ema     : [18, 20, 21, 26]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0, 2.5]
```

Total combinations: ~3 × 3 × 2 × 4 × 4 × 3 × 3 = 2,592 per instrument.

### Instrument Suitability

All instruments. This is the foundational MTF framework. Start with
EURUSD (15-min HTF, 5-min LTF) and BTCUSD (1-h HTF, 5-min LTF).

---

## MT-02 — Multi-TF Confluence Signal

### Hypothesis

Requiring the same signal type to appear on multiple timeframes simultaneously
dramatically reduces false positives at the cost of lower trade frequency.
The confluence requirement ensures entries only occur when the trend is aligned
across short, medium, and long-term views — a condition associated with the
strongest and most persistent moves.

### Structure

- **TF1 (5-min):** Primary entry signal (e.g. RSI oversold + EMA bullish).
- **TF2 (15-min):** Secondary confirmation (e.g. price above EMA(50), RSI > 50).
- **TF3 (1-h):** Macro trend filter (e.g. price above EMA(200)).
- **Confluent long:** All three conditions bullish simultaneously.

### Standard Parameters

| Timeframe | Condition |
|---|---|
| 5-min (LTF) | Entry trigger: EMA cross, RSI level, candlestick pattern |
| 15-min (MTF) | Trend confirmation: price above EMA(50) |
| 1-h (HTF) | Macro direction: price above EMA(200) |
| Stop | 1.5–2.0× ATR on LTF |
| Target | 2.0–3.0:1 R:R (low frequency → higher R:R required) |

### Brute-Force Parameter Search Space

```
htf              : ["1h", "4h"]
htf_ema          : [100, 200]
mtf              : ["15min", "30min"]
mtf_ema          : [50, 100]
ltf              : ["5min"]
ltf_signal       : ["ema_cross", "rsi_level", "supertrend"]
required_tf_count: [2, 3]       # require 2 or all 3 TF confirmations
atr_stop_mult    : [1.5, 2.0]
rr_ratio         : [2.0, 2.5, 3.0]
```

### Notes

Very low trade frequency. Expect fewer than 1–2 trades per day per instrument.
High selectivity means out-of-sample performance is more stable.

---

## MT-03 — HTF Support/Resistance + LTF Entry

### Hypothesis

Support and resistance levels identified on higher timeframes (1-h or 4-h)
are far more significant than LTF S/R levels because they reflect the
decisions of longer-horizon participants. When a 1-h or 4-h S/R level is
approached on the LTF chart, a confirmation entry (bounce pattern, pin bar,
inside bar) on the 5-min chart provides a high-quality entry with a stop
just beyond the HTF level.

### Structure

- **HTF S/R detection:** Swing highs/lows on 1-h or 4-h bars (N-bar lookback).
- **LTF proximity:** 5-min price approaches within ATR(14) of HTF S/R.
- **LTF confirmation:** Bounce candle (pin bar, engulfing) on 5-min chart.
- **Entry:** On confirmation candle close.
- **Stop:** Just beyond the HTF S/R level (0.5× ATR buffer).
- **Target:** Next HTF S/R level or 2:1 R:R.

### Brute-Force Parameter Search Space

```
htf              : ["1h", "4h"]
htf_swing_lookback: [5, 10, 20]       # bars for HTF swing detection
proximity_atr    : [0.5, 1.0, 1.5]   # proximity to HTF level
ltf              : ["5min"]
ltf_pattern      : ["pin_bar", "engulfing", "any_reversal"]
htf_level_type   : ["swing_hl", "round_number", "both"]
atr_stop_mult    : [0.5, 1.0]
target_type      : ["next_htf_level", "fixed_rr"]
rr_ratio         : [1.5, 2.0, 2.5]
```

---

## MT-04 — MTF RSI Alignment

### Hypothesis

RSI alignment across timeframes provides a momentum confirmation that is both
stronger and more selective than single-TF RSI. When RSI on the 5-min, 15-min,
and 1-h charts are all above 50 (bullish momentum) simultaneously, the
probability of a sustained upward move is significantly higher than when only
one TF shows bullish RSI.

### Structure

- **HTF RSI (1-h):** RSI(14) > 50 → macro bullish momentum.
- **MTF RSI (15-min):** RSI(14) > 50 → intermediate bullish.
- **LTF RSI (5-min):** RSI(14) crosses above 50 (or exits oversold zone < 30)
  → entry trigger.
- **Entry:** LTF RSI crosses 50 upward AND both higher TF RSIs > 50.

### Brute-Force Parameter Search Space

```
htf              : ["1h", "4h"]
htf_rsi_period   : [14]
htf_rsi_threshold: [50, 55]
mtf              : ["15min", "30min"]
mtf_rsi_period   : [14]
mtf_rsi_threshold: [50, 55]
ltf              : ["5min"]
ltf_rsi_period   : [7, 10, 14]
ltf_rsi_trigger  : ["cross_50", "exit_oversold"]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0, 2.5]
```

---

## MT-05 — Daily Trend + Intraday Signal

### Hypothesis

The daily trend (derived from 1-h bars spanning the full day) provides the
strongest context for intraday trading decisions. When the day's trend is up
(e.g. price above the 20-day EMA equivalent on 1-h bars), only long signals
are taken during the intraday session. This simple two-layer framework
(daily direction + intraday trigger) dramatically reduces counter-trend losses.

### Structure

- **Daily proxy (1-h bars):** EMA(24) on 1-h bars ≈ 24-hour smoothing.
  Price above EMA(24) on 1-h → daily uptrend.
- **Intraday entry (5-min):** Any signal type (EMA cross, SuperTrend, MACD,
  ORB, etc.) in the direction of the daily trend.

### Brute-Force Parameter Search Space

```
daily_ema_1h     : [20, 24, 48]            # periods on 1-h bars
intraday_ltf     : ["5min", "15min"]
intraday_signal  : ["ema_cross", "supertrend", "macd", "orb"]
session_filter   : ["london_ny_only", "all_sessions"]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0, 2.5]
```

---

## MT-06 — MTF Ichimoku Cloud

### Hypothesis

Ichimoku Cloud on the 1-h chart defines the major trend structure (price above
cloud = bull, below = bear). When the 15-min chart also shows price above the
cloud, the intermediate trend is aligned. A TK cross on the 5-min or 15-min
chart in the direction of the 1-h cloud provides the entry trigger. This
multi-layer Ichimoku approach is used by many professional Forex traders.

### Structure

- **HTF (1-h):** Price above 1-h cloud → bull. TK cross direction on 1-h.
- **LTF (15-min):** Price above 15-min cloud → intermediate bull.
- **Entry (15-min or 5-min):** TK cross in bullish direction.
- **Stop:** Kijun-sen of entry TF.
- **Target:** 2:1 R:R or upper cloud edge.

### Brute-Force Parameter Search Space

```
htf              : ["1h", "4h"]
ltf              : ["5min", "15min"]
ichimoku_fast    : [7, 9, 10]
ichimoku_slow    : [22, 26, 30]
ichimoku_span    : [44, 52, 60]
signal_type      : ["tk_cross", "cloud_breakout", "tk_above_cloud"]
stop_type        : ["kijun", "cloud_bottom", "atr_stop"]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0, 2.5]
```

---

## MT-07 — MTF MACD Alignment

### Hypothesis

MACD alignment across two timeframes provides strong momentum confirmation.
When the 1-h MACD histogram is positive and rising (macro bullish momentum)
and the 15-min or 5-min MACD line crosses above its signal line (micro
entry), the probability of a sustained directional move is significantly
higher than either signal alone.

### Structure

- **HTF (1-h):** MACD histogram > 0 AND rising (bar-over-bar increase).
- **LTF (15-min or 5-min):** MACD line crosses above signal line.
- **Entry:** LTF MACD bullish cross while HTF histogram is positive.
- **Stop:** Below LTF swing low or ATR stop.

### Brute-Force Parameter Search Space

```
htf              : ["1h", "4h"]
htf_macd         : [(12,26,9), (8,21,9)]
htf_hist_cond    : ["positive", "positive_and_rising"]
ltf              : ["5min", "15min"]
ltf_macd         : [(8,21,9), (5,35,5), (12,26,9)]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0, 2.5]
```

---

## MT-08 — Weekly Bias + Daily + 1H Trigger

### Hypothesis

A three-level MTF hierarchy — weekly direction, daily structure, intraday
entry — mirrors how institutional traders actually approach markets. The
weekly bias (computed from the last 5 trading days of 1-h data) provides the
broadest context. Daily structure (prior day high/low, whether day is above
weekly VWAP) narrows the direction. A 1-h pattern or breakout triggers the
entry.

### Structure

- **Weekly bias:** Price above 5-day rolling EMA on 1-h bars → bull week.
- **Daily structure:** Price above prior day high → bullish day.
- **1-h entry:** EMA crossover, candlestick pattern, or S/R bounce on 1-h.
- **Execution:** Enter on 5-min or 15-min bar for better fill.

### Brute-Force Parameter Search Space

```
weekly_ema_1h    : [100, 120]          # 5 days × 24h = 120 on 1-h bars
daily_condition  : ["above_prior_high", "above_prior_close", "above_daily_ema"]
daily_ema_period : [5, 10, 20]         # on 1-h bars
htf_entry_tf     : ["1h"]
htf_signal       : ["ema_cross", "sr_bounce", "candle_pattern"]
execution_tf     : ["5min", "15min"]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [2.0, 2.5, 3.0]
```

### Notes

Lowest trade frequency of all MTF strategies. The three-filter requirement
produces very few trades but potentially very high quality. Minimum 50 trades
in backtest period required for statistical significance.

---

## MT-09 — MTF Bollinger Band Position

### Hypothesis

The position of price relative to Bollinger Bands on the higher timeframe
provides a powerful context filter for LTF entries. When price is in the
upper half of the 1-h Bollinger Bands (above the 1-h midband), it is in a
bullish regime; in the lower half (below 1-h midband), bearish. Taking only
LTF long signals when HTF price is in the upper BB half dramatically reduces
counter-trend fade losses.

### Structure

- **HTF (1-h):** Bollinger Band position. `%B > 0.5` (above midband) → bull.
- **LTF (5-min):** Entry signal in direction of HTF BB position.
- **%B formula:** `(Close − lower) / (upper − lower)`.

### Brute-Force Parameter Search Space

```
htf              : ["1h", "4h"]
htf_bb_period    : [20, 30, 50]
htf_bb_sigma     : [2.0, 2.5]
htf_bb_threshold : [0.5, 0.55, 0.60]    # %B above this = bull regime
ltf              : ["5min", "15min"]
ltf_signal       : ["ema_cross", "supertrend", "rsi_exit_oversold"]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0, 2.5]
```

---

## MT-10 — MTF Volume Confirmation

### Hypothesis

A trend signal on the LTF is more reliable when confirmed by above-average
volume on the HTF bar that contains the LTF entry. A 15-min bar with volume
> 1.5× its rolling average and a bullish close (strong buying) is more
credible institutional commitment than a low-volume 15-min bar showing the
same price action.

### Structure

- **HTF (15-min):** Volume > N× rolling average AND bullish bar direction.
- **LTF (5-min):** Entry signal in same direction as HTF volume bar.

> **Volume caveat:** Volume in this corpus is tick-volume (number of ticks per
> bar), not notional traded volume. Tick-volume is a reasonable proxy for
> activity level but may reflect broker-specific data artifacts. Validate
> per-instrument before relying on this strategy.

### Brute-Force Parameter Search Space

```
htf              : ["15min", "1h"]
volume_window    : [20, 50, 100]         # bars for rolling volume average
volume_mult      : [1.5, 2.0, 2.5, 3.0] # required spike multiplier
volume_bar_direction: ["same_as_ltf", "any"]
ltf              : ["1min", "5min"]
ltf_signal       : ["ema_cross", "supertrend", "macd_cross"]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0, 2.5]
```

---

## Cross-Strategy Considerations

### Resampling Without Look-Ahead

When resampling 1-min bars to higher timeframes, a bar is only "complete"
and usable at the start of the next bar. For example, a 15-min bar starting
at 09:00 EET is completed at 09:15 EET. Never use incomplete higher-TF bars
for signal generation. In code:

```python
# Correct: resample and shift by 1 to get the last COMPLETE bar's values
htf_close = df_1min.resample("15T").last().shift(1)

# Wrong: using df_1min.resample("15T").last() directly — includes current
# incomplete bar
```

### HTF Indicator Computation

Precompute all HTF indicators on the resampled series, then align back to the
1-min or 5-min base using forward-fill. This is more efficient than
recomputing HTF indicators at every LTF bar.

### Performance Hierarchy

In general (validated across TF research):

| HTF | LTF | Balance |
|---|---|---|
| 4-h | 1-h | Too slow for intraday; better for swing |
| 1-h | 15-min | Good balance; reliable signals |
| 1-h | 5-min | Most common professional intraday combination |
| 15-min | 5-min | More signals, more noise |
| 15-min | 1-min | Very high frequency; transaction costs bite hard |

### Suggested Evaluation Priority

| Priority | Strategy | Reason |
|---|---|---|
| 1 | MT-01 HTF Trend + LTF EMA | Foundation strategy; well-documented edge |
| 2 | MT-05 Daily + Intraday | Simplest multi-layer; easy to implement |
| 3 | MT-04 MTF RSI Alignment | Intuitive; effective momentum confirmation |
| 4 | MT-03 HTF S/R + LTF Entry | High R:R; institutional level confluence |
| 5 | MT-07 MTF MACD Alignment | Strong momentum confirmation |
| 6 | MT-09 MTF BB Position | Regime context from BB position |
| 7 | MT-02 Multi-TF Confluence | Highest quality but very low frequency |
| 8 | MT-06 MTF Ichimoku | Complete system; well-proven in Forex |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
