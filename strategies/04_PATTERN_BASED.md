# Category 4 — Pattern-Based: Top 20 Strategies

Detailed research document for the **Pattern-Based** strategy family.
Each strategy is documented with: core hypothesis, indicators and their mechanics,
standard parameters used in practice, entry/exit rules, and a **brute-force
parameter search space** suitable for exhaustive or grid-search optimization over
the `data/bars/` corpus.

All strategies operate on 1-minute bars or on bars resampled from them
(5 min, 15 min, 1 h). See `CATEGORIES.md` for context.

---

## Table of Contents

| # | Strategy | Complexity | Best TF |
|---|---|---|---|
| PB-01 | Bullish/Bearish Engulfing | Low | 5-min, 15-min |
| PB-02 | Pin Bar (Hammer / Shooting Star) | Low | 5-min, 15-min |
| PB-03 | Inside Bar Breakout | Low | 5-min, 15-min |
| PB-04 | Morning Star / Evening Star | Medium | 15-min, 1-h |
| PB-05 | Doji Reversal | Low | 5-min, 15-min |
| PB-06 | Three Bar Reversal (3-Bar Pattern) | Low | 5-min, 15-min |
| PB-07 | Head & Shoulders Pattern | High | 15-min, 1-h |
| PB-08 | Double Top / Double Bottom | Medium | 15-min, 1-h |
| PB-09 | Triangle Breakout | Medium | 15-min, 1-h |
| PB-10 | Bull/Bear Flag Continuation | Medium | 5-min, 15-min |
| PB-11 | Support & Resistance Bounce | Medium | 5-min, 15-min |
| PB-12 | Round Number (Psychological Level) Reaction | Low | 5-min, 15-min |
| PB-13 | Prior Session High/Low Reaction | Low | 5-min, 15-min |
| PB-14 | Fair Value Gap (FVG) Fill | Medium | 1-min, 5-min |
| PB-15 | Order Block Reaction | High | 5-min, 15-min |
| PB-16 | Liquidity Sweep + Reversal | High | 5-min, 15-min |
| PB-17 | Breaker Block | High | 5-min, 15-min |
| PB-18 | Swing High/Low Break Continuation | Medium | 5-min, 15-min |
| PB-19 | Wedge Pattern Breakout | Medium | 15-min, 1-h |
| PB-20 | Cup and Handle Continuation | High | 15-min, 1-h |

---

## PB-01 — Bullish/Bearish Engulfing

### Hypothesis

A bullish engulfing candle has a body that completely engulfs the prior bar's
body with a bullish close — indicating that buyers overwhelmed sellers decisively
in a single bar. At support levels or after a downtrend, this pattern signals
a high-probability reversal. The bearish engulfing is the inverse.

### Indicators

- **Bullish engulfing:** `Open[0] < Close[−1] AND Close[0] > Open[−1] AND
  body[0] > body[−1]` where bar[0] is bullish and bar[−1] is bearish.
- **Bearish engulfing:** Inverse.
- **Context filter:** Pattern at a support/resistance level or after N-bar
  directional move adds signal quality.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Body ratio | Body[0] / Body[−1] > 1.0 (engulfs) | Strict definition |
| Context bars | 3–10 bars of prior directional move | Counts a prior trend |
| Wick-to-body ratio | Wick < 50% of body (optional) | Reduces noise |
| Stop | Below/above the engulfing bar |
| Target | 2:1 R:R or next S/R level |

### Brute-Force Parameter Search Space

