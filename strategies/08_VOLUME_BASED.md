# Category 8 — Volume-Based: Top 15 Strategies

Detailed research document for the **Volume-Based** strategy family.
Each strategy is documented with: core hypothesis, indicators and their mechanics,
standard parameters used in practice, entry/exit rules, and a **brute-force
parameter search space** suitable for exhaustive or grid-search optimization over
the `data/bars/` corpus.

> **Critical caveat for this corpus:** Volume in `data/bars/` is **tick-volume**
> (the number of price ticks recorded during each bar), not notional traded
> volume in dollars or lots. Tick-volume is a reasonable proxy for market
> activity and participation level, but it may reflect broker-specific data
> collection artifacts rather than true institutional flow. Always verify
> volume > 0 consistency for your target instrument before building
> volume-dependent strategies. EURUSD and XAUUSD have the most consistent
> non-zero volume across years. Crypto instruments (BTCUSD, ETHUSD, etc.)
> may show higher variability in tick-volume recording.

---

## Table of Contents

| # | Strategy | Complexity | Best TF |
|---|---|---|---|
| VO-01 | Volume Spike Breakout | Low | 1-min, 5-min |
| VO-02 | OBV Divergence Reversion | Medium | 5-min, 15-min |
| VO-03 | Volume-Weighted Entry Filter | Low | Any |
| VO-04 | VWAP + Volume Confirmation | Medium | 1-min, 5-min |
| VO-05 | Money Flow Index (MFI) Signal | Medium | 5-min, 15-min |
| VO-06 | Chaikin Money Flow (CMF) | Medium | 5-min, 15-min |
| VO-07 | Accumulation/Distribution Line | Medium | 5-min, 15-min |
| VO-08 | Force Index Signal | Low | 5-min, 15-min |
| VO-09 | Volume-Weighted MACD | Medium | 5-min, 15-min |
| VO-10 | Volume Rate of Change (VROC) | Low | 1-min, 5-min |
| VO-11 | High-Volume Node Reaction | High | 5-min, 15-min |
| VO-12 | Ease of Movement (EMV) | Medium | 5-min, 15-min |
| VO-13 | Price-Volume Trend (PVT) | Low | 5-min, 15-min |
| VO-14 | Klinger Oscillator | Medium | 5-min, 15-min |
| VO-15 | Volume Profile Intraday Levels | High | 1-min, 5-min |

---

## VO-01 — Volume Spike Breakout

### Hypothesis

When a bar's volume is significantly higher than recent average (2–3× the
rolling mean), it signals that an unusually large number of participants are
active. High-conviction directional bars with volume spikes tend to continue
in the direction of the bar's close — the volume represents institutional
commitment to the move, not just noise.

### Indicators

- **Volume ratio:** `Volume / rolling_mean(Volume, n)`.
- **Spike condition:** `Volume_ratio > threshold`.
- **Direction:** `Close > Open` (bullish spike) or `Close < Open` (bearish).
- **Signal:** Spike bar confirms direction → enter on next bar open or current
  bar close.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Rolling window | 20, 50 bars | Mean volume over this window |
| Spike threshold | 2.0, 2.5, 3.0× mean | Higher = fewer, higher-quality signals |
| Entry | Same bar close or next bar open | |
| Stop | Low of spike bar (long) or high (short) | |
| Target | 1.5× ATR or 2:1 R:R | |

### Entry Rules

- **Long:** Bullish bar (close > open) with volume > N× average. Enter on bar
  close or next open.
- **Short:** Bearish bar with spike volume. Enter on bar close.
- Optional: Require the bar to also break a prior N-bar high/low.

### Brute-Force Parameter Search Space

```
volume_window    : [10, 20, 50, 100]
spike_mult       : [1.5, 2.0, 2.5, 3.0, 4.0]
entry_timing     : ["current_close", "next_open"]
require_breakout : [True, False]
breakout_n       : [5, 10, 20]           # N-bar high/low breakout
atr_stop_mult    : [0.75, 1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [1min, 5min]
```

### Instrument Suitability

| Instrument | Suitability | Notes |
|---|---|---|
| EURUSD | High | Consistent tick-volume data; spikes around economic releases |
| XAUUSD | High | Volume spikes coincide with significant gold moves |
| BTCUSD | Medium | Verify tick-volume consistency across years |
| Altcoins | Low | Thin volume; spikes may be noise |

