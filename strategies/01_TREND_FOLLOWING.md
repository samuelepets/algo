# Category 1 — Trend-Following: Top 20 Strategies

Detailed research document for the **Trend-Following** strategy family.
Each strategy is documented with: core hypothesis, indicators and their mechanics,
standard parameters used in practice, entry/exit rules, and a **brute-force
parameter search space** suitable for exhaustive or grid-search optimization over
the `data/bars/` corpus.

All strategies operate on 1-minute bars or on bars resampled from them
(5 min, 15 min, 1 h, 4 h). See `CATEGORIES.md` for resampling rules.

---

## Table of Contents

| # | Strategy | Complexity | Best TF |
|---|---|---|---|
| TF-01 | EMA Crossover (Fast/Slow) | Low | 5-min, 15-min |
| TF-02 | Triple EMA Alignment (5/8/13 or Fibonacci) | Low | 5-min, 15-min |
| TF-03 | MACD Line/Signal Crossover | Low | 5-min, 15-min |
| TF-04 | MACD + 200 EMA Trend Filter | Low | 5-min, 15-min |
| TF-05 | EMA Crossover + RSI Momentum Filter | Low | 5-min |
| TF-06 | ADX + EMA Directional System | Low | 5-min, 15-min |
| TF-07 | SuperTrend | Low | 5-min, 15-min |
| TF-08 | SuperTrend + VWAP + ADX Combo | Medium | 5-min |
| TF-09 | VWAP Trend Bias | Low | 1-min, 5-min |
| TF-10 | Parabolic SAR Trend-Following | Low | 5-min, 15-min |
| TF-11 | Ichimoku Cloud System | Medium | 15-min, 1-h |
| TF-12 | Williams Alligator (Jaw/Teeth/Lips) | Low | 5-min, 15-min |
| TF-13 | EMA Ribbon (Multi-MA Alignment) | Medium | 5-min, 15-min |
| TF-14 | Hull Moving Average (HMA) Trend | Low | 1-min, 5-min |
| TF-15 | EMA Pullback to Dynamic Support | Low | 1-min, 5-min |
| TF-16 | Linear Regression Channel Trend | Medium | 5-min, 15-min |
| TF-17 | Donchian Channel Breakout | Low | 15-min, 1-h |
| TF-18 | N-Period High/Low Breakout | Low | 5-min, 15-min |
| TF-19 | Momentum (ROC) Breakout | Low | 1-min, 5-min |
| TF-20 | Elder Impulse System | Medium | 5-min, 15-min |

---

## TF-01 — EMA Crossover (Fast/Slow)

### Hypothesis

When a short-period EMA crosses above a long-period EMA, recent price momentum
has shifted upward; the crossing represents a regime change from bearish to
bullish short-term dynamics. The edge comes from capturing the beginning of
sustained directional moves before the crowd catches up.

### Indicators

- **EMA(fast):** Exponential Moving Average over a short period. Reacts quickly
  to recent price changes, representing current momentum.
- **EMA(slow):** EMA over a longer period. Represents the underlying trend.
- **Signal:** `EMA(fast) > EMA(slow)` → bullish; `EMA(fast) < EMA(slow)` →
  bearish. A crossover triggers the entry.

### Standard Parameters (practice-validated)

| Parameter | Common values | Notes |
|---|---|---|
| Fast EMA | 5, 8, 9, 12 | 9 is the most popular for 1-min/5-min scalping |
| Slow EMA | 20, 21, 26, 50 | 21 pairs well with 9; 26 with 12 (MACD-like) |
| Popular pairs | 9/21, 5/20, 8/21, 9/30, 12/26 | |
| ATR stop mult | 1.0×–2.0× ATR(14) | Adaptive to volatility |
| R:R target | 1.5:1 – 2.5:1 | |

### Entry Rules

- **Long:** `EMA(fast)` crosses above `EMA(slow)`; both lines sloping upward;
  bar closes above both EMAs.
- **Short:** `EMA(fast)` crosses below `EMA(slow)`; both lines sloping downward;
  bar closes below both EMAs.
- Optional MTF filter: price must be above EMA(200) on a higher TF (e.g. 1-h)
  for longs, below for shorts.

### Exit Rules

- Opposite crossover.
- ATR-based trailing stop below/above the slow EMA.
- Fixed R:R target.

### Brute-Force Parameter Search Space

```
fast_ema     : [3, 5, 7, 8, 9, 10, 12, 13]
slow_ema     : [18, 20, 21, 25, 26, 30, 34, 50]
constraint   : slow_ema > fast_ema + 5
atr_stop_mult: [0.5, 1.0, 1.5, 2.0, 2.5]
rr_ratio     : [1.0, 1.5, 2.0, 2.5, 3.0]
timeframe    : [5min, 15min]
```

Total combinations (unconstrained): ~8 × 8 × 5 × 5 × 2 = 3,200. With constraint,
approximately ~1,500 valid combinations per instrument.

### Instrument Suitability

| Instrument | Suitability | Notes |
|---|---|---|
| EURUSD | High | Consistent trending during London/NY sessions |
| XAUUSD | High | Strong trends, higher volatility → wider stops |
| BTCUSD | High | Strong trends but higher false-breakout rate |
| ETHUSD | Medium | Similar to BTC; more noise |
| XAGUSD | Medium | Trends exist but less liquid |
| BATUSD/ADAUSD/AVEUSD/CMPUSD | Low | Thin markets; many whipsaws |