```
body_ratio_min   : [1.0, 1.2, 1.5]        # engulfing body is X× prior body
prior_trend_bars : [3, 5, 10]              # N bars of same-direction move required
context_filter   : ["none", "at_ema", "at_sr"]
atr_stop_mult    : [0.5, 1.0, 1.5]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

### Instrument Suitability

All instruments. Most reliable at key S/R levels or after a defined trend.
On 1-min bars, engulfing patterns are extremely noisy; 5-min or 15-min bars
strongly recommended.

---

## PB-02 — Pin Bar (Hammer / Shooting Star)

### Hypothesis

A pin bar features a long wick and a small body at the opposite end, indicating
that price was sharply rejected at an extreme. A bullish pin (hammer) has a long
lower wick — buyers rejected the lows aggressively. A bearish pin (shooting star)
has a long upper wick. At key support/resistance, these patterns signal high-
probability reversals.

### Indicators

- **Wick-to-body ratio:** `wick_length / body_size > threshold`.
- **Body position:** Body in top 30% of bar (bullish pin) or bottom 30% (bearish).
- **Wick direction:** Long lower wick → bullish pin; long upper wick → bearish.
- **Rejection wick:** `wick / total_range > 0.5` — wick dominates the bar.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Wick-to-body ratio | > 2.0 | Long wick must be at least 2× body |
| Body/range ratio | < 0.30 | Body is small |
| Wick/range ratio | > 0.50 | Wick is the dominant feature |
| Context filter | At EMA, at S/R, round number | Context improves quality |
| Stop | Beyond pin bar wick extreme | |
| Target | 2:1 R:R or prior swing |

### Brute-Force Parameter Search Space

```
wick_body_ratio  : [1.5, 2.0, 2.5, 3.0]
body_range_max   : [0.25, 0.30, 0.40]     # body size relative to bar range
wick_range_min   : [0.40, 0.50, 0.60]     # wick relative to bar range
context_filter   : ["none", "at_ema", "at_sr", "at_round_number"]
atr_stop_mult    : [0.5, 1.0, 1.5]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

---

## PB-03 — Inside Bar Breakout (Pattern Variant)

### Hypothesis

An inside bar is a bar fully contained within the prior bar's high-low range.
It represents indecision or consolidation after a move. The breakout above the
mother bar's high or below its low resolves the indecision and typically continues
in the breakout direction. Inside bars following a strong directional move are
particularly reliable continuation patterns.

### Indicators

- **Inside bar:** `High[0] < High[−1] AND Low[0] > Low[−1]`.
- **Mother bar:** The prior bar that contains the inside bar.
- **Breakout:** `Close[+1] > High[−1]` (long) or `Close[+1] < Low[−1]` (short).

### Standard Parameters

| Parameter | Common values |
|---|---|
| Prior trend requirement | 3–10 bars of same direction |
| Entry | On breakout candle close or next open |
| Stop | Opposite side of mother bar |
| Target | 1.0× mother bar range projected |

### Brute-Force Parameter Search Space

```
prior_trend_bars : [3, 5, 10]
entry_bar        : ["breakout_close", "next_open"]
stop_type        : ["mother_bar_opposite", "inside_bar_opposite"]
atr_stop_mult    : [0.5, 1.0, 1.5]
target_mult      : [1.0, 1.5, 2.0]
context_filter   : ["none", "trend_direction", "at_sr"]
timeframe        : [5min, 15min]
```

---

## PB-04 — Morning Star / Evening Star

### Hypothesis

The Morning Star is a 3-bar bullish reversal pattern: large bearish bar, then a
small-body (indecision) bar that gaps or significantly overlaps lower, then a
large bullish bar that closes above the midpoint of the first bar. It signals a
transition from bearish to bullish control. Evening Star is the inverse.

### Indicators

- **Bar 1:** Large bearish candle (body > ATR × threshold).
- **Bar 2:** Small body (body < 30% of ATR) — indecision/star.
- **Bar 3:** Large bullish candle closing above midpoint of Bar 1 body.
- **Gap (optional):** Star gaps below Bar 1 body (stronger signal on higher TF).

### Standard Parameters

| Parameter | Common values |
|---|---|
| Bar 1 body size | > 60% of ATR(14) |
| Bar 2 body size | < 30% of ATR(14) |
| Bar 3 penetration | Closes above 50% of Bar 1 body |
| Entry | Close of Bar 3 or open of Bar 4 |
| Stop | Low of Bar 2 (for morning star) |
| Target | 2:1 R:R |