---

## VO-02 — OBV Divergence Reversion

### Hypothesis

On-Balance Volume (OBV) accumulates volume in the direction of each bar's
close: `OBV += Volume if Close > Close[-1] else OBV -= Volume`. When price
makes a new high but OBV does not confirm (OBV divergence), it indicates that
the price move is not backed by increasing participation — a sign of exhaustion
and potential reversal. Bullish divergence (price lower low, OBV higher low)
signals reversal to the upside.

### Indicators

- **OBV:** Cumulative signed volume indicator.
- **Price swing:** N-bar swing highs/lows on Close.
- **OBV swing:** N-bar swing highs/lows on OBV.
- **Divergence:** Price higher high + OBV lower high → bearish.
  Price lower low + OBV higher low → bullish.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Swing lookback | 5, 10, 15, 20 bars each side |
| Divergence tolerance | OBV must not confirm by 5–10% margin |
| Confirmation | Entry on next reversal candle after divergence |
| Stop | Beyond price extreme (with ATR buffer) |
| Target | Prior swing level |

### Brute-Force Parameter Search Space

```
swing_lookback   : [5, 8, 10, 15]
obv_smooth       : [1, 3, 5]             # EMA smooth OBV before divergence detection
div_tolerance    : [0.0, 0.05, 0.10]     # OBV tolerance for "new high/low"
confirmation     : ["reversal_candle", "next_bar"]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_type      : ["prior_swing", "fixed_rr"]
rr_ratio         : [1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-03 — Volume-Weighted Entry Filter

### Hypothesis

Entering trades only when current bar volume exceeds its rolling average
filters out thin-market false moves. Low-volume bars are more susceptible to
noise and sudden reversals. High-volume bars represent genuine market activity
where moves are more likely to be sustained. This filter applies on top of
any directional strategy.

### Usage

Apply as a binary gate on any strategy:
- `Volume[0] > rolling_mean(Volume, n) × threshold` → allow entry.
- Otherwise, skip the signal.

### Brute-Force Parameter Search Space

```
volume_window    : [10, 20, 50]
threshold_mult   : [0.8, 1.0, 1.2, 1.5]   # volume > threshold × mean to enter
underlying       : ["ema_cross", "supertrend", "macd", "bb_reversion"]
timeframe        : [1min, 5min, 15min]
```

### Notes

This is a pure filter — it cannot be the primary signal. Combine with any
strategy from Categories 1–7 for a volume-quality enhancement.

---

## VO-04 — VWAP + Volume Confirmation

### Hypothesis

Combining VWAP (the institutional price anchor) with volume confirmation
creates a high-quality entry trigger. A breakout above VWAP on above-average
volume is far more reliable than a low-volume drift above VWAP. Similarly,
a reversion from above VWAP on declining volume signals a higher-probability
mean-reversion entry.

### Indicators

- **VWAP:** Session-anchored Volume-Weighted Average Price.
- **Volume confirmation:** Current bar volume > N× rolling average.
- **VWAP trend signal:** Price crosses above VWAP on high volume → long.
- **VWAP reversion signal:** Price extends above VWAP + Nσ on declining
  volume → short (fade).

### Brute-Force Parameter Search Space

```
vwap_reset       : ["daily", "session_london", "session_ny"]
signal_type      : ["trend_crossover", "reversion_fade"]
volume_window    : [20, 50]
volume_mult      : [1.0, 1.5, 2.0]
vwap_sigma_entry : [1.0, 1.5, 2.0]          # for reversion mode
atr_stop_mult    : [0.75, 1.0, 1.5]
rr_ratio         : [1.5, 2.0]
timeframe        : [1min, 5min]
```

---

## VO-05 — Money Flow Index (MFI) Signal

### Hypothesis

MFI is a volume-weighted RSI that simultaneously captures price direction and
volume strength. An MFI reading below 20 indicates both price at a low and
declining volume participation (oversold with institutional disinterest in
pushing lower). An MFI cross back above 20 from below is a stronger reversal
signal than RSI alone because it incorporates participation level.

### Indicators

- **Typical Price:** `(H + L + C) / 3`.
- **Raw Money Flow:** `Typical_Price × Volume`.
- **MFI(n):** `100 × Positive_Money_Flow / (Positive_Money_Flow + Negative_Money_Flow)`.
  Ranges 0–100.
- **Signal:** MFI < 20 → long; MFI > 80 → short; cross back for timing.

### Brute-Force Parameter Search Space

```
mfi_period       : [7, 10, 14, 20]
oversold_thresh  : [10, 15, 20, 25]
overbought_thresh: [90, 85, 80, 75]
exit_mfi         : [50]
signal_type      : ["threshold_cross", "exit_extreme"]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-06 — Chaikin Money Flow (CMF)

