# Category 2 — Mean-Reversion: Top 20 Strategies

Detailed research document for the **Mean-Reversion** strategy family.
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
| MR-01 | Bollinger Band Mean Reversion | Low | 5-min, 15-min |
| MR-02 | RSI(2) Ultra-Short Reversion | Low | 5-min, 15-min |
| MR-03 | VWAP Standard Deviation Bands | Medium | 1-min, 5-min |
| MR-04 | Z-Score Statistical Reversion | Low | 5-min, 15-min |
| MR-05 | Stochastic %K/%D Reversion | Low | 5-min, 15-min |
| MR-06 | CCI Extreme Reversion | Low | 5-min, 15-min |
| MR-07 | Williams %R Reversion | Low | 1-min, 5-min |
| MR-08 | Keltner Channel Reversion | Medium | 5-min, 15-min |
| MR-09 | Price/EMA Distance (Rubber Band) | Low | 1-min, 5-min |
| MR-10 | RSI Divergence Reversion | Medium | 5-min, 15-min |
| MR-11 | Double Bollinger Band System | Low | 5-min, 15-min |
| MR-12 | Pivot Point Reversion | Medium | 5-min, 15-min |
| MR-13 | Money Flow Index (MFI) Extremes | Medium | 5-min, 15-min |
| MR-14 | Stochastic RSI Reversion | Low | 5-min, 15-min |
| MR-15 | DeMarker Oscillator Reversion | Low | 5-min, 15-min |
| MR-16 | Opening Range Mean Reversion | Low | 5-min |
| MR-17 | EMA Touch Return | Low | 1-min, 5-min |
| MR-18 | High-Low Channel Fade | Low | 5-min, 15-min |
| MR-19 | Connors RSI (3-Component) Reversion | Medium | 5-min, 15-min |
| MR-20 | TEMA Distance Reversion | Medium | 5-min, 15-min |

---

## MR-01 — Bollinger Band Mean Reversion

### Hypothesis

Price touching or closing outside the outer Bollinger Band represents a
statistical extreme — approximately 2 standard deviations from the mean.
In non-trending markets, price is expected to revert toward the middle band
(the moving average). The edge comes from consistently fading these extremes
before the rubber-band snaps back.

### Indicators

- **SMA(period):** Middle band — simple moving average of close prices.
- **Upper band:** `SMA + k × σ` where σ is the rolling standard deviation.
- **Lower band:** `SMA − k × σ`.
- **%B:** `(Close − lower) / (upper − lower)` — normalized position in the bands.
  %B > 1 = above upper band; %B < 0 = below lower band.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| MA period | 20 | Default; 10 for faster response on 1-min |
| σ multiplier (k) | 1.5, 2.0, 2.5 | 2.0 is standard |
| Entry | Close outside band, or first close back inside band | "re-entry" variant reduces false fades |
| Stop | Prior extreme + 0.5× ATR buffer | |
| Exit | Middle band (SMA) | |

### Entry Rules

- **Long:** Close < lower band (or first bar closing back above lower band after being below).
- **Short:** Close > upper band (or first bar closing back below upper band after being above).
- Optional trend filter: Only take reversion trades when ADX < 20 (non-trending regime).

### Exit Rules

- Price reaches middle band (SMA).
- Hard stop: Prior extreme + 0.5× ATR.
- Maximum holding period: N bars.

### Brute-Force Parameter Search Space

```
bb_period      : [10, 14, 20, 30, 50]
bb_mult        : [1.0, 1.5, 2.0, 2.5, 3.0]
entry_type     : ["close_outside", "reentry"]
adx_filter     : [None, 20, 25]      # ADX < value = non-trending
atr_stop_mult  : [0.5, 1.0, 1.5]
max_hold_bars  : [5, 10, 20, 30]
timeframe      : [5min, 15min]
```

Total combinations: ~5 × 5 × 2 × 3 × 3 × 4 × 2 = 3,600 per instrument.

### Instrument Suitability