### Brute-Force Parameter Search Space

```
bar1_body_atr    : [0.4, 0.5, 0.6, 0.7]      # bar 1 body / ATR minimum
bar2_body_atr    : [0.1, 0.2, 0.30]           # bar 2 body / ATR maximum
bar3_penetration : [0.40, 0.50, 0.60]         # fraction of bar 1 body to close above
gap_required     : [True, False]
context_filter   : ["none", "after_trend", "at_sr"]
atr_stop_mult    : [0.5, 1.0, 1.5]
timeframe        : [15min, 1h]
```

---

## PB-05 — Doji Reversal

### Hypothesis

A Doji is a bar where the open and close are nearly equal, creating a cross-like
appearance. It signals indecision — neither buyers nor sellers achieved dominance.
At the end of a trend, a Doji signals potential exhaustion and reversal. A
gravestone Doji (long upper wick, body at low) after an uptrend is strongly
bearish; a dragonfly Doji (long lower wick, body at high) after a downtrend is
strongly bullish.

### Indicators

- **Doji condition:** `|Close − Open| / ATR(14) < threshold` — tiny body.
- **Wick analysis:** Direction of dominant wick indicates rejection.
- **Types:**
  - Standard Doji: wick on both sides.
  - Gravestone Doji: upper wick only (bearish).
  - Dragonfly Doji: lower wick only (bullish).

### Brute-Force Parameter Search Space

```
body_atr_max     : [0.05, 0.10, 0.15, 0.20]   # body size / ATR
doji_type        : ["standard", "gravestone", "dragonfly", "all"]
prior_trend_bars : [3, 5, 10]
context_filter   : ["none", "at_sr", "at_ema"]
atr_stop_mult    : [0.75, 1.0, 1.5]
rr_ratio         : [1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## PB-06 — Three Bar Reversal

### Hypothesis

The three-bar reversal pattern consists of three sequential bars that signal
momentum exhaustion and reversal: (1) a large bar in the trend direction,
(2) a smaller bar still in trend direction (weakening), (3) a bar that closes
beyond the high/low of bar 1 in the opposite direction. This pattern is one
of the cleanest programmatic reversal signals available.

### Indicators

- **Bullish three-bar reversal:**
  1. Bar −2: Large bearish bar.
  2. Bar −1: Bearish bar with lower high (lower than bar −2).
  3. Bar 0: Bullish bar with close above high of bar −2.
- **Bearish three-bar reversal:** Inverse.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Consecutive bars | 3 (canonical) |
| Bar 3 closes beyond | High of bar −2 (bull) or Low of bar −2 (bear) |
| Entry | Close of bar 0 |
| Stop | Low of bar −2 (bull) + ATR buffer |
| Target | 2:1 R:R |

### Brute-Force Parameter Search Space

```
bar1_body_atr_min: [0.3, 0.5, 0.7]    # first bar must be significant
close_beyond_bar1: [True, False]        # bar 3 must close beyond bar 1
context_filter   : ["none", "at_sr", "trend_reversal"]
atr_stop_mult    : [0.5, 1.0, 1.5]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

---

## PB-07 — Head & Shoulders Pattern

### Hypothesis

The Head & Shoulders (H&S) is one of the most reliable chart reversal patterns.
It consists of three peaks: a left shoulder, a higher head, and a lower right
shoulder, with a neckline connecting the troughs between them. A close below
the neckline confirms the pattern and projects a measured move equal to the
head-to-neckline distance downward from the neckline breakout.

### Indicators

- **Left shoulder:** Local peak after an uptrend.
- **Head:** Higher peak than the left shoulder.
- **Right shoulder:** Lower peak than the head, approximately equal to left shoulder.
- **Neckline:** Line connecting the troughs between the peaks.
- **Breakout:** Close below the neckline (bear H&S) or above (inverse H&S).

### Detection Algorithm

1. Detect swing highs using a minimum lookback N.
2. Confirm three-peak structure where middle peak exceeds both.
3. Check right shoulder is below the head.
4. Draw neckline; wait for close below.
5. Measured move: neckline − (head − neckline).