### Hypothesis

Chaikin Money Flow measures the degree of buying or selling pressure by
combining price position within the bar range with volume. Positive CMF
indicates accumulation (close in upper half of range on above-average volume);
negative CMF indicates distribution. CMF crossing above 0 on rising volume
is a bullish trend confirmation signal.

### Indicators

- **Money Flow Multiplier:** `((Close − Low) − (High − Close)) / (High − Low)`.
- **Money Flow Volume:** `MFM × Volume`.
- **CMF(n):** `sum(MFV, n) / sum(Volume, n)`. Range [−1, +1].
- **Signal:** CMF crosses above 0 → bullish; below 0 → bearish.
- **Confirmation:** Use positive CMF as trend filter for other strategies.

### Standard Parameters

| Parameter | Common values |
|---|---|
| CMF period | 20, 21 (standard), 14 (faster) |
| Long threshold | CMF > 0.05 (above zero + margin) |
| Short threshold | CMF < −0.05 |
| Exit | CMF crosses back to 0 |

### Brute-Force Parameter Search Space

```
cmf_period       : [10, 14, 20, 21, 30]
long_threshold   : [0.0, 0.02, 0.05, 0.10]
short_threshold  : [0.0, -0.02, -0.05, -0.10]
signal_type      : ["standalone", "filter_only"]
underlying       : ["ema_cross", "supertrend", "macd"]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-07 — Accumulation/Distribution Line

### Hypothesis

The A/D Line accumulates positive or negative money flow volumes without the
absolute direction requirement of OBV. Each bar contributes volume weighted
by the bar's close relative to its high-low range. A rising A/D Line while
price is falling (bullish A/D divergence) indicates institutional accumulation
despite falling prices — a strong reversal signal.

### Indicators

- **CLV (Close Location Value):** `((Close − Low) − (High − Close)) / (High − Low)`.
  Range [−1, +1].
- **A/D Line:** Cumulative sum of `CLV × Volume`.
- **Signal:** A/D divergence from price direction → potential reversal.

### Brute-Force Parameter Search Space

```
ad_smooth        : [1, 3, 5, 10]         # EMA smooth before divergence detection
swing_lookback   : [5, 10, 15]
divergence_type  : ["bullish", "bearish", "both"]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_type      : ["prior_swing", "fixed_rr"]
rr_ratio         : [1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-08 — Force Index Signal

### Hypothesis

Alexander Elder's Force Index combines price direction, extent of the price
move, and volume: `Force = (Close − Close[-1]) × Volume`. A smoothed Force
Index (EMA of Force) measures the raw power behind each price move. A 2-period
Force Index is ultra-sensitive to short-term buying/selling surges. A 13-period
Force Index identifies intermediate-term money flow.

### Indicators

- **Force(1):** Raw Force Index.
- **Force EMA(n):** `EMA(Force, n)`.
- **Signal:** Force(13) crosses above 0 from below → bullish (positive money
  flow); below 0 from above → bearish.
- **Short-term use:** Force(2) < 0 in an uptrend → potential long entry (dip).

### Brute-Force Parameter Search Space

```
force_ema_period : [2, 5, 13, 20]
signal_type      : ["zero_cross", "dip_in_trend", "both"]
trend_filter     : [None, "ema50", "ema200"]
force_threshold  : [0.0]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-09 — Volume-Weighted MACD

### Hypothesis

A MACD computed on VWAP prices rather than close prices incorporates volume
weighting into the momentum calculation. Crosses of the VWAP-MACD signal line
reflect momentum changes in the volume-weighted price rather than just the
last traded price — making the signal less susceptible to thin-volume price
extremes.

### Indicators

- **VWAP MACD:** Same as standard MACD but using VWAP as the price input
  instead of Close.
- `VW-MACD = EMA(VWAP, fast) − EMA(VWAP, slow)`
- `Signal = EMA(VW-MACD, signal_period)`
- **Signal:** VW-MACD crosses above signal line → long.

### Brute-Force Parameter Search Space

```
vwap_reset       : ["daily", "session"]
macd_fast        : [8, 10, 12]
macd_slow        : [21, 24, 26]
macd_signal      : [7, 9]
zero_filter      : [True, False]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-10 — Volume Rate of Change (VROC)

### Hypothesis

Volume Rate of Change measures the percentage change in volume over N bars:
`VROC(n) = (Volume − Volume[-n]) / Volume[-n] × 100`. A sharp positive VROC
(sudden volume surge) signals a major increase in market participation — often
preceding or confirming a significant price move. Used as an entry filter:
only trade when VROC exceeds a threshold.

### Standard Parameters

| Parameter | Common values |
|---|---|
| VROC period | 5, 10, 20 bars |
| Threshold | > 100% (volume doubled) or > 200% |
| Usage | Filter confirming another strategy's signal |

### Brute-Force Parameter Search Space

```
vroc_period      : [5, 10, 14, 20]
vroc_threshold   : [50, 100, 150, 200]   # % increase in volume
signal_role      : ["standalone_spike", "entry_filter"]
direction        : ["bar_direction", "price_momentum"]
atr_stop_mult    : [1.0, 1.5, 2.0]
hold_bars        : [3, 5, 10]
timeframe        : [1min, 5min]
```

---

## VO-11 — High-Volume Node Reaction

### Hypothesis

A Volume Profile maps the distribution of traded volume across price levels.
The Point of Control (POC) — the price level with the most traded volume —
acts as a magnet. The Value Area High (VAH) and Value Area Low (VAL) act
as support/resistance levels. Price approaching these levels from outside
tends to react: either a bounce (from VAH/VAL as boundaries) or a thrust
through the POC (as price seeks fair value).

### Indicators

- **Volume Profile:** `for each price level: sum(Volume) when price was at that level`.
- **POC:** `argmax(volume_at_price)` — highest volume level.
- **Value Area:** Price range containing 70% of total session volume.
- **VAH, VAL:** Top and bottom of the Value Area.

### Computation Notes

Building a proper volume profile requires grouping volume by price level
(rounding Close to the nearest pip/tick) and accumulating over the session.
This is compute-intensive but straightforward with Numba.

### Brute-Force Parameter Search Space

```
profile_period   : ["session", "day", "week"]
price_tick_size  : ["1pip", "5pips", "10pips"]   # rounding for price levels
signal_type      : ["poc_magnet", "val_bounce", "vah_bounce"]
proximity_atr    : [0.25, 0.50, 1.0]
atr_stop_mult    : [0.5, 1.0, 1.5]
target           : ["poc", "opposite_va", "fixed_rr"]
rr_ratio         : [1.5, 2.0]
timeframe        : [1min, 5min]
```

---

## VO-12 — Ease of Movement (EMV)

### Hypothesis

Ease of Movement relates price change to volume. A large price move on low
volume (high EMV) indicates that the market is "easy" to move — low resistance.
A small price move on high volume (low EMV) suggests the market is "hard" to
move — strong resistance from the opposing side. High positive EMV → bullish
easy upward movement; high negative EMV → bearish.

### Indicators

- **Midpoint move:** `(High + Low)/2 − (High[-1] + Low[-1])/2`.
- **Box ratio:** `Volume / (High − Low)`.
- **EMV:** `Midpoint_Move / Box_Ratio`.
- **Signal:** `EMA(EMV, n)` crosses above 0 → bullish; below 0 → bearish.

### Brute-Force Parameter Search Space

```
emv_smooth       : [7, 14, 20]
signal_threshold : [0.0]
volume_scale     : [1000, 10000, 100000]    # normalization factor
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-13 — Price-Volume Trend (PVT)

### Hypothesis

Price-Volume Trend is a cumulative indicator similar to OBV but uses the
percentage price change rather than just direction: `PVT += Volume × (Close − Close[-1]) / Close[-1]`.
This makes PVT sensitive to the magnitude of price changes, not just direction.
Divergences between PVT and price (price rising, PVT falling) indicate
weakening momentum backed by proportionally less volume per price move.

### Indicators

- **PVT:** `cumulative_sum(Volume × log(Close / Close[-1]))`.
- **Divergence:** Same detection method as OBV divergence (VO-02) but on PVT.
- **Signal:** PVT/price divergence → reversal expected.

### Brute-Force Parameter Search Space

```
pvt_smooth       : [1, 3, 5, 10]
swing_lookback   : [5, 10, 15]
divergence_type  : ["bullish", "bearish", "both"]
atr_stop_mult    : [1.0, 1.5, 2.0]
rr_ratio         : [1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-14 — Klinger Oscillator

### Hypothesis

The Klinger Oscillator is based on the concept of "volume force" — comparing
the direction of price movement against the sign of cumulative volume. It uses
two EMAs of the volume force series to create an oscillator (similar to MACD
in structure). The oscillator captures volume-driven momentum cycles and
divergences from price that may precede reversals.

### Indicators

- **Volume Force (VF):** Complex calculation combining direction of the midpoint,
  volume, and a running total of direction changes.
- **KO:** `EMA(VF, short_period) − EMA(VF, long_period)`.
- **Signal line:** `EMA(KO, signal_period)`.
- **Signal:** KO crosses above signal line → bullish; below → bearish.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Fast EMA | 34 |
| Slow EMA | 55 |
| Signal | 13 |

### Brute-Force Parameter Search Space

```
fast_period      : [25, 34, 40]
slow_period      : [50, 55, 65]
signal_period    : [9, 13]
zero_filter      : [True, False]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VO-15 — Volume Profile Intraday Levels

### Hypothesis

Extending VO-11 to use the prior session's volume profile, levels from the
prior day's POC, VAH, and VAL carry predictive power into the next session.
Price approaching these carry-forward levels tends to react similarly to
prior session S/R levels (Category 4). High-volume nodes from prior sessions
represent "fair value" from the perspective of prior participants.

### Method

1. Compute prior session's volume profile (POC, VAH, VAL).
2. In the current session, monitor price approaching these levels.
3. Apply fade (bounce) or breakout logic as in VO-11.

### Brute-Force Parameter Search Space

```
reference_period : ["prior_session", "prior_day", "prior_week"]
levels           : ["poc_only", "vah_val_only", "all_three"]
proximity_atr    : [0.25, 0.50, 1.0]
signal_type      : ["bounce", "breakout"]
atr_stop_mult    : [0.5, 1.0, 1.5]
target           : ["opposite_level", "poc", "fixed_rr"]
timeframe        : [1min, 5min]
```

---

## Cross-Strategy Considerations

### Volume Validation Protocol

Before using any volume-based strategy on a new instrument, run this
validation:

1. `pct_zero_volume = (df['Volume'] == 0).mean()` — if > 5%, volume data
   is unreliable.
2. Check for suspiciously round volume values (tick-volume should vary
   naturally; repeating exact integers suggest recording artifacts).
3. Compare volume time series across years for the same instrument to detect
   structural breaks in data recording.

### Volume as Confirmation vs. Primary Signal

| Role | Strategy examples | Recommended use |
|---|---|---|
| Primary signal | VO-01, VO-02, VO-08 | Requires high data confidence |
| Confirmation filter | VO-03, VO-04, VO-10 | Lower risk; enhances other signals |
| Regime context | VO-06, VO-07 | Meta-filter similar to ATR percentile |

### Suggested Evaluation Priority

| Priority | Strategy | Reason |
|---|---|---|
| 1 | VO-01 Volume Spike Breakout | Simple; most direct volume signal |
| 2 | VO-03 Volume Filter | Improves any strategy with minimal code |
| 3 | VO-02 OBV Divergence | Classic; well-studied; works with tick-volume |
| 4 | VO-05 MFI Signal | Volume-weighted RSI; clean implementation |
| 5 | VO-06 CMF | Institutional money flow measure |
| 6 | VO-04 VWAP + Volume | High-quality entries when volume confirms VWAP |
| 7 | VO-11 Volume Profile | Most information-rich but hardest to compute |
| 8 | VO-08 Force Index | Elder's proven indicator; easy to implement |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