---

## TF-02 — Triple EMA Alignment (Fibonacci Ribbon)

### Hypothesis

When three EMAs with Fibonacci-derived periods (5, 8, 13 or 9, 21, 55) are fully
aligned in ascending order (fast > mid > slow) with positive slopes, the market
is in a strongly trending state. Entries are taken on pullbacks to the middle or
slow EMA rather than on raw crossovers, improving entry quality.

### Indicators

- **EMA(fast):** e.g. 5 or 9 — immediate momentum proxy.
- **EMA(mid):** e.g. 8 or 21 — short-term trend.
- **EMA(slow):** e.g. 13 or 55 — medium-term trend context.
- **Alignment signal:** `EMA(fast) > EMA(mid) > EMA(slow)` (bull) or inverse.
- **Slope filter:** All three EMAs must have positive (or negative) slope.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Period sets | (5, 8, 13), (9, 21, 55), (8, 13, 21), (10, 20, 50) |
| Entry trigger | Pullback to EMA(mid) or EMA(slow) after alignment |
| Confirmation candle | First close back above EMA(mid) after pullback (bull) |
| Stop | Below swing low or below EMA(slow) |

### Entry Rules

- **Long:** All three EMAs aligned bullishly; price pulls back to touch EMA(mid)
  or EMA(slow); first bullish bar closing back above EMA(mid) → enter long.
- **Short:** Inverse alignment; price pulls back to EMA(mid); first bearish bar
  closing below EMA(mid) → enter short.

### Exit Rules

- Price closes below EMA(fast) on 2 consecutive bars (bull exit).
- EMA alignment breaks (fast < mid).
- Fixed ATR stop.

### Brute-Force Parameter Search Space

```
fast_ema     : [3, 5, 8, 9]
mid_ema      : [13, 20, 21, 34]
slow_ema     : [34, 50, 55, 89]
constraint   : fast < mid < slow
pullback_ema : [mid, slow]   # which EMA to use for pullback entry
atr_stop_mult: [1.0, 1.5, 2.0]
timeframe    : [5min, 15min]
```

### Instrument Suitability

Best on EURUSD, XAUUSD during trending sessions. Requires strong prior trend;
underperforms on Crypto altcoins.

---

## TF-03 — MACD Line/Signal Crossover

### Hypothesis

MACD measures the difference between two EMAs (fast and slow). When the MACD line
crosses above its signal line (EMA of MACD), it indicates that short-term momentum
is accelerating upward relative to the medium-term trend — a buy signal. The
histogram visualizes this divergence.

### Indicators

- **MACD line:** `EMA(fast) − EMA(slow)`
- **Signal line:** `EMA(MACD, signal_period)` — smoothed version of MACD.
- **Histogram:** `MACD − Signal` — positive when bullish momentum is accelerating.
- **Entry signal:** MACD line crosses above signal line (bull); opposite for bear.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Fast EMA | 12 | Default; 8 for faster crypto/intraday |
| Slow EMA | 26 | Default; 21 for faster response |
| Signal | 9 | Default across all markets |
| Alternative sets | (5,35,5), (8,21,9), (3,10,16) | Forex intraday; faster crypto |
| Stop | Below swing low or 1.5× ATR(14) | |
| Target | R:R 1.5–2.0 | |

### Entry Rules

- **Long:** MACD line crosses above signal line AND histogram turns positive;
  ideally MACD is above zero (macro bullish) or returning to zero from below.
- **Short:** MACD line crosses below signal line AND histogram turns negative.
- Filter: Only enter when MACD cross is above/below the zero line (avoids
  counter-trend signals).

### Exit Rules

- Opposite crossover.
- Histogram shrinks to < 25% of its peak.
- ATR trailing stop.

### Brute-Force Parameter Search Space

```
fast_ema     : [5, 8, 10, 12]
slow_ema     : [21, 24, 26, 30, 35]
signal      : [7, 9, 12]
zero_filter  : [True, False]   # only enter on same side as zero line
atr_stop_mult: [1.0, 1.5, 2.0]
timeframe    : [5min, 15min]
```

Total combinations: ~4 × 5 × 3 × 2 × 3 × 2 = 720 per instrument.

### Instrument Suitability

EURUSD (5,35,5 is classic for FX); XAUUSD, BTCUSD with default (12,26,9) or
(8,21,9). Avoid on thin altcoins (BATUSD, CMPUSD).

---

## TF-04 — MACD + 200 EMA Trend Filter

### Hypothesis

The 200-period EMA is the most widely watched long-term trend filter in trading.
By conditioning MACD signals on price being above (below) EMA(200), we ensure
entries are always in the direction of the dominant trend, eliminating a large
fraction of counter-trend false signals that plague raw MACD crossovers.

### Indicators

- **EMA(200):** Long-term trend baseline. Price above = bull regime; below = bear.
- **MACD(fast, slow, signal):** Entry trigger (same as TF-03).
- **Combined signal:** `Close > EMA(200)` + MACD bullish cross → long only.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Long-term EMA | 200 (on entry TF) or 50 on 1-h (equivalent long-term) |
| MACD | (12,26,9) default; (8,21,9) for crypto |
| Entry bar | Bar that closes with MACD line > signal AND Close > EMA(200) |
| Stop | Below swing low; or 1.5–2.0× ATR(14) |
| Target | Trail with EMA(21) or EMA(34); exit on MACD bear cross |