| Instrument | Suitability | Notes |
|---|---|---|
| EURUSD | High | Clear mean-reversion behavior in Asian session |
| XAUUSD | Medium | Works in ranging sessions; dangerous in news events |
| BTCUSD | Low–Medium | Strong trends make fading risky |
| ETHUSD | Low–Medium | Similar to BTC |

---

## MR-02 — RSI(2) Ultra-Short Reversion

### Hypothesis

Larry Connors' RSI(2) system exploits the fact that a 2-period RSI reaching
extreme levels (< 5 or > 95) indicates a very short-term overextension that
tends to snap back within 1–5 bars. Unlike standard RSI(14), the 2-period
variant is extremely sensitive and triggers frequently on intraday bars.

### Indicators

- **RSI(2):** 2-period RSI computed on close prices. Ranges from near 0 to
  near 100 within individual sessions.
- **SMA(200):** Long-term trend filter — only take longs above it, shorts below.
- **Signal:** RSI(2) < 5 → long; RSI(2) > 95 → short.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| RSI period | 2 | Core to this strategy; 3 is a softer version |
| Long threshold | < 5, < 10, < 15 | Lower = higher selectivity |
| Short threshold | > 95, > 90, > 85 | |
| Exit RSI | > 55 for longs; < 45 for shorts | Return to neutral zone |
| Trend filter EMA | 200 | Only long above; only short below |

### Entry Rules

- **Long:** Price above SMA(200) AND RSI(2) < 5. Enter on bar close.
- **Short:** Price below SMA(200) AND RSI(2) > 95. Enter on bar close.

### Exit Rules

- RSI(2) crosses above 55 (long exit) or below 45 (short exit).
- Maximum holding period: 5–10 bars.
- Hard stop: 1.5× ATR from entry.

### Brute-Force Parameter Search Space

```
rsi_period       : [2, 3, 4]
long_threshold   : [2, 5, 10, 15]
short_threshold  : [98, 95, 90, 85]
exit_rsi_long    : [50, 55, 60, 65]
exit_rsi_short   : [50, 45, 40, 35]
trend_ema        : [None, 100, 200]
max_hold_bars    : [3, 5, 10, 15]
timeframe        : [5min, 15min]
```

### Instrument Suitability

Most effective on instruments with low-to-medium trend persistence. EURUSD
during low-volatility sessions is ideal. Avoid in strongly trending markets
(crypto bull runs, strong news moves on XAUUSD).

---

## MR-03 — VWAP Standard Deviation Bands

### Hypothesis

VWAP is the institutional price anchor for the session. When price deviates
more than 2 standard deviations above or below VWAP, it is statistically
expensive or cheap relative to the day's fair value. Institutional market
makers tend to bring price back toward VWAP, creating a reliable mean-reversion
force within the session.

### Indicators

- **VWAP:** `cumsum(Typical_Price × Volume) / cumsum(Volume)`, reset each session.
- **Typical Price:** `(High + Low + Close) / 3`.
- **VWAP bands:** `VWAP ± N × std(Typical_Price − VWAP)` computed over the session.
- **Signal:** Price at ±Nσ VWAP band → fade toward VWAP.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| VWAP reset | Daily / per Forex session | London or NY anchor |
| Band σ multiplier | 1.0, 1.5, 2.0, 2.5 | Entry at 2.0σ; target at 0.5σ |
| Entry | First close beyond Nσ band | |
| Exit | VWAP line or ±0.5σ | |
| Stop | Price extends 0.5× ATR beyond entry band | |

> **Volume caveat:** Verify that Volume > 0 for the target instrument before
> running VWAP-based strategies. EURUSD and XAUUSD have the most consistent
> volume data in this corpus.

### Brute-Force Parameter Search Space

```
vwap_reset       : ["daily", "session_london", "session_ny"]
entry_sigma      : [1.0, 1.5, 2.0, 2.5, 3.0]
exit_sigma       : [0.0, 0.5, 1.0]        # 0.0 = target VWAP exactly
atr_stop_mult    : [0.5, 1.0, 1.5]
timeframe        : [1min, 5min]
```