### Brute-Force Parameter Search Space

```
swing_lookback   : [5, 10, 15, 20]     # bars each side for swing detection
shoulder_ratio   : [0.7, 0.8, 0.9]    # right shoulder must be < ratio × head
neckline_buffer  : [0.0, 0.1]         # ATR buffer for neckline break
measured_move    : [0.5, 0.75, 1.0]   # fraction of full measured move as target
retest_entry     : [True, False]       # enter on neckline retest after breakout
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [15min, 1h]
```

### Notes

Automating H&S detection is non-trivial. Swing detection sensitivity (lookback)
greatly affects pattern quality. Recommend 15-min or 1-h bars where patterns
are more visually clean. False patterns are common on 1-min/5-min bars.

---

## PB-08 — Double Top / Double Bottom

### Hypothesis

The Double Top is formed when price makes two approximately equal highs
separated by a trough. Failure to break above the first high on the second
attempt signals weakening buying pressure — sellers are defending the level.
A close below the trough (neckline) confirms the reversal. Double Bottom
is the inverse bullish pattern.

### Indicators

- **First peak:** Swing high.
- **Second peak:** Swing high approximately equal to the first (within tolerance).
- **Neckline:** The trough between the two peaks.
- **Confirmation:** Close below neckline.
- **Target:** Measured move = distance from double top to neckline, projected
  below the neckline.

### Brute-Force Parameter Search Space

```
swing_lookback   : [5, 10, 15, 20]
peak_tolerance   : [0.001, 0.002, 0.005]    # peaks within % of each other
neckline_buffer  : [0.0, 0.05, 0.10]        # ATR mult buffer
target_mult      : [0.5, 0.75, 1.0]         # fraction of measured move
retest_entry     : [True, False]
atr_stop_mult    : [1.0, 1.5]
timeframe        : [15min, 1h]
```

---

## PB-09 — Triangle Breakout

### Hypothesis

Triangles (ascending, descending, symmetrical) represent a period of
consolidation where the range contracts toward an apex. Energy builds as
price makes lower highs and higher lows (symmetrical), or tests a flat
resistance/support level multiple times (ascending/descending). The eventual
breakout from the triangle tends to be forceful and directional.

### Indicators

- **Ascending triangle:** Flat resistance (multiple equal highs) + rising lows.
- **Descending triangle:** Flat support (multiple equal lows) + falling highs.
- **Symmetrical triangle:** Converging highs and lows — no flat side.
- **Apex:** Point where upper and lower trend lines converge.
- **Breakout:** Close beyond the triangle boundary.

### Detection Algorithm

1. Identify swing highs and lows with minimum N-bar lookback.
2. Fit trend lines: upper line through highs, lower through lows.
3. Confirm convergence (positive slope difference > 0).
4. Breakout: close beyond either trend line.

### Brute-Force Parameter Search Space

```
swing_lookback   : [5, 10, 15]
triangle_type    : ["ascending", "descending", "symmetrical", "any"]
min_touches      : [2, 3]                 # minimum touches per trend line
apex_pct_remaining: [0.1, 0.2, 0.3]      # enter when this close to apex
buffer_atr_mult  : [0.0, 0.10, 0.20]
target_triangle_base_mult: [0.5, 0.75, 1.0]
atr_stop_mult    : [1.0, 1.5]
timeframe        : [15min, 1h]
```

---

## PB-10 — Bull/Bear Flag Continuation

### Hypothesis

A flag pattern is a brief, orderly pullback against the prevailing trend after
a sharp directional move (the "flagpole"). The pullback forms parallel trend
lines creating the "flag". Breakout of the upper boundary (bull flag) or lower
boundary (bear flag) signals resumption of the original trend, with a target
equal to the flagpole height projected from the breakout.

### Indicators

- **Flagpole:** Sharp move of at least N× ATR in one direction over M bars.
- **Flag:** Subsequent pullback of 20–50% of the flagpole over 5–20 bars with
  declining volume.