### Brute-Force Parameter Search Space

```
trend_ema    : [100, 150, 200, 250]
macd_fast    : [8, 10, 12]
macd_slow    : [21, 26, 30]
macd_signal  : [7, 9]
atr_stop_mult: [1.0, 1.5, 2.0]
timeframe    : [5min, 15min, 1h]
```

### Instrument Suitability

Excellent on EURUSD (200 EMA is widely respected) and XAUUSD. Good on BTCUSD.
On 5-min bars, EMA(200) = 200 × 5 min = ~16.7 hours of data — a meaningful
medium-term filter.

---

## TF-05 — EMA Crossover + RSI Momentum Filter

### Hypothesis

Pure EMA crossovers generate many signals in choppy markets where the RSI
oscillates near 50. Adding an RSI threshold filter (RSI > 55 for longs, < 45 for
shorts) ensures entries only occur when momentum is already aligned with the
crossover direction, improving signal quality significantly.

### Indicators

- **EMA(fast) / EMA(slow):** Primary crossover signal (same as TF-01).
- **RSI(period):** Momentum oscillator. Values > 50 indicate buying pressure;
  < 50 indicate selling pressure.
- **Combined:** EMA cross + RSI above/below threshold.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| EMA pair | 9/21, 9/30 | Standard scalping pairs |
| RSI period | 14 | Default; 10 or 7 for faster response |
| Long RSI threshold | > 50 or > 55 | 55 reduces frequency but improves quality |
| Short RSI threshold | < 50 or < 45 | |
| ATR stop | 1.0–1.5× ATR(14) | |

### Entry Rules

- **Long:** `EMA(9) > EMA(21)` (crossover just occurred) AND `RSI(14) > 55`.
- **Short:** `EMA(9) < EMA(21)` AND `RSI(14) < 45`.

### Brute-Force Parameter Search Space

```
fast_ema         : [5, 7, 9, 12]
slow_ema         : [18, 20, 21, 26]
rsi_period       : [7, 10, 14]
rsi_long_thresh  : [50, 52, 55, 57]
rsi_short_thresh : [50, 48, 45, 43]
atr_stop_mult    : [0.75, 1.0, 1.5, 2.0]
timeframe        : [1min, 5min]
```

### Instrument Suitability

All instruments. Particularly effective on EURUSD and XAUUSD during active
sessions. The RSI filter dramatically reduces noise on 1-min bars for BTCUSD.

---

## TF-06 — ADX + EMA Directional System

### Hypothesis

The ADX (Average Directional Index) measures trend strength without regard to
direction. An ADX above 20–25 confirms the market is trending, not ranging. By
requiring ADX confirmation before entering EMA-based trend signals, we
systematically avoid trading in sideways markets where MA crossovers fail.

### Indicators

- **ADX(period):** Non-directional trend strength. Range 0–100. >20 = trend;
  >25 = strong trend; >40 = very strong trend.
- **+DI / −DI:** Directional indicators. `+DI > −DI` = upward trend;
  `−DI > +DI` = downward trend.
- **EMA(period):** Direction filter (price above = bull, below = bear).
- **Signal:** ADX > threshold AND +DI > −DI AND Close > EMA → long.

### Standard Parameters

| Parameter | Common values |
|---|---|
| ADX period | 14 (default) |
| ADX threshold | 20, 25 |
| EMA (direction) | 20, 50 |
| Stop | Below most recent swing low; or 1.5× ATR |

### Brute-Force Parameter Search Space

```
adx_period    : [10, 14, 20]
adx_threshold : [15, 20, 25, 30]
trend_ema     : [20, 50, 100]
di_cross      : [True, False]   # require +DI/-DI cross or just level
atr_stop_mult : [1.0, 1.5, 2.0]
timeframe     : [5min, 15min]
```

### Instrument Suitability

All instruments. ADX is one of the most reliable choppy-market filters. Very
useful on BTCUSD where ranging and trending regimes alternate frequently.

---

## TF-07 — SuperTrend

### Hypothesis

SuperTrend is an ATR-based trailing support/resistance line that flips side
whenever price closes on the opposite side. It combines trend direction with
dynamic stop placement in a single indicator, making it one of the most
practical trend-following tools for intraday use.

### Indicators

- **ATR(period):** Measures volatility over `period` bars.
- **SuperTrend upper band:** `HL2 + multiplier × ATR` (resistance in downtrend).
- **SuperTrend lower band:** `HL2 − multiplier × ATR` (support in uptrend).
- **Signal:** When close crosses above upper band → trend flips to bullish (green);
  when close crosses below lower band → flips bearish (red).
- The active band acts as a trailing stop.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| ATR period | 7, 10, 14 | 10 is the most common default |
| Multiplier | 2.0, 3.0, 4.0 | 3.0 is the default; higher = fewer signals, wider stops |
| Common combos | (10, 3.0), (7, 3.0), (14, 2.0) | |
| Stop | The SuperTrend line itself | Built-in adaptive stop |

### Entry Rules

- **Long:** SuperTrend flips from red to green (close crosses above upper band).
  Enter on bar close.
- **Short:** SuperTrend flips from green to red. Enter on bar close.
- Optional: only enter in the direction of a higher-TF trend.

### Exit Rules

- SuperTrend flips direction (also acts as stop).
- Fixed R:R target based on ATR.

### Brute-Force Parameter Search Space