### Instrument Suitability

| Instrument | Suitability | Notes |
|---|---|---|
| EURUSD | High | Clear session structure; volume data reliable |
| XAUUSD | High | NY session VWAP very relevant |
| BTCUSD | Low | 24-h market; VWAP reset choice is arbitrary |

---

## MR-04 — Z-Score Statistical Reversion

### Hypothesis

The rolling z-score of log-returns measures how far the current price movement
is from its recent statistical mean in units of standard deviation. Values
exceeding ±2 indicate statistical extremes in the short-term return distribution,
which tend to correct toward zero. Using log-returns rather than raw price
avoids non-stationarity issues.

### Indicators

- **Log-return:** `log(Close / Close[1])`.
- **Rolling mean (μ):** Mean of log-returns over N bars.
- **Rolling std (σ):** Standard deviation of log-returns over N bars.
- **Z-score:** `(current_return − μ) / σ`.
- **Signal:** Z > +threshold → short (overbought); Z < −threshold → long.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Z-score window | 20, 60, 120, 240 bars | Shorter = more responsive, noisier |
| Entry threshold | ±1.5, ±2.0, ±2.5, ±3.0 | |
| Exit | Z returns to 0 or ±0.5 | |
| Stop | Z extends by additional 1.0σ in adverse direction | |

### Brute-Force Parameter Search Space

```
zscore_window    : [20, 30, 60, 120, 240]
entry_threshold  : [1.5, 2.0, 2.5, 3.0]
exit_threshold   : [0.0, 0.5]
atr_stop_mult    : [0.75, 1.0, 1.5, 2.0]
input_type       : ["log_return", "close_detrended"]
timeframe        : [5min, 15min]
```

### Instrument Suitability

All instruments. Works best on EURUSD (more stationary behavior) and on
instruments during low-volatility periods. Log-return z-scores are more
meaningful than raw price z-scores.

---

## MR-05 — Stochastic %K/%D Reversion

### Hypothesis

The Stochastic oscillator compares the current close to its high-low range over
N periods. When %K is in an extreme zone (< 20 or > 80) and then crosses back
with %D confirmation, it signals that the short-term momentum extreme has
resolved and price is likely to revert. The dual-line structure provides better
confirmation than RSI alone.

### Indicators

- **%K:** `(Close − Lowest_Low[n]) / (Highest_High[n] − Lowest_Low[n]) × 100`.
- **%D:** `SMA(%K, d_period)` — signal line.
- **Signal:** %K < 20 AND %K crosses above %D → long; %K > 80 AND %K crosses below %D → short.

### Standard Parameters

| Parameter | Common values |
|---|---|
| %K period | 5, 9, 14 |
| %D smoothing | 3 (SMA) |
| Overbought | 80, 85 |
| Oversold | 20, 15 |
| Slowing period | 1 (fast Stoch) or 3 (slow Stoch) |

### Entry Rules

- **Long:** %K < 20, %K crosses above %D. Enter on the crossover bar close.
- **Short:** %K > 80, %K crosses below %D. Enter on bar close.

### Brute-Force Parameter Search Space

```
k_period         : [5, 9, 14, 21]
d_period         : [3, 5]
slowing          : [1, 3]
oversold_thresh  : [15, 20, 25]
overbought_thresh: [85, 80, 75]
atr_stop_mult    : [0.75, 1.0, 1.5]
max_hold_bars    : [5, 10, 15, 20]
timeframe        : [5min, 15min]
```

---

## MR-06 — CCI Extreme Reversion

### Hypothesis

The Commodity Channel Index (CCI) measures how far price deviates from its
statistical mean, scaled by mean absolute deviation. Readings beyond ±100
(or ±150, ±200) indicate significant deviation from the rolling mean. On
short intraday timeframes these extremes tend to revert. CCI is less bounded
than RSI/Stochastic, allowing detection of larger extremes.

### Indicators