- **Breakout:** Close beyond the flag's upper boundary (bull) or lower (bear).

### Standard Parameters

| Parameter | Common values |
|---|---|
| Flagpole minimum | 2–3× ATR(14) over 3–10 bars |
| Flag retracement | 20–50% of flagpole |
| Flag duration | 5–20 bars |
| Stop | Low of flag (bull) or high of flag (bear) |
| Target | Flagpole height projected from breakout |

### Brute-Force Parameter Search Space

```
pole_atr_mult    : [1.5, 2.0, 3.0]         # minimum flagpole size
pole_bars_max    : [5, 10, 15]              # flagpole max duration
flag_retrace_max : [0.30, 0.40, 0.50]      # max flag retracement of pole
flag_bars        : [5, 10, 15, 20]          # flag duration
flag_channel_slope_max: [0.3, 0.5]         # flag slope (0 = horizontal)
buffer_atr_mult  : [0.0, 0.10]
atr_stop_mult    : [1.0, 1.5]
target_pole_mult : [0.5, 0.75, 1.0]
timeframe        : [5min, 15min]
```

---

## PB-11 — Support & Resistance Bounce

### Hypothesis

Support and resistance levels are price zones where significant buying or
selling previously occurred. These levels are self-fulfilling: traders
remember them, place orders there, and react when price returns. Trading a
bounce off these levels — entering on the first bullish candle off support
or bearish candle off resistance — provides favorable R:R entries.

### Indicators

- **Swing S/R:** Local swing highs and lows detected via N-bar lookback.
- **Touch detection:** Price approaches level within ATR × threshold.
- **Bounce candle:** First bullish bar (for support) or bearish bar (for resistance)
  after touching the level.
- **Level strength:** Count prior touches of the level — more touches = stronger.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Swing lookback | 10, 20, 50 bars |
| Level proximity | Within 0.5× ATR(14) |
| Bounce confirmation | 1 bullish/bearish bar with close away from level |
| Stop | 1× ATR below support (for longs) |
| Target | Next S/R level or 2:1 R:R |

### Brute-Force Parameter Search Space

```
swing_lookback   : [10, 20, 50, 100]
proximity_atr    : [0.25, 0.50, 0.75, 1.0]
min_touches      : [1, 2, 3]
bounce_bars      : [1, 2]              # bars of confirmation
atr_stop_mult    : [0.5, 1.0, 1.5]
target_type      : ["next_sr", "fixed_rr"]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

---

## PB-12 — Round Number (Psychological Level) Reaction

### Hypothesis

Round numbers — whole figures, half figures, and quarter figures — act as
natural psychological price anchors. Large stop-loss clusters and limit orders
pile up at these levels. Price often stalls, reverses, or accelerates through
round numbers with above-average probability. The effect is strongest at
major round levels.

### Indicators

- **Round level detection:** `price % increment == 0` where increment defines
  what is "round" for each instrument.
- **EURUSD round levels:** Every 50 pips (1.0950, 1.1000, 1.1050, …).
- **XAUUSD round levels:** Every $10 or $50 (2000, 2050, 2100, …).
- **BTCUSD round levels:** Every $1,000 or $5,000.
- **Touch-and-bounce vs. break-and-retest:** Two modes.

### Standard Parameters

| Instrument | Round level increment |
|---|---|
| EURUSD | 50 pips (0.0050), 100 pips (0.0100) |
| XAUUSD | $10, $50, $100 |
| BTCUSD | $1,000, $5,000, $10,000 |
| XAGUSD | $0.50, $1.00 |

### Brute-Force Parameter Search Space

```
level_type       : ["50pip", "100pip", "whole_figure"]   # per-instrument
mode             : ["bounce", "breakout"]
proximity_atr    : [0.25, 0.50, 0.75]
confirmation_bars: [1, 2]
atr_stop_mult    : [0.5, 1.0, 1.5]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

---

## PB-13 — Prior Session High/Low Reaction