```
atr_period    : [5, 7, 10, 12, 14]
multiplier    : [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
htf_filter    : [None, "15min", "1h"]   # higher-TF trend filter
atr_stop_mult : [1.0, 1.5, 2.0]        # for fixed-target exit
timeframe     : [1min, 5min, 15min]
```

Total combinations: ~5 × 6 × 3 × 3 × 3 = 810 per instrument.

### Instrument Suitability

| Instrument | Suitability |
|---|---|
| EURUSD | High (especially on 5-min) |
| XAUUSD | High (volatile; larger multiplier preferred) |
| BTCUSD/ETHUSD | High (fast-moving; SuperTrend adapts well) |
| XAGUSD | Medium |
| Altcoins | Low–Medium |

---

## TF-08 — SuperTrend + VWAP + ADX Combo

### Hypothesis

Combining SuperTrend (trend direction), VWAP (institutional price anchor), and
ADX (trend strength confirmation) creates a high-conviction filter that takes
only the strongest trend signals while avoiding weak, consolidating markets.
The three components are complementary: SuperTrend provides direction, VWAP
confirms bias, ADX confirms strength.

### Indicators

- **SuperTrend(atr, mult):** Direction filter (green = bull, red = bear).
- **VWAP:** Session-based volume-weighted price. Above = bullish institutional
  bias; below = bearish.
- **ADX(period):** Trend strength. Must exceed threshold.
- **EMA(21):** Secondary confirmation; VWAP and EMA must agree.

### Entry Conditions

- **Long:** SuperTrend = green AND Close > VWAP AND Close > EMA(21)
  AND ADX > 25.
- **Short:** SuperTrend = red AND Close < VWAP AND Close < EMA(21)
  AND ADX > 25.

### Standard Parameters

| Component | Parameters |
|---|---|
| SuperTrend | ATR(10), multiplier 3.0 |
| VWAP | Session-anchored (daily reset) |
| ADX | Period 14, threshold 25 |
| EMA | Period 21 |
| Stop | SuperTrend line |
| Target | 2× ATR from entry |

### Brute-Force Parameter Search Space

```
st_atr        : [7, 10, 14]
st_mult       : [2.0, 2.5, 3.0, 3.5]
adx_period    : [10, 14]
adx_threshold : [20, 25, 30]
trend_ema     : [20, 21, 50]
atr_target    : [1.5, 2.0, 2.5, 3.0]
timeframe     : [5min, 15min]
```

### Instrument Suitability

Best on EURUSD (session VWAP is meaningful due to clear session structure) and
XAUUSD. VWAP utility on 24-h Crypto is reduced (no natural session anchor).

---

## TF-09 — VWAP Trend Bias

### Hypothesis

VWAP is the average price weighted by volume since session open. Institutional
traders use it as a benchmark — buying below VWAP (getting a discount) and
selling above (getting a premium). Price above VWAP = institutional buyers
in control; below = sellers. Trading in the direction of the VWAP bias filters
out counter-institutional trades.

### Indicators

- **VWAP:** Computed as `cumsum(Typical Price × Volume) / cumsum(Volume)`,
  reset at session open.
- **Typical Price:** `(High + Low + Close) / 3`
- **VWAP bands:** VWAP ± N × standard deviation of price from VWAP.
- **Signal:** `Close > VWAP` → long bias; `Close < VWAP` → short bias.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| VWAP reset | Daily / session | Session = London or NY for Forex |
| Band width (σ) | 1.0, 1.5, 2.0 | Entry at VWAP band extremes |
| Entry trigger | Price returns from band toward VWAP | Reversion entry |
| Or | Price rides VWAP after pullback | Trend-continuation entry |
| Stop | Opposite VWAP band or 1.5× ATR |  |

### Usage as Trend-Following

- Enter long when price dips to VWAP from above and bounces (VWAP as dynamic
  support in uptrend).
- Trail stop just below VWAP.
- Exit when price closes below VWAP on 2 bars.

### Brute-Force Parameter Search Space

```
vwap_reset       : ["daily", "session"]
entry_type       : ["vwap_bounce", "above_vwap_continuation"]
band_width_sigma : [1.0, 1.5, 2.0]
atr_stop_mult    : [0.75, 1.0, 1.5]
timeframe        : [1min, 5min]
```

> **Note:** Verify volume > 0 consistency for each instrument before
> running VWAP-dependent backtests. XAUUSD and EURUSD have the most
> consistent volume data in this corpus.

---

## TF-10 — Parabolic SAR Trend-Following

### Hypothesis

Parabolic SAR (Stop and Reverse) is a trailing stop system that accelerates as
a trend matures. It is always in the market (long or short), placing a dot above
price in downtrends and below price in uptrends. When price crosses the SAR dot,
the system reverses. It is particularly useful as an adaptive trailing stop for
trend-following entries generated by other signals.

### Indicators

- **SAR:** Calculated as: `SAR(n) = SAR(n-1) + AF × (EP − SAR(n-1))`
  where EP = extreme price in the trend, AF = acceleration factor.
- **AF:** Starts at `AF_start`, increments by `AF_step` each bar where a new
  extreme is set, capped at `AF_max`.
- **Signal:** Dot flips from above price to below → bullish reversal; opposite
  → bearish reversal.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| AF start | 0.02 | Default; higher = more aggressive |
