# Category 5 — Time-Based: Top 10 Strategies

Detailed research document for the **Time-Based** strategy family.
Each strategy is documented with: core hypothesis, indicators and their mechanics,
standard parameters used in practice, entry/exit rules, and a **brute-force
parameter search space** suitable for exhaustive or grid-search optimization over
the `data/bars/` corpus.

All timestamps in this corpus are in **EET (Eastern European Time)**.
Session definitions: Asian 22:00–08:00, London 08:00–16:00, New York 13:00–21:00.
Account for DST shifts when computing precise boundaries across years.

---

## Table of Contents

| # | Strategy | Complexity | Best TF |
|---|---|---|---|
| TB-01 | London Open Momentum | Low | 5-min |
| TB-02 | New York Open Momentum | Low | 5-min |
| TB-03 | London/NY Session Overlap Trade | Medium | 5-min |
| TB-04 | Asian Session Range Fade | Low | 5-min, 15-min |
| TB-05 | Time-of-Day Return Seasonality | Medium | 1-min, 5-min |
| TB-06 | Day-of-Week Bias Filter | Low | Any |
| TB-07 | End-of-Session Momentum Fade | Low | 5-min |
| TB-08 | Session Transition Effect | Medium | 5-min |
| TB-09 | Monday Gap Effect | Low | 5-min |
| TB-10 | First Hour Pattern | Medium | 5-min, 15-min |

---

## TB-01 — London Open Momentum

### Hypothesis

The London session open (08:00 EET) marks the start of the most liquid and
directional period of the Forex trading day. Institutional participation
increases sharply as London desks come online, often establishing a directional
bias for the entire European session. The first 15–30 minutes post-open tends
to have above-average directional momentum that can be captured with a
momentum entry.

### Indicators

- **Session open time:** 08:00 EET (London).
- **Pre-open range:** High and low of the Asian session or a shorter pre-open
  window (e.g. 06:00–08:00 EET).
- **Entry signal:** First close above/below the pre-open range after 08:00 EET.
- **Momentum confirmation (optional):** Current bar's ROC or close above EMA.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Entry window | 08:00–09:30 EET | Only enter signals in this window |
| Pre-open reference | 06:00–08:00 EET range or Asian session range | |
| Stop | Opposite side of pre-open range | |
| Target | 1.0–2.0× pre-open range projected | |
| Max trades | 1 per session | Avoid re-entries after a failed signal |

### Entry Rules

- **Long:** After 08:00 EET, first bar close above the pre-open range high.
- **Short:** First bar close below the pre-open range low.
- Time exit: Close position by 12:00 EET or session-based rule.

### Brute-Force Parameter Search Space

```
pre_open_start   : ["05:00", "06:00", "07:00"]    # EET
open_time        : ["08:00"]                         # London open fixed
entry_window_end : ["09:00", "09:30", "10:00"]     # EET
buffer_atr_mult  : [0.0, 0.05, 0.10, 0.20]
stop_type        : ["opposite_range", "atr_stop"]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_mult      : [1.0, 1.5, 2.0]
time_exit        : ["12:00", "13:00", "16:00"]     # EET
timeframe        : [1min, 5min]
```

### Instrument Suitability

| Instrument | Suitability | Notes |
|---|---|---|
| EURUSD | Very High | London open is the primary driver for EUR pairs |
| XAUUSD | High | Gold is highly active at London open (European time zone) |
| BTCUSD | Medium | 24-h market; London open has some effect but less pronounced |
| XAGUSD | High | Silver follows gold dynamics |

---

## TB-02 — New York Open Momentum

### Hypothesis

The New York session open (13:00 EET) marks the start of the highest-liquidity
period of the trading day — the London/NY overlap. Major economic data releases
(CPI, NFP, FOMC) land at 13:30 or 15:00 EET. Even without major releases, the
NY open produces increased directional momentum as American institutional
participants establish positions.

### Indicators

- **Session open time:** 13:00 EET (New York).
- **Pre-NY range:** High and low of the London morning session (08:00–13:00 EET).
- **Entry:** Breakout above/below pre-NY range in the first 30–60 minutes.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Reference range | 08:00–13:00 EET (London session) |
| Entry window | 13:00–14:00 EET |
| Stop | Opposite side of pre-NY range |
| Target | 1.0–2.0× pre-NY range |
| Time exit | 16:00 or 18:00 EET |

### Brute-Force Parameter Search Space

```
pre_open_start   : ["10:00", "11:00", "12:00"]    # EET
open_time        : ["13:00"]                         # NY open fixed
entry_window_end : ["13:30", "14:00", "14:30"]     # EET
buffer_atr_mult  : [0.0, 0.05, 0.10, 0.20]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_mult      : [1.0, 1.5, 2.0]
time_exit        : ["16:00", "18:00", "21:00"]     # EET
timeframe        : [1min, 5min]
```