### Hypothesis

The prior session's high and low are among the most watched levels by intraday
traders and automated systems. When price approaches the prior day's high or low,
reactions are common: either a bounce (rejected) or an acceleration through
(breakout). This creates two tradeable setups from the same reference level.

### Indicators

- **Prior session high (PSH):** High of the previous trading session.
- **Prior session low (PSL):** Low of the previous trading session.
- **Mode:** Bounce (fade) or breakout (continuation).
- **Proximity:** Price within ATR × threshold of the level.

### Brute-Force Parameter Search Space

```
session_type     : ["prior_day", "prior_london", "prior_ny"]
mode             : ["bounce", "breakout"]
proximity_atr    : [0.25, 0.50, 1.0]
confirmation_bars: [1, 2]
atr_stop_mult    : [0.5, 1.0, 1.5]
rr_ratio         : [1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## PB-14 — Fair Value Gap (FVG) Fill

### Hypothesis

A Fair Value Gap (FVG), also known as an imbalance, occurs when a 3-bar
sequence leaves a price gap: Bar N+1 moves so strongly that its range does
not overlap with Bar N−1's range. The resulting gap represents a zone where
no two-sided price discovery occurred. Price tends to return to fill (overlap)
this imbalance, offering a defined entry point with a clear target and stop.

### Indicators

- **Bullish FVG:** `Low[+1] > High[−1]` — an upward gap (price rose fast).
  When price returns down to fill the gap, enter long at the FVG bottom.
- **Bearish FVG:** `High[+1] < Low[−1]` — a downward gap.
  When price returns up to fill the gap, enter short at the FVG top.
- **FVG size:** `Low[+1] − High[−1]` (bull FVG) — must exceed minimum ATR.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Minimum FVG size | 0.3× ATR(14) | Filter trivial gaps |
| Validity window | 20–100 bars | FVG expires if not filled |
| Entry | Price re-enters FVG zone | |
| Stop | Beyond the FVG zone | |
| Target | Top of FVG (for bull fill) — full fill or partial fill | |

### Brute-Force Parameter Search Space

```
min_fvg_atr_mult : [0.2, 0.3, 0.5, 0.75]
validity_bars    : [20, 50, 100, 200]
entry_pct_fvg    : [0.0, 0.25, 0.50]    # enter at top, 25%, or 50% into FVG
target_type      : ["full_fill", "50pct_fill", "next_sr"]
atr_stop_mult    : [0.5, 1.0, 1.5]
trend_filter     : ["none", "ema_direction", "htf_bias"]
timeframe        : [1min, 5min]
```

### Instrument Suitability

All instruments. FVGs are most reliable on Forex (EURUSD, XAUUSD) where
institutional participation is high and FVGs are regularly mitigated.

---

## PB-15 — Order Block Reaction

### Hypothesis

An Order Block (OB) is the last bearish candle before a significant bullish
impulse move (bullish OB), or the last bullish candle before a bearish impulse
(bearish OB). These zones represent where large institutional orders were placed.
When price returns to the order block, the institutional orders resume, causing
a reaction. The OB is the most fundamental SMC (Smart Money Concepts) entry.

### Indicators

- **Bullish OB:** Last bearish candle before a bullish impulse of N× ATR.
- **Bearish OB:** Last bullish candle before a bearish impulse.
- **Impulse threshold:** `|impulse_move| > k × ATR(atr_period)`.
- **OB zone:** High and low of the OB candle.
- **Reaction:** Price returns to OB zone → enter in original impulse direction.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Impulse ATR multiplier | 2.0, 3.0, 4.0× |
| OB validity | 50–200 bars from formation |
| Entry zone | Returning into OB body (high–low range) |
| Stop | Beyond OB (below low for bull OB) |
| Target | Next structural high or 2:1 R:R |

### Brute-Force Parameter Search Space

```
impulse_atr_mult : [1.5, 2.0, 3.0, 4.0]
ob_validity_bars : [20, 50, 100, 200]
entry_type       : ["ob_top", "ob_50pct", "ob_bottom"]
atr_stop_mult    : [0.5, 1.0, 1.5]
rr_ratio         : [1.5, 2.0, 2.5, 3.0]
htf_confirmation : [True, False]         # require higher-TF bias alignment
timeframe        : [5min, 15min]
```

---

## PB-16 — Liquidity Sweep + Reversal

### Hypothesis

Liquidity sits just beyond obvious swing highs (buy stops) and swing lows
(sell stops). Smart money drives price beyond these levels to trigger stop
orders, accumulate inventory at favorable prices, then reverses. A candle that
pierces a swing high but closes back below it (a "stop hunt") followed by
immediate reversal is a high-probability short entry — and vice versa for lows.

### Indicators

- **Swing high/low:** Detected with N-bar lookback.
- **Sweep:** Price high exceeds swing high but candle closes back below it.
- **Reversal bar:** The sweep bar closes strongly in the opposite direction.
- **Confirmation:** Follow-up bar confirms reversal momentum.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Swing lookback | 5, 10, 20 bars |
| Sweep definition | High exceeds swing high; close is below it |
| Confirmation | Next bar closes in reversal direction |
| Stop | Sweep bar extreme + ATR buffer |
| Target | Next significant swing level |

### Brute-Force Parameter Search Space

```
swing_lookback   : [5, 10, 15, 20]
sweep_buffer     : [0.0, 0.1, 0.2]      # ATR mult — sweep must exceed level by X
confirmation_bars: [1, 2]
atr_stop_mult    : [0.5, 1.0, 1.5]
target_type      : ["next_swing", "fixed_rr"]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