| AF step | 0.02 | Increment per new extreme bar |
| AF max | 0.20 | Cap on acceleration |
| Alternative | AF (0.01, 0.01, 0.10) | Slower, fewer signals |
| Alternative | AF (0.05, 0.05, 0.50) | Faster, more signals |

### Usage

- **Standalone:** Enter long/short on SAR flip; stop is the SAR dot itself.
- **Filter mode:** Use SAR dot position to confirm direction of an EMA or MACD
  signal — only take bullish EMA signals when SAR is below price.
- **Exit only:** Enter on another strategy's signal; use SAR flip as the exit.

### Brute-Force Parameter Search Space

```
af_start     : [0.01, 0.02, 0.03, 0.05]
af_step      : [0.01, 0.02, 0.03]
af_max       : [0.10, 0.15, 0.20, 0.30]
mode         : ["standalone", "exit_only", "filter"]
timeframe    : [5min, 15min]
```

### Instrument Suitability

Parabolic SAR performs well in strongly trending markets (BTCUSD, XAUUSD) and
poorly in choppy ones. Best used as an exit mechanism rather than a primary signal.

---

## TF-11 — Ichimoku Cloud System

### Hypothesis

Ichimoku is a complete trend-following system that simultaneously shows support
and resistance (cloud), momentum (TK cross), and trend direction (price vs. cloud).
It is one of the most information-dense single-indicator systems, particularly
effective on higher intraday timeframes.

### Indicators

- **Tenkan-sen (Conversion line):** `(max(High,n1) + min(Low,n1)) / 2`. Fast line.
- **Kijun-sen (Base line):** `(max(High,n2) + min(Low,n2)) / 2`. Slow line.
- **Senkou Span A:** `(Tenkan + Kijun) / 2`, plotted `n2` bars forward.
- **Senkou Span B:** `(max(High,n3) + min(Low,n3)) / 2`, plotted `n2` bars forward.
- **Kumo (Cloud):** Area between Span A and Span B. Price above = bullish.
- **Chikou Span:** Current close plotted `n2` bars back. Above past price = bullish.

### Standard Parameters

| Parameter | Traditional | Alt (faster) | Notes |
|---|---|---|---|
| n1 (Tenkan) | 9 | 7 | Fast period |
| n2 (Kijun) | 26 | 22 | Base period |
| n3 (Senkou B) | 52 | 44 | Cloud span |
| Displacement | 26 | 22 | Cloud offset forward |

The traditional (9, 26, 52) set is derived from Japanese trading sessions
(6-day week). On 24-h Crypto markets, (10, 30, 60) or (20, 60, 120) are
sometimes preferred.

### Entry Rules (Full Ichimoku Signal)

- **Long (all conditions):**
  1. Tenkan-sen crosses above Kijun-sen (TK bullish cross).
  2. Price is above the Kumo (cloud).
  3. Chikou Span is above price from `n2` bars ago.
  4. Senkou Span A > Span B (bullish cloud — green cloud).
- **Short:** All conditions inverse.
- **Simplified entry:** TK cross in direction of trend (price above cloud).

### Brute-Force Parameter Search Space

```
tenkan       : [7, 9, 10, 13]
kijun        : [20, 22, 26, 30]
senkou_b     : [44, 52, 60]
# constraint : senkou_b ≈ 2 × kijun
signal_type  : ["full_signal", "tk_cross_only", "cloud_breakout"]
timeframe    : [15min, 1h]
```

### Instrument Suitability

Ichimoku requires sufficient data for the cloud to be meaningful. Best on 15-min
bars (cloud covers ~10-h window) and 1-h bars. EURUSD and XAUUSD are ideal
instruments. Less reliable on thin Crypto altcoins.

---

## TF-12 — Williams Alligator

### Hypothesis

Bill Williams' Alligator uses three Smoothed Moving Averages (SMMA) with
Fibonacci periods and forward offsets to model the "sleeping" (ranging) and
"awake" (trending) states of the market. When the three lines fan out (alligator
eating), the market is trending and trades should be taken in the direction of
the fan. When lines converge (sleeping), avoid trading.

### Indicators

- **Jaw (blue):** SMMA(13) shifted 8 bars forward. Slowest — represents the
  broad trend direction.
- **Teeth (red):** SMMA(8) shifted 5 bars forward. Medium speed.
- **Lips (green):** SMMA(5) shifted 3 bars forward. Fastest — first to react.
- **Signal:** Lips crosses above Teeth and Jaw → bullish "awakening". Inverse
  for bearish.

### Standard Parameters

| Line | Period | Shift | Notes |
|---|---|---|---|
| Jaw | 13 | 8 | Fibonacci-based; standard |
| Teeth | 8 | 5 | Fibonacci-based |
| Lips | 5 | 3 | Fibonacci-based |
| Smoothing | SMMA | | Slower than EMA, reduces noise |

### Entry Rules

- **Long:** Lips crosses above Teeth AND Teeth is above Jaw (full alignment);
  price above all three lines. Enter on next bar open.
- **Short:** Lips crosses below Teeth AND Teeth below Jaw; price below all lines.
- **Avoid:** When the three lines are intertwined (sleeping alligator).

### Exit Rules

- Lines begin to converge (alligator falling asleep).
- Lips crosses in opposite direction.
- ATR trailing stop.

### Brute-Force Parameter Search Space