### Instrument Suitability

EURUSD and XAUUSD are strongest. NY open is the dominant session for XAUUSD
(gold is heavily traded by New York commodity desks). BTCUSD shows moderate
but real NY open effects.

---

## TB-03 — London/NY Session Overlap Trade

### Hypothesis

The London/NY overlap (13:00–16:00 EET) is the most liquid and volatile period
of the trading week for Forex and metals. Bid-ask spreads narrow, volume peaks,
and directional moves tend to be the largest and most sustained of the day.
Trading only during this overlap window, with any directional strategy, improves
win rate and average profit per trade compared to trading all hours.

### Indicators

- **Overlap window:** 13:00–16:00 EET (London and NY both open).
- **Direction filter:** Use any trend signal (EMA crossover, MACD, SuperTrend)
  but only enter during the overlap window.
- **Exit by:** 16:00 EET (London close) or time-based exit.

### Usage

This strategy is a **time filter wrapper** — apply it around any other strategy:
- Enable entries only between 13:00–16:00 EET.
- Close all positions by 16:00 EET regardless of stop/target.
- Do not carry positions through the London close.

### Brute-Force Parameter Search Space

```
overlap_start    : ["13:00", "13:30"]              # EET
overlap_end      : ["15:30", "16:00", "16:30"]     # EET
exit_method      : ["time_exit", "strategy_exit"]
underlying_signal: ["ema_crossover", "supertrend", "macd", "rsi_momentum"]
timeframe        : [1min, 5min]
```

### Instrument Suitability

EURUSD (highest overlap volume), XAUUSD, XAGUSD. Avoid applying the overlap
filter to BTCUSD where the effect is weaker.

---

## TB-04 — Asian Session Range Fade

### Hypothesis

The Asian session (22:00–08:00 EET) is characteristically low-volume and
range-bound for Forex and metals. Price oscillates within a narrow band
without sustained directional moves. Fading the extremes of the Asian session
range — selling near the Asian high, buying near the Asian low — produces
consistent mean-reversion profits during the Asian hours.

### Indicators

- **Asian high:** Max(High) from 22:00 to current bar time (during Asian session).
- **Asian low:** Min(Low) from 22:00 to current bar time.
- **Mid-range:** `(asian_high + asian_low) / 2`.
- **Signal:** Price near Asian high → short toward mid; near Asian low → long.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Session definition | 22:00–08:00 EET | Asian session |
| Entry proximity | Within 0.25–0.5× ATR of range extreme | |
| Exit | Mid-range or fixed R:R | |
| Stop | 0.5× ATR beyond range extreme | |
| Avoid | Positions open at 08:00 EET (London open volatility) | |

### Brute-Force Parameter Search Space