---

## PB-17 — Breaker Block

### Hypothesis

A Breaker Block is an Order Block (PB-15) that was "broken through" — price
moved through the OB zone without stopping, invalidating it as a support/
resistance block. However, when price returns to the broken OB, it often
reacts as the opposing force: a bullish OB that was broken becomes resistance
(bearish breaker); a bearish OB that was broken becomes support (bullish
breaker). This role reversal creates a predictable reaction zone.

### Indicators

- **Original OB:** Formed as in PB-15.
- **Break event:** Price moves through the OB without reversing.
- **Breaker zone:** Original OB zone, now acting as opposite S/R.
- **Return:** Price comes back to the breaker zone.
- **Signal:** Reaction from the breaker zone in the new direction.

### Brute-Force Parameter Search Space

```
impulse_atr_mult    : [1.5, 2.0, 3.0]
break_confirmation  : ["close_through", "wick_through"]
breaker_validity    : [50, 100, 200]
entry_type          : ["breaker_top", "breaker_50pct", "breaker_bottom"]
atr_stop_mult       : [0.5, 1.0, 1.5]
rr_ratio            : [1.5, 2.0, 2.5]
timeframe           : [5min, 15min]
```

---

## PB-18 — Swing High/Low Break Continuation

### Hypothesis

In a trending market, price makes higher highs and higher lows (uptrend).
When a prior swing high is broken to the upside (close above), it confirms
the trend continuation and offers a low-risk entry. The broken swing high
becomes new support. This is a simple, objective trend-continuation entry
aligned with structure rather than indicators.

### Indicators

- **Swing high:** Local high detected with N-bar lookback.
- **Break signal:** Current close > prior swing high.
- **Entry:** On breakout bar close or on pullback to broken level.
- **Stop:** Prior swing low (for longs) or recent ATR multiple.

### Brute-Force Parameter Search Space