```
jaw_period   : [10, 13, 15]
jaw_shift    : [6, 8, 10]
teeth_period : [6, 8, 10]
teeth_shift  : [4, 5, 6]
lips_period  : [3, 5, 7]
lips_shift   : [2, 3, 4]
# Maintain Fibonacci ratios where possible
timeframe    : [5min, 15min]
```

Practical approach: fix the ratios and search over a global scaling factor.

```
scale_factor : [0.7, 0.85, 1.0, 1.15, 1.3]
# periods = round([5, 8, 13] × scale_factor)
# shifts  = round([3, 5, 8]  × scale_factor)
timeframe    : [5min, 15min]
```

---

## TF-13 — EMA Ribbon (Multi-MA Alignment)

### Hypothesis

A ribbon of 5–8 EMAs with evenly spaced periods provides a visual and
quantitative measure of trend strength. When all EMAs are aligned and well-spaced
(ribbon expanding), the trend is strong. When they converge or braid (ribbon
compressing), the trend is weakening. Trading in alignment with an expanding
ribbon has a strong theoretical edge.

### Indicators

- **5–8 EMAs** with periods from ~5 to ~89 (e.g. 5, 8, 13, 21, 34, 55, 89).
- **Alignment score:** Number of EMAs in correct order / total EMAs. Score = 1.0
  means fully aligned bull ribbon.
- **Spacing:** Average distance between consecutive EMAs — wider = stronger trend.

### Entry Rules

- **Long:** Full alignment (all EMAs in ascending order) AND ribbon expanding
  (spacing increasing over last N bars); enter on pullback to fastest EMA.
- **Short:** Full inverse alignment AND expanding; enter on pullback to fastest EMA.

### Standard Parameters

| Parameter | Values |
|---|---|
| EMA set | (5,8,13,21,34,55) or (8,13,21,34,55,89) |
| Alignment threshold | 100% (all in order) or ≥ 5/6 |
| Expansion window | 3, 5 bars |
| Entry pullback | Nearest EMA (5 or 8) |

### Brute-Force Parameter Search Space

```
ema_start      : [3, 5, 8]
ema_ratio      : [1.5, 1.618, 2.0]   # multiplicative step between periods
ema_count      : [4, 5, 6]           # number of EMAs in ribbon
alignment_pct  : [0.8, 0.9, 1.0]     # minimum alignment fraction
expansion_bars : [2, 3, 5]
timeframe      : [5min, 15min]
```

---

## TF-14 — Hull Moving Average (HMA) Trend

### Hypothesis

The Hull Moving Average (HMA) dramatically reduces the lag of traditional MAs
by using weighted moving averages of two WMA periods and taking their square root
in period count. The result is a smoother, more responsive line that reacts to
trend changes much faster than EMA/SMA, making it ideal for 1-min to 5-min bars.

### Indicators

- **HMA(n):** `WMA(2 × WMA(n/2) − WMA(n), sqrt(n))`
- **Signal:** HMA slope change (from falling to rising) → bull signal.
- **Or:** HMA crossover with a slower MA.

### Standard Parameters

| Parameter | Common values |
|---|---|
| HMA period | 9, 16, 25, 36, 49 (perfect squares preferred) |
| Trend confirmation | 2 consecutive bars of same slope |
| Stop | Below/above most recent HMA trough/peak |
| Crossover pair | HMA(9) over HMA(25) |

### Entry Rules

- **Long:** HMA slope turns positive (current HMA > prior HMA) for 2+ bars AND
  price is above HMA.
- **Short:** HMA slope turns negative for 2+ bars.

### Brute-Force Parameter Search Space

```
hma_fast     : [6, 9, 12, 16, 20]
hma_slow     : [20, 25, 36, 49]    # for crossover variant
mode         : ["slope", "crossover"]
slope_bars   : [1, 2, 3]           # confirmation bars
atr_stop_mult: [1.0, 1.5, 2.0]
timeframe    : [1min, 5min]
```

---

## TF-15 — EMA Pullback to Dynamic Support

### Hypothesis

During a trending market, price repeatedly pulls back to a fast EMA before
continuing in the trend direction. These pullbacks offer low-risk entries aligned
with the trend. The setup requires: (1) established trend, (2) pullback touches
the EMA, (3) rejection candle (bullish engulfing, pin bar) at the EMA level.

### Indicators

- **EMA(fast):** e.g. 9, 13, or 20 — acts as dynamic support in uptrend.
- **EMA(slow):** e.g. 50, 100, 200 — defines trend direction.
- **Rejection candle:** A specific candlestick pattern confirming the bounce
  (engulfing, hammer, inside bar breakout).

### Entry Rules

- **Long:** `Close > EMA(slow)` (in uptrend); price pulls back to touch
  `EMA(fast)` (low touches EMA(fast)); a bullish rejection candle forms at
  EMA(fast); enter on the close of the rejection bar or the open of the next bar.
- **Short:** Inverse — in downtrend, pullback to EMA(fast) resistance, bearish
  rejection candle.

### Standard Parameters

| Parameter | Values |
|---|---|
| Fast EMA | 9, 13, 20 |
| Slow EMA | 50, 100, 200 |
| Rejection candle | Engulfing, Hammer, Inside bar breakout |
| Stop | Below rejection candle low (1–2 pips buffer) or below EMA(fast) |
| Target | Next swing high or 2× ATR |

### Brute-Force Parameter Search Space