- **CCI(n):** `(Typical_Price − SMA(Typical_Price, n)) / (0.015 × MAD(n))`
  where MAD is the mean absolute deviation.
- **Signal:** CCI > +threshold → short; CCI < −threshold → long.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| CCI period | 14, 20 | 14 is most common |
| Entry threshold | ±100, ±150, ±200 | Higher = fewer but better trades |
| Exit | CCI returns to 0 | |
| Stop | CCI extends to ±300 in adverse direction | ATR stop is a safer alternative |

### Brute-Force Parameter Search Space

```
cci_period       : [10, 14, 20, 30]
entry_threshold  : [100, 125, 150, 200]
exit_threshold   : [0, 25, 50]
adx_filter       : [None, 20, 25]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## MR-07 — Williams %R Reversion

### Hypothesis

Williams %R measures where the close falls within the high-low range of the
last N periods, expressed as a negative percentage (0 = at N-period high,
−100 = at N-period low). Readings near 0 (overbought) or near −100 (oversold)
indicate short-term extremes that tend to revert on intraday timeframes. Its
calculation is the inverse of Stochastic %K, offering an alternative entry
trigger timing.

### Indicators

- **Williams %R(n):** `(Highest_High[n] − Close) / (Highest_High[n] − Lowest_Low[n]) × −100`.
- **Signal:** %R > −20 → overbought (short); %R < −80 → oversold (long).

### Standard Parameters

| Parameter | Common values |
|---|---|
| Period | 14 (default), 10, 20 |
| Overbought | > −20 |
| Oversold | < −80 |
| Exit | %R returns to −50 (midpoint) |

### Brute-Force Parameter Search Space

```
wr_period        : [5, 10, 14, 20]
oversold_thresh  : [-80, -85, -90]
overbought_thresh: [-20, -15, -10]
exit_level       : [-50, -40, -60]
atr_stop_mult    : [0.75, 1.0, 1.5]
max_hold_bars    : [5, 10, 15]
timeframe        : [1min, 5min]
```

---

## MR-08 — Keltner Channel Reversion

### Hypothesis

Keltner Channels use ATR-based bands around an EMA, forming a volatility-
adaptive channel. Unlike Bollinger Bands (which use standard deviation),
Keltner Channels are smoother and less prone to sudden band expansion during
spike events. Price reverting from the outer Keltner bands tends to be a
cleaner signal, as the channel contracts less during volatile spikes.

### Indicators

- **EMA(n):** Center line.
- **Upper Keltner:** `EMA + k × ATR(atr_period)`.
- **Lower Keltner:** `EMA − k × ATR(atr_period)`.
- **Signal:** Close beyond outer band → reversion expected.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| EMA period | 20 | Center line |
| ATR period | 10, 14 | ATR for band calculation |
| ATR multiplier (k) | 1.5, 2.0, 2.5 | |
| Entry | Close outside band | |
| Exit | Return to EMA center | |

### Brute-Force Parameter Search Space

```
ema_period      : [10, 20, 30]
atr_period      : [10, 14]
k_mult          : [1.0, 1.5, 2.0, 2.5, 3.0]
entry_type      : ["close_outside", "wick_touch"]
atr_stop_mult   : [0.5, 1.0, 1.5]
timeframe       : [5min, 15min]
```

---

## MR-09 — Price/EMA Distance (Rubber Band)

### Hypothesis

When price deviates significantly from a moving average — measured in ATR
units — there is a statistical tendency for it to snap back. The distance
between price and a fast or slow EMA acts as a "rubber band": the further
price stretches from its mean, the stronger the reversion force. This is
one of the most robust and parameter-stable mean-reversion setups.

### Indicators

- **EMA(period):** Reference mean.
- **Distance:** `(Close − EMA) / ATR(atr_period)` — deviation in ATR units.
- **Signal:** Distance > +threshold → short; Distance < −threshold → long.

### Standard Parameters

| Parameter | Common values |
|---|---|
| EMA period | 20, 50, 100 |
| ATR period | 14 |
| Distance threshold | 1.5, 2.0, 2.5, 3.0 ATR |
| Exit | Price returns to EMA |

### Brute-Force Parameter Search Space

```
ema_period       : [10, 20, 50, 100]
atr_period       : [10, 14]
distance_thresh  : [1.0, 1.5, 2.0, 2.5, 3.0]
exit_target      : ["ema", "half_distance"]
adx_filter       : [None, 20, 25]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [1min, 5min, 15min]
```

---

## MR-10 — RSI Divergence Reversion

### Hypothesis

Divergence occurs when price makes a new high (or low) but RSI does not
confirm it — a sign that momentum is weakening despite the new extreme.
RSI bullish divergence (price lower low, RSI higher low) signals a potential
upward reversion; bearish divergence (price higher high, RSI lower high)
signals downward reversion. Divergence is more selective than raw RSI extremes
and tends to produce higher R:R opportunities.

### Indicators

- **RSI(period):** Momentum oscillator.
- **Price swings:** Detected with a minimum N-bar lookback each side.
- **Divergence:** Price makes new pivot low but RSI forms higher low → bullish.
  Inverse → bearish.

### Standard Parameters

| Parameter | Common values |
|---|---|
| RSI period | 14 |
| Swing lookback | 5, 10, 15 bars each side |
| Divergence tolerance | ±5 RSI points (RSI "higher low" if within tolerance) |
| Entry | Confirmation candle after divergence detected |
| Stop | Below/above the divergence pivot |

### Brute-Force Parameter Search Space

```
rsi_period       : [7, 10, 14]
swing_lookback   : [3, 5, 8, 10]
div_tolerance    : [0, 3, 5]
confirmation     : ["any_bar", "bullish_candle"]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## MR-11 — Double Bollinger Band System