```
swing_lookback   : [5, 10, 15, 20]
entry_type       : ["breakout_close", "pullback_retest"]
buffer_atr_mult  : [0.0, 0.05, 0.10]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_type      : ["next_swing", "fixed_rr"]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

---

## PB-19 — Wedge Pattern Breakout

### Hypothesis

A wedge is a chart pattern where both the upper and lower trend lines slope in
the same direction but converge. A rising wedge (both lines rise, upper less
steep) in an uptrend signals weakening momentum and often breaks to the
downside. A falling wedge in a downtrend often breaks to the upside. Wedges
represent an exhausting move that typically resolves with a sharp breakout.

### Indicators

- **Trend lines:** Fit through swing highs (upper) and swing lows (lower).
- **Wedge condition:** Both lines slope in same direction but converge.
- **Breakout:** Close beyond the opposite trend line.
- **Target:** Back to the start of the wedge (measured move).

### Brute-Force Parameter Search Space

```
swing_lookback   : [5, 10, 15]
min_touches      : [2, 3]               # per trend line
convergence_angle: [5, 10, 15]         # degrees of convergence minimum
breakout_buffer  : [0.0, 0.10]
target_type      : ["wedge_start", "fixed_rr"]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [15min, 1h]
```

---

## PB-20 — Cup and Handle Continuation

### Hypothesis

The Cup and Handle is a bullish continuation pattern where price forms a
rounded bottom (cup) followed by a brief consolidation/pullback (handle).
The handle is typically a small flag or channel sloping down 10–20% of the
cup's depth. A breakout above the cup's rim level after the handle completes
is the buy signal, with a measured target equal to the cup's depth.

### Indicators

- **Cup:** Rounded V or U shape — price corrects and recovers to prior highs.
- **Cup rim:** The prior high that defines the cup's upper boundary.
- **Handle:** Small pullback of 10–30% of cup depth, duration < 20% of cup.
- **Breakout:** Close above cup rim on the handle exit.
- **Target:** Cup rim + cup depth (measured move).

### Detection Considerations

Cup and Handle detection on intraday bars (5-min/15-min) requires a minimum
cup depth filter (e.g. > 1× ATR(14)) and duration filter (cup must span > 20
bars). On 1-min bars, patterns are too noisy for reliable detection.

### Brute-Force Parameter Search Space

```
cup_bars_min     : [20, 30, 50]
cup_bars_max     : [100, 200]
cup_depth_atr    : [2.0, 3.0, 5.0]            # minimum cup depth in ATR
handle_retrace   : [0.10, 0.20, 0.30]          # max handle retracement
handle_bars_max  : [5, 10, 20]
breakout_buffer  : [0.0, 0.10]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [15min, 1h]
```

---

## Cross-Strategy Considerations

### Context Is Everything for Pattern Trading

Pattern-based strategies without context filters have a very high false positive
rate on intraday bars. Always add at least one of:

| Context layer | Purpose |
|---|---|
| Trend direction (EMA slope, ADX) | Trade patterns only with the trend |
| S/R proximity | Patterns at key levels are far more reliable |
| Session timing | Patterns during active sessions have more follow-through |
| Volume confirmation | Higher volume on pattern completion = higher conviction |

### Timeframe Recommendations

| Pattern type | Recommended TF | Reason |
|---|---|---|
| Single-bar (engulfing, pin, doji) | 5-min, 15-min | 1-min too noisy |
| Multi-bar (morning star, 3-bar) | 15-min, 1-h | More meaningful candle sizes |
| Chart patterns (H&S, triangle) | 15-min, 1-h | Patterns need enough bars to form |
| SMC patterns (FVG, OB, sweep) | 1-min, 5-min | SMC works best at higher resolution |

### Suggested Evaluation Priority

| Priority | Strategy | Reason |
|---|---|---|
| 1 | PB-14 Fair Value Gap | Objective detection; clear target and stop |
| 2 | PB-01 Engulfing | Most studied single-bar pattern |
| 3 | PB-02 Pin Bar | High R:R at S/R levels |
| 4 | PB-11 S/R Bounce | Self-fulfilling; widely applicable |
| 5 | PB-10 Bull/Bear Flag | High-quality continuation with measured move |
| 6 | PB-15 Order Block | Core SMC signal; strong institutional basis |
| 7 | PB-03 Inside Bar | Simple, objective, easy to parameterize |
| 8 | PB-16 Liquidity Sweep | Very high R:R when correct; captures stop hunts |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