```
fast_ema          : [8, 9, 13, 20, 21]
slow_ema          : [50, 100, 200]
pullback_touch    : ["low_touches_ema", "close_near_ema"]  # definition of "touch"
candle_pattern    : ["engulfing", "hammer", "any_reversal", "none"]
atr_stop_mult     : [1.0, 1.5, 2.0]
timeframe         : [1min, 5min]
```

---

## TF-16 — Linear Regression Channel Trend

### Hypothesis

A rolling linear regression fit to the closing price defines the "true" trend
line. The channel (regression line ± N standard deviations of residuals) shows
where price is statistically expensive or cheap relative to the trend. Trading
in the direction of the regression slope and entering near the middle band or
on a channel breakout captures trend continuation moves.

### Indicators

- **LinReg(n):** Ordinary Least Squares fit to the last `n` close prices.
  Slope indicates trend direction and magnitude.
- **Residual std (σ):** Standard deviation of actual closes around the regression
  line.
- **Channel:** `LinReg ± k×σ` — upper and lower bounds.
- **Signal:** Slope > 0 AND price above LinReg → bull trend. Alternatively,
  price breaking above the upper channel → strong breakout.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Regression period | 50, 100, 200 bars |
| Channel width (k) | 1.5, 2.0, 2.5 × σ |
| Entry | Bounce from LinReg line (trend-following) or upper channel breakout |
| Stop | Opposite channel band or 1.5× ATR |

### Brute-Force Parameter Search Space

```
linreg_period   : [30, 50, 75, 100, 150, 200]
channel_width_k : [1.0, 1.5, 2.0, 2.5]
entry_type      : ["bounce_center", "breakout_upper"]
atr_stop_mult   : [1.0, 1.5, 2.0]
timeframe       : [5min, 15min]
```

---

## TF-17 — Donchian Channel Breakout

### Hypothesis

Donchian Channels (N-period highest high / lowest low) define the recent price
range. A breakout above the upper channel means price has exceeded all prices
over the last N bars — a significant momentum event. The turtle traders used a
variant of this system (20-day breakout for entry, 10-day for exit).

### Indicators

- **Upper band:** `max(High, n)` — resistance level.
- **Lower band:** `min(Low, n)` — support level.
- **Middle band:** `(upper + lower) / 2`.
- **Signal:** `Close > Upper_band` → long entry. `Close < Lower_band` → short.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| Entry channel | 20, 40, 55 bars | Original turtle: 20-day |
| Exit channel | 10, 15, 20 bars | Shorter than entry |
| Buffer | 0, 0.1× ATR | Avoids false breakouts |
| Stop | Opposite channel or 2× ATR |  |

On 5-min bars: 20-bar channel = 100 minutes ≈ 1.7 hours of history.
On 15-min bars: 20-bar channel = 300 minutes = 5 hours.

### Brute-Force Parameter Search Space

```
entry_channel  : [10, 15, 20, 30, 40, 55]
exit_channel   : [5, 8, 10, 15, 20]
constraint     : exit_channel < entry_channel
buffer_atr     : [0.0, 0.1, 0.2]
timeframe      : [5min, 15min, 1h]
```

### Instrument Suitability

XAUUSD and BTCUSD (strong momentum breakouts). EURUSD during London/NY overlap.
Avoid on thin altcoins.

---

## TF-18 — N-Period High/Low Breakout (Simple Breakout)

### Hypothesis

Similar to Donchian but simpler in exit logic. Price exceeding the highest high
of the last N bars signals that buyers have overcome all prior sellers within
that window — a sign of renewed momentum. More flexible than Donchian in that
the exit can be a fixed stop or time-based rather than a channel-based stop.

### Indicators

- **N-bar high:** `max(High, n)` — breakout level.
- **N-bar low:** `min(Low, n)` — breakdown level.
- **Volume confirmation (optional):** Volume on breakout bar > rolling average.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Breakout window (N) | 10, 20, 30, 50 bars |
| Confirmation | Close > N-bar high (not just tick) |
| Stop | N-bar low or 1.5× ATR |
| Target | Fixed R:R 1.5–2.0 or next structural resistance |

### Brute-Force Parameter Search Space

```
breakout_n     : [5, 10, 15, 20, 30, 40, 50]
confirmation   : ["close", "tick"]
volume_filter  : [True, False]
atr_stop_mult  : [1.0, 1.5, 2.0, 2.5]
rr_ratio       : [1.0, 1.5, 2.0]
timeframe      : [5min, 15min]
```

---

## TF-19 — Momentum (ROC) Breakout

### Hypothesis

Rate of Change (ROC) measures the percentage change in price over N bars:
`ROC(n) = (Close / Close[n] − 1) × 100`. When ROC exceeds a positive threshold,
price is accelerating upward — an early-stage trend signal. ROC is a leading
indicator compared to MA crossovers since it measures price velocity directly.

### Indicators

- **ROC(n):** `((Close − Close[n]) / Close[n]) × 100`
- **Signal:** `ROC > threshold` → long; `ROC < −threshold` → short.
- **Trend filter (optional):** Only enter longs when longer-period ROC is also
  positive (e.g. ROC(60) > 0 to ensure momentum is not against a broader move).

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| ROC period | 5, 10, 20, 30 bars | On 5-min bars: 5 bars = 25 min |
| Threshold | 0.1%, 0.2%, 0.5% | Depends heavily on instrument |
| EURUSD typical ROC range | 0.05%–0.15% per 5-min bar | Use smaller thresholds |
| BTCUSD typical ROC range | 0.1%–0.5% per 5-min bar | Use larger thresholds |
| Exit | ROC returns to zero; or fixed holding period | |