### Hypothesis

The Double Bollinger Band (DBB) system uses two sets of Bollinger Bands at
different σ levels (1σ and 2σ). Price between the two upper bands is in the
"buy zone" (strong uptrend); price between the two lower bands is in the "sell
zone" (strong downtrend). Price reverting from the outer 2σ band back toward
the 1σ band is the reversion entry signal. The inner bands act as a target.

### Indicators

- **BB(period, 1σ):** Inner bands.
- **BB(period, 2σ):** Outer bands.
- **Zones:**
  - Overbought reversion entry: Close above upper 2σ band.
  - Oversold reversion entry: Close below lower 2σ band.
  - Exit target: inner 1σ band or center SMA.

### Brute-Force Parameter Search Space

```
bb_period        : [14, 20, 30]
outer_sigma      : [1.5, 2.0, 2.5]
target           : ["inner_band", "center_sma"]
adx_filter       : [None, 20, 25]
atr_stop_mult    : [0.5, 1.0, 1.5]
timeframe        : [5min, 15min]
```

---

## MR-12 — Pivot Point Reversion

### Hypothesis

Classic pivot points (calculated from the prior period's High, Low, Close)
define widely watched support (S1, S2, S3) and resistance (R1, R2, R3) levels.
Institutional traders and algorithms reference these levels for order placement.
Fading the approach to S1/R1 with a target at the central pivot P exploits
the self-fulfilling institutional reaction at these levels.

### Indicators

- **Pivot (P):** `(H + L + C) / 3` from prior period.
- **R1:** `2P − L`; **R2:** `P + (H − L)`.
- **S1:** `2P − H`; **S2:** `P − (H − L)`.
- **Signal:** Price approaches S1 or R1 → fade toward P.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Pivot period | Daily (most common), Weekly |
| Levels to fade | S1/R1 (standard); S2/R2 (extended) |
| Touch definition | Price within ATR(14) of level |
| Exit | P (central pivot) |
| Stop | Beyond S2/R2 + ATR buffer |

### Brute-Force Parameter Search Space

```
pivot_period     : ["daily", "weekly"]
fade_level       : ["S1/R1", "S2/R2"]
touch_atr_thresh : [0.25, 0.5, 0.75, 1.0]
target           : ["P", "mid_SR1_P"]
atr_stop_mult    : [0.5, 1.0, 1.5]
timeframe        : [5min, 15min]
```

### Instrument Suitability

EURUSD and XAUUSD — pivot points are most reliable on instruments with
high institutional participation and clear session structure.

---

## MR-13 — Money Flow Index (MFI) Extremes

### Hypothesis

The Money Flow Index (MFI) is a volume-weighted RSI that measures buying and
selling pressure. MFI below 20 signals overselling with declining volume
commitment; above 80 signals overbought conditions. Volume weighting makes it
more sensitive to true institutional extremes than pure price-based oscillators,
provided volume data is reliable for the target instrument.

### Indicators

- **Typical Price:** `(H + L + C) / 3`.
- **Money Flow:** `Typical_Price × Volume`.
- **MFI(n):** RSI-like ratio of positive to negative money flow over N periods.
- **Signal:** MFI < 20 → long; MFI > 80 → short.

> **Volume caveat:** Verify volume consistency per instrument before applying MFI.
> XAUUSD and EURUSD have the most consistent volume data in this corpus.

### Brute-Force Parameter Search Space

```
mfi_period       : [7, 10, 14, 20]
oversold_thresh  : [10, 15, 20, 25]
overbought_thresh: [90, 85, 80, 75]
exit_level       : [50]
atr_stop_mult    : [1.0, 1.5]
timeframe        : [5min, 15min]
```

---

## MR-14 — Stochastic RSI Reversion

### Hypothesis

StochRSI applies the Stochastic formula to RSI values, creating an oscillator
of an oscillator that is more sensitive to short-term RSI extremes than raw
RSI. It reaches 0 and 1 extremes much more frequently than standard RSI,
producing more signals while maintaining similar logic. StochRSI below 0.05
signals an extreme oversold RSI state; above 0.95 signals extreme overbought.

### Indicators

- **RSI(rsi_period):** Standard RSI.
- **StochRSI:** `(RSI − min(RSI, stoch_period)) / (max(RSI, stoch_period) − min(RSI, stoch_period))`.
- **K/D lines:** Smoothed versions of StochRSI for entry confirmation.
- **Signal:** K < 0.05 → oversold; K > 0.95 → overbought.

### Brute-Force Parameter Search Space

```
rsi_period        : [10, 14]
stoch_period      : [10, 14]
smooth_k          : [3, 5]
smooth_d          : [3]
oversold_thresh   : [0.05, 0.10, 0.15, 0.20]
overbought_thresh : [0.95, 0.90, 0.85, 0.80]
atr_stop_mult     : [0.75, 1.0, 1.5]
timeframe         : [5min, 15min]
```

---

## MR-15 — DeMarker Oscillator Reversion

### Hypothesis

The DeMarker oscillator compares the current bar's high to the prior bar's
high (and low to low) to measure demand relative to supply on a 0–1 scale.
It is a less commonly used oscillator that can offer complementary signal
timing to RSI and Stochastic, particularly because its construction makes it
less correlated with standard momentum measures during choppy markets.

### Indicators

- **DeMax(n):** `mean(max(High − High[−1], 0), n)`.
- **DeMin(n):** `mean(max(Low[−1] − Low, 0), n)`.
- **DeMarker:** `DeMax / (DeMax + DeMin)`.
- **Signal:** < 0.10 → oversold (long); > 0.90 → overbought (short).

### Brute-Force Parameter Search Space

```
demarker_period   : [5, 10, 14, 20]
oversold_thresh   : [0.05, 0.10, 0.15, 0.20]
overbought_thresh : [0.95, 0.90, 0.85, 0.80]
exit_level        : [0.50]
atr_stop_mult     : [0.75, 1.0, 1.5]
timeframe         : [5min, 15min]
```

---

## MR-16 — Opening Range Mean Reversion

### Hypothesis

The opening range (first N minutes of the session) establishes a reference for
the day. When price moves beyond the opening range but fails to sustain the
breakout and reverses back inside within the first 1–3 bars, it indicates a
false breakout — the counter-strategy to the ORB trend trade. These failed
breakouts tend to retrace back to the opposite side of the range.

### Indicators

- **Opening range high (ORH):** High of the first N-minute window.
- **Opening range low (ORL):** Low of the first N-minute window.
- **Breakout test:** Price closes outside the range.
- **Failure signal:** Price reverses back inside the range on the next 1–3 bars.

### Standard Parameters

| Parameter | Common values |
|---|---|
| OR duration | 5, 10, 15, 30 minutes |
| Breakout threshold | Close beyond ORH/ORL |
| Failure condition | Close back inside range within N bars |
| Target | Opposite side of opening range |
| Stop | High/low of the outside bar + ATR buffer |

### Brute-Force Parameter Search Space

```
or_duration_min  : [5, 10, 15, 30]
reversal_bars    : [1, 2, 3]
target           : ["mid_range", "opposite_band"]
atr_stop_mult    : [0.5, 1.0, 1.5]
session          : ["london", "ny"]
timeframe        : [1min, 5min]
```

### Instrument Suitability

EURUSD (London 08:00 EET, NY 13:00 EET); XAUUSD (NY open dominant).
All timestamps in EET per corpus convention.

---

## MR-17 — EMA Touch Return

### Hypothesis

During a non-trending session, price repeatedly oscillates around its mean
EMA. Each time price moves 1–2× ATR away from the EMA and then shows a
reversal candle, there is a high probability it returns to the EMA. This is
distinct from the trend-following EMA pullback (TF-15): here, the higher-TF
trend is absent or weak, and the EMA acts as a true mean rather than dynamic
support.

### Indicators

- **EMA(period):** Mean reference line.
- **Distance:** `|Close − EMA| / ATR(14)` — deviation in ATR units.
- **Regime condition:** ADX < 20 (non-trending market).
- **Signal:** Distance > threshold AND reversal candle → enter toward EMA.

### Brute-Force Parameter Search Space

```
ema_period         : [10, 20, 50]
distance_thresh_atr: [0.5, 1.0, 1.5, 2.0]
adx_max            : [15, 20, 25]
atr_stop_mult      : [0.5, 1.0, 1.5]
exit_type          : ["ema_touch", "half_distance"]
timeframe          : [5min, 15min]
```

---

## MR-18 — High-Low Channel Fade

### Hypothesis

During range-bound sessions, price repeatedly bounces between a well-defined
high and low established over the last N bars. Selling near the top of the
range and buying near the bottom — with stops outside the range — produces
consistent small profits when the market is genuinely consolidating. The key
filter is confirming the range is tight (ATR relative to range width is small).

### Indicators

- **Range high:** `max(High, n)` — resistance.
- **Range low:** `min(Low, n)` — support.
- **Range center:** `(range_high + range_low) / 2`.
- **ATR filter:** `ATR(14) / (range_high − range_low)` — low ratio confirms range.

### Brute-Force Parameter Search Space

```
range_period     : [20, 30, 50, 100]
entry_pct        : [0.80, 0.85, 0.90, 0.95]   # % of range from center
atr_range_ratio  : [0.20, 0.30, 0.40]           # ATR/range width filter
target           : ["center", "opposite_side"]
atr_stop_mult    : [0.5, 1.0]
timeframe        : [5min, 15min]
```

---

## MR-19 — Connors RSI (3-Component) Reversion

### Hypothesis

Connors RSI (CRSI) combines three components: (1) RSI(3) of close prices,
(2) Up/Down streak RSI — counts consecutive up/down closes and applies RSI
to the streak duration, (3) ROC percentile rank over a lookback period.
The composite score produces more reliable oversold/overbought signals than
any individual component. CRSI < 10 → strong oversold; > 90 → strong
overbought.

### Indicators

- **RSI(3):** 3-period RSI of close.
- **UD_RSI(2):** RSI of a series counting consecutive up (+1) and down (−1)
  closes.
- **ROC percentile:** `percentile_rank(ROC(1), n_period)` — rank of today's
  1-bar return within the lookback.
- **CRSI:** `(RSI(3) + UD_RSI(2) + ROC_percentile) / 3`.

### Standard Parameters

| Parameter | Common values |
|---|---|
| CRSI components | RSI(3), UD_RSI(2), ROC_percentile(100) |
| Oversold entry | CRSI < 10 |
| Overbought entry | CRSI > 90 |
| Exit | CRSI > 50 (long); < 50 (short) |
| Trend filter | 200-period SMA |

### Brute-Force Parameter Search Space

```
rsi_period        : [2, 3, 4]
ud_rsi_period     : [2, 3]
roc_rank_period   : [50, 100, 200]
oversold_thresh   : [5, 10, 15, 20]
overbought_thresh : [95, 90, 85, 80]
exit_level        : [50, 55, 60]
trend_sma         : [None, 100, 200]
timeframe         : [5min, 15min]
```

---

## MR-20 — TEMA Distance Reversion

### Hypothesis

TEMA (Triple Exponential Moving Average) eliminates most of the lag inherent
in standard EMAs. When price deviates significantly from TEMA, the lag-reduced
nature of TEMA means the deviation is genuinely large relative to recent
dynamics — a potentially more reliable reversion signal than simple EMA
distance (MR-09). The reduced lag means the TEMA is closer to the "true"
current mean of price.

### Indicators

- **TEMA(n):** `3×EMA(n) − 3×EMA(EMA(n)) + EMA(EMA(EMA(n)))`.
- **Distance:** `(Close − TEMA) / ATR(14)` — in ATR units.
- **Signal:** Deviation > threshold → mean-reversion entry.

### Brute-Force Parameter Search Space

```
tema_period      : [9, 14, 21, 30]
distance_thresh  : [1.0, 1.5, 2.0, 2.5]
atr_period       : [10, 14]
exit_type        : ["tema_touch", "half_distance"]
atr_stop_mult    : [0.75, 1.0, 1.5]
timeframe        : [5min, 15min]
```

---

## Cross-Strategy Considerations

### Regime Detection

Mean-reversion strategies share a fundamental requirement: the market must not
be in a strong trend. Always apply at least one regime filter:

| Filter | Condition | Notes |
|---|---|---|
| ADX | ADX < 20 (or < 25) | Most reliable non-trend indicator |
| Hurst | H < 0.5 | Mean-reverting regime (see SQ-03) |
| BB Width | BBW at low percentile | Compressed volatility |
| ATR | ATR < 40th percentile | Quiet, ranging market |

### Transaction Cost Sensitivity

Mean-reversion trades have smaller average wins than trend-following trades and
are more sensitive to transaction costs. Apply a minimum net R:R requirement:

| Instrument | Spread estimate | Minimum R:R for viability |
|---|---|---|
| EURUSD | 0.5–1.0 pip | 1.5:1 |
| XAUUSD | $0.10–$0.30 | 1.5:1 |
| BTCUSD | 0.05%–0.10% | 2.0:1 |

### Suggested Evaluation Priority

| Priority | Strategy | Reason |
|---|---|---|
| 1 | MR-01 Bollinger Band Reversion | Most well-documented; easy baseline |
| 2 | MR-02 RSI(2) Ultra-Short | Connors system; proven on equities — test on Forex/Crypto |
| 3 | MR-03 VWAP Deviation | Institutional anchor; high reliability during sessions |
| 4 | MR-04 Z-Score Reversion | Statistically clean on log-returns |
| 5 | MR-10 RSI Divergence | High R:R; selective signal |
| 6 | MR-19 Connors RSI | Multi-component reduces false signals |
| 7 | MR-12 Pivot Point | Self-fulfilling institutional levels |
| 8 | MR-09 EMA Rubber Band | Simple, adaptable, broadly applicable |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