```
session_start    : ["22:00"]                   # EET, fixed
session_end      : ["07:00", "07:30", "08:00"] # EET — fade only until near end
proximity_atr    : [0.20, 0.30, 0.50]
stop_atr_mult    : [0.5, 1.0]
target           : ["mid_range", "opposite_extreme", "fixed_rr"]
rr_ratio         : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

### Instrument Suitability

EURUSD (very clear Asian consolidation). XAUUSD is moderately active in Asia
due to Asian gold demand. Avoid on BTCUSD (24-h market with no Asian-specific
reduction in activity for crypto).

---

## TB-05 — Time-of-Day Return Seasonality

### Hypothesis

Certain hours of the trading day statistically exhibit higher average returns
or directional bias. These intraday seasonality patterns persist because they
reflect systematic institutional activity cycles (rebalancing, fixing, hedging).
Identifying hours with statistically significant positive or negative average
returns and entering trades timed to those windows provides a structural edge.

### Method

1. Compute the log-return of each 1-minute or 5-minute bar.
2. Group bars by hour-of-day (EET).
3. Compute mean return per hour; test significance with t-test.
4. Identify hours with |mean_return| statistically > 0 (p < 0.05).
5. Enter long/short at the start of "positive" or "negative" hours.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Bar granularity | 1-min, 5-min |
| Significance level | p < 0.05, p < 0.01 |
| Entry | At the start of the significant hour |
| Exit | End of the hour (fixed holding period = 60 bars on 1-min) |
| Training period | 1–3 years of in-sample data |
| Test: walk-forward | Year-over-year to check stability |

### Brute-Force Parameter Search Space

```
bar_size         : ["1min", "5min"]
significance     : [0.01, 0.05, 0.10]
min_years_data   : [1, 2, 3]
holding_bars     : [10, 30, 60]           # number of bars to hold
direction        : ["mean_sign", "prior_day_direction"]
timeframe        : [1min, 5min]
```

> **Non-stationarity warning:** Hour-of-day seasonality is not stable across
> years. Always validate out-of-sample; patterns may shift as market structure
> changes. Walk-forward validation mandatory.

### Instrument Suitability

All instruments; must be computed independently per instrument since session
structures differ significantly between Forex, Metals, and Crypto.

---

## TB-06 — Day-of-Week Bias Filter

### Hypothesis

Certain weekdays exhibit systematic directional bias or volatility patterns.
For Forex, Friday afternoons tend to see position unwinding and lower
volatility; Mondays can show gap effects (especially after weekend news for
Crypto). These patterns are weak signals on their own but can filter other
strategies to improve performance.

### Method

1. Compute daily log-returns.
2. Group by weekday (Monday = 0 through Friday = 4).
3. Test for statistical significance in mean return per weekday.
4. Apply as a binary filter: only enter trades on "good" weekdays for the
   specific instrument.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Granularity | Daily return or intraday hour-of-day within each day |
| Significance | p < 0.05 |
| Application | Filter only (do not trade standalone) |
| Avoid | Holding positions over weekends (gap risk) |

### Known Patterns (to test, not assumed)

| Pattern | Instrument | Status |
|---|---|---|
| Monday reversal (gap fill) | EURUSD | To test |
| Friday afternoon slowdown | EURUSD | To test |
| Weekend gap continuation | BTCUSD | To test — crypto is 24-h |
| Wednesday/Thursday strength | XAUUSD | To test |

### Brute-Force Parameter Search Space

```
training_years   : [1, 2, 3, 5]
significance     : [0.05, 0.10]
filter_mode      : ["exclude_bad_days", "boost_good_days"]
combine_with     : ["ema_crossover", "supertrend", "macd"]
timeframe        : [5min, 15min, 1h]
```

---

## TB-07 — End-of-Session Momentum Fade

### Hypothesis

As the trading session approaches its end (e.g. London close at 16:00 EET),
institutional positions are wound down, causing reversal of intraday directional
moves. The last 30–60 minutes of the London session often reverses the
morning's move. Similarly, the NY close at 21:00 EET tends to see position
squaring. Fading the session's direction in the final hour provides a
time-based mean-reversion trade.

### Indicators

- **Session direction:** Compare current price to session open.
- **Fade signal:** If price is significantly above session open → short; below → long.
- **Entry window:** Last 30–60 minutes before session close.
- **Exit:** Session close (flat).

### Standard Parameters

| Parameter | Common values |
|---|---|
| Session end | 16:00 EET (London), 21:00 EET (NY) |
| Entry window | 30–60 minutes before close |
| Deviation from session open | > 0.5× ATR → enter fade |
| Stop | 1× ATR from entry |
| Target | Session open price |

### Brute-Force Parameter Search Space

```
session_close    : ["16:00", "21:00"]              # EET
entry_minutes_before: [30, 45, 60]
open_deviation_atr: [0.3, 0.5, 0.75, 1.0]
atr_stop_mult    : [0.5, 1.0, 1.5]
target           : ["session_open", "half_deviation"]
timeframe        : [5min, 15min]
```

---

## TB-08 — Session Transition Effect

### Hypothesis

As one session ends and another begins, there is often a brief but reliable
directional impulse as the new session's participants establish positions and
override the prior session's order flow. The Asian-to-London transition
(08:00 EET) and London-to-NY transition (13:00 EET) are the two primary
events. The direction of the impulse at session transition tends to be in
the opposite direction of the prior session's late move (as positions are
squared) or in the direction of the new session's bias.

### Indicators

- **Transition time:** 08:00 EET (Asian → London) and 13:00 EET (London → NY).
- **Prior session late direction:** Last 30 minutes of prior session.
- **Transition signal:** Reversal or continuation at open.
- **Signal type:** The first 5-min bar after transition that exceeds the prior
  session's last bar range.

### Brute-Force Parameter Search Space

```
transition_time  : ["08:00", "13:00"]              # EET
prior_window_min : [15, 30, 60]                    # prior session late bars
signal_type      : ["reversal", "continuation"]
entry_bars_max   : [2, 3, 5]                       # bars after transition to enter
atr_stop_mult    : [0.75, 1.0, 1.5]
rr_ratio         : [1.5, 2.0]
timeframe        : [1min, 5min]
```

---

## TB-09 — Monday Gap Effect

### Hypothesis

For instruments that close on Friday and reopen on Sunday/Monday (Forex reopens
Sunday 22:00 EET; crypto is continuous), weekend gaps can be significant.
Smaller gaps (< 1× ATR) tend to fill within the first few hours of Monday
trading. Larger gaps (> 2× ATR) may continue in the gap direction. The
Monday gap effect provides a systematic entry opportunity at the start of
each trading week.

### Indicators

- **Weekend gap:** `|Open_Monday − Close_Friday|` in pips/ATR units.
- **Gap direction:** Positive = upward; negative = downward.
- **Fill trade:** Fade the gap; target = Friday close.
- **Continuation trade:** Enter in gap direction when gap is large.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Gap detection time | First bar after weekend open | Sunday 22:00 EET for Forex |
| Small gap (fill) | < 0.5–1.0× ATR | Fade back to Friday close |
| Large gap (continue) | > 2.0× ATR | Trade in gap direction |
| Stop | 0.5× ATR beyond gap open | |
| Target | Friday close (fill) or 1× gap size (continue) | |

### Brute-Force Parameter Search Space

```
gap_atr_fill_max  : [0.5, 0.75, 1.0]       # gaps below this → fill trade
gap_atr_cont_min  : [1.5, 2.0, 3.0]        # gaps above this → continuation
mode              : ["fill", "continuation", "both"]
stop_atr_mult     : [0.5, 1.0]
timeframe         : [1min, 5min]
```

### Instrument Suitability

EURUSD (weekend gap common on Forex); XAUUSD (similar session structure).
BTCUSD: no weekend gap as crypto trades continuously, but the "Monday effect"
can still exist as institutional Forex traders return.

---

## TB-10 — First Hour Pattern

### Hypothesis

The first hour of the trading session (e.g. 08:00–09:00 EET for London, or
13:00–14:00 EET for NY) establishes important context for the rest of the
session. The high and low of the first hour act as a micro version of the
opening range. The direction of the first-hour close relative to the
first-hour open (bullish or bearish first hour) has predictive value for
the session's direction.

### Method

1. Define first-hour range: `FH_high = max(High, 08:00–09:00)`,
   `FH_low = min(Low, 08:00–09:00)`.
2. Compute first-hour direction: `FH_direction = sign(Close[09:00] − Open[08:00])`.
3. After 09:00 EET, trade in the direction of `FH_direction` on the first
   pullback to a key level (EMA, VWAP, or FH midpoint).
4. Alternatively, trade the breakout above `FH_high` (long) or below
   `FH_low` (short) after 09:00 EET.

### Brute-Force Parameter Search Space

```
fh_start         : ["08:00", "13:00"]              # EET
fh_end           : ["08:30", "09:00", "09:30"]     # EET
signal_type      : ["fh_direction_pullback", "fh_breakout"]
entry_window     : ["09:00-12:00", "09:00-16:00"]  # valid entry window
atr_stop_mult    : [1.0, 1.5, 2.0]
target_type      : ["fixed_rr", "session_extreme"]
rr_ratio         : [1.5, 2.0]
timeframe        : [5min, 15min]
```

### Instrument Suitability

EURUSD (London first hour: 08:00–09:00 EET); XAUUSD (NY first hour: 13:00–14:00
EET). Instruments with clear session structure benefit most.

---

## Cross-Strategy Considerations

### Session Timing Reference (EET)

| Event | Time (EET) | Notes |
|---|---|---|
| Forex weekend reopen | Sun 22:00 | Monday effect starts here |
| Asian session open | 22:00 | Previous evening |
| Asian session close | 08:00 | |
| London session open | 08:00 | Most important Forex transition |
| London/NY overlap start | 13:00 | Peak liquidity |
| London close | 16:00 | Session-end effects |
| NY close | 21:00 | Session-end effects |
| Crypto | 24/7 | No natural session; use UTC 00:00 as reset |

> All corpus timestamps are EET. DST changes (last Sunday of March and October
> in Europe) affect the offset to UTC. For multi-year backtests, handle DST
> transitions explicitly.

### Time-Based Strategies as Filters

Most time-based strategies are most powerful when combined with other signals:

| Role | Use case |
|---|---|
| Entry window | Only take trend signals between 08:00–09:30 EET |
| Session filter | Disable trading during Asian session for trend strategies |
| Day filter | Skip Fridays after 14:00 EET (position squaring) |
| Boost | Increase position size when time seasonality aligns with signal |

### Suggested Evaluation Priority

| Priority | Strategy | Reason |
|---|---|---|
| 1 | TB-01 London Open Momentum | Strongest and most consistent time effect |
| 2 | TB-02 NY Open Momentum | Second strongest; major economic data timing |
| 3 | TB-04 Asian Session Fade | Consistent ranging behavior; good for mean-reversion |
| 4 | TB-03 London/NY Overlap Filter | Improves any strategy by restricting to peak hours |
| 5 | TB-05 Time-of-Day Seasonality | Data-driven; validate carefully |
| 6 | TB-09 Monday Gap | Systematic edge at week start |
| 7 | TB-10 First Hour Pattern | Session structure-based; early direction bias |
| 8 | TB-06 Day-of-Week Filter | Weak standalone; best as add-on filter |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