### Brute-Force Parameter Search Space

```
roc_period       : [3, 5, 10, 15, 20, 30]
threshold_pct    : [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
long_roc_filter  : [None, 30, 60]    # longer-period ROC > 0
holding_bars     : [5, 10, 20, 30]   # fixed holding period exit
timeframe        : [1min, 5min]
```

> **Important:** Calibrate `threshold_pct` per instrument — EURUSD and XAGUSD
> have very small per-bar ROC; BTCUSD and ETHUSD have much larger ranges.
> Consider normalizing by ATR instead of a fixed percentage.

---

## TF-20 — Elder Impulse System

### Hypothesis

Alexander Elder's Impulse System combines a trend indicator (EMA slope) with a
momentum indicator (MACD histogram direction) to produce a bar-by-bar color code:
**green** (both bullish → buy), **red** (both bearish → sell), **blue/neutral**
(conflicting → wait). It is a filter that restricts trading to only the highest-
conviction directional bars, dramatically reducing noise.

### Indicators

- **EMA(period):** Trend direction. Bar is bullish when EMA is rising
  (`EMA[0] > EMA[1]`), bearish when falling.
- **MACD Histogram(fast, slow, signal):** Momentum direction. Bar is bullish
  when histogram is rising (`Hist[0] > Hist[1]`), bearish when falling.
- **Impulse color:**
  - Green: EMA rising AND histogram rising → strong bullish bar.
  - Red: EMA falling AND histogram falling → strong bearish bar.
  - Neutral: Mixed signals → avoid entry.

### Standard Parameters

| Parameter | Common values |
|---|---|
| EMA period | 13, 20, 26 |
| MACD | (12, 26, 9) or (8, 21, 5) |
| Entry | Buy on close of green bar after neutral period; short on red |
| Stop | Below most recent red bar (bull position) or 1.5× ATR |
| Exit | First neutral or opposite-colored bar |

### Entry Rules

- **Long:** Current bar is Green (EMA rising + MACD hist rising) after one or
  more Neutral bars. Enter on bar close.
- **Short:** Current bar is Red after Neutral bars. Enter on bar close.
- Avoid entering mid-sequence (e.g. 3rd consecutive green bar — momentum may
  be exhausted).

### Brute-Force Parameter Search Space

```
ema_period      : [10, 13, 20, 26]
macd_fast       : [8, 10, 12]
macd_slow       : [21, 24, 26]
macd_signal     : [7, 9]
entry_condition : ["first_colored_bar", "any_colored_bar"]
exit_condition  : ["first_neutral", "opposite_color"]
atr_stop_mult   : [1.0, 1.5, 2.0]
timeframe       : [5min, 15min]
```

Total combinations: ~4 × 3 × 3 × 2 × 2 × 2 × 3 × 2 = 1,728 per instrument.

### Instrument Suitability

All instruments. The Elder Impulse System is particularly robust on EURUSD and
XAUUSD where EMA trends are clean during active sessions.

---

## Cross-Strategy Considerations

### Recommended Brute-Force Optimization Protocol

When running parameter searches across these strategies, follow these guidelines
to avoid common pitfalls:

1. **Walk-forward validation:** Divide the available data into in-sample (train)
   and out-of-sample (test) windows. Use a rolling or expanding window. Never
   report only in-sample metrics.

2. **Minimum trade count filter:** Discard parameter sets that produce fewer
   than ~50 trades in the test window — insufficient statistical significance.

3. **Overfitting guard:** If more than one parameter set produces an exceptional
   Sharpe ratio (> 2.0) in-sample, be skeptical. The fewer the trades, the more
   likely it is data-fitted.

4. **Transaction cost model:** Always include at least a fixed spread/commission
   cost per trade. For EURUSD: 0.5–1.0 pip; XAUUSD: $0.10–$0.30; BTC: 0.05%.

5. **Objective metrics (prioritize in this order):**
   - Sharpe Ratio (annualized, > 1.0 out-of-sample)
   - Profit Factor (> 1.3)
   - Maximum Drawdown (< 20%)
   - Win Rate (less important than R:R × win rate combination)
   - Number of trades (signal frequency)

6. **Instrument-specific calibration:** Run optimization separately per
   instrument. Parameters that work on EURUSD rarely transfer to BTCUSD without
   adjustment.

### Suggested Evaluation Priority

Based on literature and practical evidence, the following strategies are
recommended as first candidates for experiment implementation:

| Priority | Strategy | Reason |
|---|---|---|
| 1 | TF-07 SuperTrend | Simple, adaptive, built-in stop, well-documented edge |
| 2 | TF-06 ADX + EMA | Regime filter + direction = robust combination |
| 3 | TF-05 EMA Cross + RSI | Very practical; low complexity; proven in live systems |
| 4 | TF-04 MACD + 200 EMA | Classic; strong institutional support |
| 5 | TF-20 Elder Impulse | High selectivity; reduces overtrading |
| 6 | TF-08 SuperTrend + VWAP + ADX | Multi-confirmation; best for Forex sessions |
| 7 | TF-17 Donchian Breakout | Turtle system heritage; well-studied edge |
| 8 | TF-15 EMA Pullback | High R:R; captures optimal entry within a trend |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
