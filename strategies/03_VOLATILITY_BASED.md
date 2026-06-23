# Category 3 — Volatility-Based: Top 15 Strategies

Detailed research document for the **Volatility-Based** strategy family.
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
| VB-01 | ATR Expansion Entry | Low | 1-min, 5-min |
| VB-02 | Opening Range Breakout (ORB) | Low | 5-min |
| VB-03 | Volatility Squeeze (Keltner + Bollinger) | Medium | 5-min, 15-min |
| VB-04 | Volatility Regime Filter | Low | Any |
| VB-05 | Bollinger Band Width Expansion Signal | Low | 5-min, 15-min |
| VB-06 | Inside Bar / Narrow Range Breakout | Low | 5-min, 15-min |
| VB-07 | True Range Spike Detection | Low | 1-min, 5-min |
| VB-08 | Pre-Session Consolidation Breakout | Medium | 5-min |
| VB-09 | ATR Channel Breakout | Low | 5-min, 15-min |
| VB-10 | Chandelier Exit System | Low | 5-min, 15-min |
| VB-11 | First Candle of Session Breakout | Low | 5-min |
| VB-12 | Historical Volatility Percentile Filter | Medium | Any |
| VB-13 | Gap Detection and Trade | Medium | 5-min |
| VB-14 | Session High/Low Breakout | Low | 5-min, 15-min |
| VB-15 | Compression-to-Expansion (NR7) | Low | 5-min, 15-min |

---

## VB-01 — ATR Expansion Entry

### Hypothesis

Volatility is mean-reverting and clustered. When ATR drops to a multi-period
low, the market is compressing into a period of unusually low volatility — a
coiling spring. The first large bar that breaks the recent range after an ATR
contraction tends to be the beginning of a sustained directional move. The
direction is provided by a trend filter; ATR expansion gives the timing signal.

### Indicators

- **ATR(period):** Average True Range — measures per-bar volatility.
- **ATR percentile:** `percentile_rank(ATR, lookback)` — current ATR relative
  to recent history.
- **Trend filter:** EMA slope or ADX direction — provides directional bias.
- **Signal:** ATR drops to low percentile, then current bar exceeds recent
  range → enter in trend direction.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| ATR period | 14 | Standard |
| ATR lookback (percentile) | 50, 100 bars | Window for computing low |
| ATR low threshold | < 20th percentile | When ATR is historically compressed |
| Expansion trigger | Current ATR > 1.5× ATR minimum | |
| Direction | EMA(50) slope or ADX +DI/−DI | |
| Stop | 1.5–2.0× ATR from entry | |

### Entry Rules

- **Long:** ATR(14) at Nth-percentile low over last M bars; current bar closes
  above N-period high; EMA slope is positive → enter long.
- **Short:** Inverse.

### Brute-Force Parameter Search Space

```
atr_period       : [10, 14, 20]
atr_lookback     : [30, 50, 100]
atr_percentile   : [10, 20, 30]       # ATR must be below this percentile
expansion_mult   : [1.3, 1.5, 2.0]   # current ATR > mult × ATR min
trend_ema        : [20, 50, 100]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [1min, 5min, 15min]
```

### Instrument Suitability

All instruments. Particularly effective on BTCUSD and XAUUSD where volatility
contractions before large moves are common and pronounced.

---

## VB-02 — Opening Range Breakout (ORB)

### Hypothesis

The opening range (first N minutes of the session) captures the initial price
discovery. When price breaks out of this range, directional momentum has been
established by the session's dominant participants. The first breakout tends
to continue in the direction of the break, especially during high-activity
sessions (London open, NY open).

### Indicators

- **Opening range high (ORH):** High of the first N minutes after session open.
- **Opening range low (ORL):** Low of the first N minutes.
- **Breakout signal:** First close above ORH (long) or below ORL (short).
- **Volume confirmation (optional):** Breakout bar volume > rolling average.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| OR duration | 5, 15, 30 minutes | 15 min is most common for Forex |
| Buffer | 0, 0.1× ATR(14) | Avoids false prints |
| Stop | ORL (for long) or ORH (for short) | Opposite side of range |
| Target | 1.0–2.0× range width projected | Measured move |
| Session | London 08:00 EET, NY 13:00 EET | EET per corpus convention |

### Entry Rules

- **Long:** First bar close above ORH + buffer after range completes.
- **Short:** First bar close below ORL − buffer.
- Only take the first signal per session (avoid re-entries after a failed ORB).

### Exit Rules

- Target: ORH + (ORH − ORL) × multiplier.
- Stop: ORL (opposite side of range).
- Time exit: close position by end of session.

### Brute-Force Parameter Search Space

```
or_duration_min  : [5, 10, 15, 30, 60]
buffer_atr_mult  : [0.0, 0.05, 0.10, 0.20]
stop_type        : ["opposite_range", "atr_stop"]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_mult      : [1.0, 1.5, 2.0]       # multiples of range width
volume_filter    : [True, False]
session          : ["london", "ny", "both"]
timeframe        : [1min, 5min]
```

Total combinations: ~5 × 4 × 2 × 3 × 3 × 2 × 3 × 2 = 4,320 per instrument.

### Instrument Suitability

| Instrument | Suitability | Notes |
|---|---|---|
| EURUSD | High | London (08:00 EET) and NY (13:00 EET) sessions produce strong ORBs |
| XAUUSD | High | NY open (13:00 EET) is particularly powerful |
| BTCUSD | Medium | No natural session; arbitrary anchor reduces reliability |
| XAGUSD | Medium | Valid during NY session; thinner than gold |

---

## VB-03 — Volatility Squeeze (Keltner + Bollinger)

### Hypothesis

When Bollinger Bands contract inside Keltner Channels, it signals an
unusually compressed volatility state — the market is coiling before a large
directional move. The "squeeze" ends when BB bands expand back outside the
Keltner Channels. The direction of the first bar after the squeeze releases
is informed by momentum (MACD histogram direction or ROC sign).

### Indicators

- **Bollinger Bands(bb_period, bb_sigma):** Price-based standard deviation bands.
- **Keltner Channels(kc_period, kc_mult):** ATR-based bands around EMA.
- **Squeeze condition:** All four BB bands are inside the Keltner Channel bands.
- **Momentum:** MACD histogram or ROC(n) sign at release — determines direction.
- **Release signal:** First bar where BB bands extend outside Keltner.

### Standard Parameters

| Parameter | Common values | Notes |
|---|---|---|
| BB period/σ | 20, 2.0 | Standard BB |
| KC period | 20 | Same period as BB |
| KC ATR mult | 1.5 | Standard squeeze definition |
| Momentum | MACD histogram(12,26,9) | Positive = long; negative = short |
| Stop | 1.5× ATR from entry | |

### Brute-Force Parameter Search Space

```
bb_period        : [14, 20, 30]
bb_sigma         : [1.5, 2.0, 2.5]
kc_period        : [14, 20]
kc_atr_mult      : [1.0, 1.5, 2.0]
momentum_type    : ["macd_hist", "roc", "close_vs_midpoint"]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

### Instrument Suitability

Very popular on BTCUSD and ETHUSD where consolidation periods before large
moves are frequent. Also effective on XAUUSD. Less reliable on EURUSD which
tends to trend more continuously without clear squeezes.

---

## VB-04 — Volatility Regime Filter

### Hypothesis

Different volatility regimes favor different strategies. Low-volatility regimes
favor mean-reversion (price oscillates around a mean); high-volatility regimes
favor trend-following (momentum moves sustain longer). Classifying the current
regime using ATR percentile or realized volatility allows adaptive strategy
selection — a meta-filter rather than a standalone signal.

### Indicators

- **Rolling ATR percentile:** `percentile_rank(ATR(14), lookback_bars)`.
- **Realized volatility:** Standard deviation of log-returns over N bars, annualized.
- **Regime classification:**
  - Low vol: ATR < 30th percentile → favor mean-reversion.
  - High vol: ATR > 70th percentile → favor trend-following.
  - Medium vol: 30th–70th percentile → use combined signals.

### Standard Parameters

| Parameter | Common values |
|---|---|
| ATR period | 14 |
| Percentile lookback | 100, 200, 500 bars |
| Low-vol threshold | < 25th, < 30th percentile |
| High-vol threshold | > 70th, > 75th percentile |

### Usage

Apply as a filter on top of any other strategy:
- In low-vol regime: enable mean-reversion strategies; disable trend strategies.
- In high-vol regime: enable trend-following; disable mean-reversion.
- In medium regime: apply both with reduced position size.

### Brute-Force Parameter Search Space

```
atr_period       : [10, 14, 20]
percentile_window: [50, 100, 200, 500]
low_vol_thresh   : [20, 25, 30]
high_vol_thresh  : [70, 75, 80]
strategy_on_low  : ["mean_reversion", "none", "both"]
strategy_on_high : ["trend", "none", "both"]
timeframe        : [5min, 15min, 1h]
```

---

## VB-05 — Bollinger Band Width Expansion Signal

### Hypothesis

Bollinger Band Width (BBW) = `(upper − lower) / middle` measures the relative
width of the bands. When BBW contracts to its lowest point in N bars and then
begins expanding, it signals the start of a volatility expansion and potential
trend move. This is a simpler proxy for the squeeze concept (VB-03) that can
be used without Keltner Channels.

### Indicators

- **BBW(period, σ):** Normalized band width.
- **BBW percentile:** `percentile_rank(BBW, lookback)`.
- **Expansion signal:** BBW rising from its lowest point in N bars.
- **Direction:** First close above/below midpoint on expansion bar.

### Brute-Force Parameter Search Space

```
bb_period        : [10, 14, 20, 30]
bb_sigma         : [1.5, 2.0, 2.5]
bbw_lookback     : [20, 50, 100]
bbw_low_pct      : [5, 10, 20]          # BBW must be at or below this percentile
direction_filter : ["close_vs_mid", "ema_slope", "roc"]
atr_stop_mult    : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VB-06 — Inside Bar / Narrow Range Breakout

### Hypothesis

An inside bar is a bar whose range (High − Low) is entirely within the
prior bar's range. It signals a pause in directional movement. A breakout
above the inside bar high or below its low — especially after multiple
consecutive inside bars — is a high-probability entry because it represents
the first commitment in either direction after a period of indecision.

### Indicators

- **Inside bar:** `High[0] < High[−1] AND Low[0] > Low[−1]`.
- **Narrow Range bars:** NR4 = narrowest range bar in 4 bars; NR7 = in 7 bars.
- **Breakout:** Close above inside bar high (long) or below inside bar low (short).
- **Confirmation:** Volume above average on breakout bar (optional).

### Standard Parameters

| Parameter | Common values |
|---|---|
| Pattern type | Inside bar, NR4, NR7 |
| Consecutive bars | 1, 2, 3 inside bars before entry |
| Breakout buffer | 0, 0.1× ATR |
| Stop | Opposite side of inside bar (tight) or 1.5× ATR |
| Target | 1.5–2.0× range of inside bar from breakout level |

### Brute-Force Parameter Search Space

```
pattern_type     : ["inside_bar", "nr4", "nr7"]
consecutive      : [1, 2, 3]
buffer_atr_mult  : [0.0, 0.05, 0.10]
stop_type        : ["inside_bar_opposite", "atr_stop"]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_mult      : [1.0, 1.5, 2.0]
volume_filter    : [True, False]
timeframe        : [5min, 15min]
```

---

## VB-07 — True Range Spike Detection

### Hypothesis

A bar with an unusually large True Range (e.g. > 3× ATR(14)) represents a
volatility spike — an extreme event often driven by news or a large order.
The direction of the spike bar's close tends to establish short-term
directional momentum. Alternatively, the spike may represent exhaustion (if
it closes against its opening direction), offering a fade entry. Two modes:
continuation (trade the spike direction) and fade (trade against it).

### Indicators

- **True Range:** `max(High − Low, |High − Close[−1]|, |Low − Close[−1]|)`.
- **ATR(period):** Rolling average of True Range.
- **Spike ratio:** `True_Range / ATR` — spike if ratio > threshold.
- **Signal:** Ratio > threshold → enter on next bar open.
- **Direction:** Continuation = same as spike bar; Fade = opposite.

### Brute-Force Parameter Search Space

```
atr_period       : [10, 14, 20]
spike_mult       : [2.0, 2.5, 3.0, 4.0]    # TR / ATR threshold
mode             : ["continuation", "fade"]
entry_timing     : ["next_open", "next_close"]
atr_stop_mult    : [1.0, 1.5, 2.0]
max_hold_bars    : [3, 5, 10]
timeframe        : [1min, 5min]
```

### Instrument Suitability

BTCUSD and ETHUSD (frequent volatility spikes); XAUUSD during news events.
EURUSD around major economic releases. Spike detection on 1-min bars captures
immediate momentum; 5-min bars filter some noise.

---

## VB-08 — Pre-Session Consolidation Breakout

### Hypothesis

The period before a major session opens (Asian session for EURUSD, pre-London
consolidation 06:00–08:00 EET) tends to be low-volatility range-bound trading.
The subsequent session open breaks out of this pre-session range with high
probability of follow-through. This is a context-specific ORB using the
pre-session range rather than the opening minutes of the session.

### Indicators

- **Pre-session range:** High and low of bars from `pre_start` to `session_open`.
- **Session open:** London = 08:00 EET; NY = 13:00 EET.
- **Breakout:** First close after session open beyond pre-session range.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Pre-session window | 04:00–08:00 EET (London pre-session), 10:00–13:00 EET (NY) |
| Buffer | 0.1× ATR |
| Stop | Opposite side of pre-session range |
| Target | 1.0–2.0× pre-session range width |

### Brute-Force Parameter Search Space

```
pre_session_start: ["04:00", "05:00", "06:00", "07:00"]   # EET
session_open     : ["08:00", "13:00"]                       # EET
buffer_atr_mult  : [0.0, 0.05, 0.10, 0.20]
stop_type        : ["opposite_range", "atr_stop"]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_mult      : [1.0, 1.5, 2.0]
timeframe        : [5min, 15min]
```

---

## VB-09 — ATR Channel Breakout

### Hypothesis

An ATR-based channel defines the expected price range around a central MA:
`MA ± k × ATR`. When price breaks above the upper channel or below the lower
channel, it has moved beyond the statistically expected range and is showing
abnormal directional strength. Unlike Keltner Channels used for mean-reversion,
here the channel break is treated as a continuation signal.

### Indicators

- **MA(period):** Channel center.
- **Upper channel:** `MA + k × ATR(atr_period)`.
- **Lower channel:** `MA − k × ATR(atr_period)`.
- **Signal:** Close above upper channel → long; close below lower channel → short.

### Brute-Force Parameter Search Space

```
ma_period        : [20, 50, 100]
atr_period       : [10, 14]
channel_mult     : [1.5, 2.0, 2.5, 3.0]
ma_type          : ["ema", "sma"]
atr_stop_mult    : [1.0, 1.5, 2.0]
exit_type        : ["trailing_atr", "opposite_channel", "fixed_rr"]
rr_ratio         : [1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

---

## VB-10 — Chandelier Exit System

### Hypothesis

The Chandelier Exit places a trailing stop at the highest high (for a long
position) minus N× ATR, or the lowest low plus N× ATR for a short. It
"hangs from the chandelier" of the highest high achieved since entry. It is
primarily an exit and trailing stop mechanism, but can also serve as an entry
signal when price reverses from the Chandelier level.

### Indicators

- **Chandelier Long Stop:** `max(High, period) − atr_mult × ATR(atr_period)`.
- **Chandelier Short Stop:** `min(Low, period) + atr_mult × ATR(atr_period)`.
- **Entry signal:** Chandelier flips from long to short (or vice versa).

### Standard Parameters

| Parameter | Common values |
|---|---|
| Lookback period | 22 (1-month equivalent on daily) |
| ATR period | 22 |
| ATR multiplier | 3.0 (default) |
| Alternative | (14, 2.0), (20, 2.5) |

### Usage Modes

1. **Exit only:** Enter via another strategy; use Chandelier as the trailing stop.
2. **Flip entry:** Enter long when short Chandelier flips to long; enter short
   on the reverse.

### Brute-Force Parameter Search Space

```
lookback_period  : [10, 14, 20, 22, 30]
atr_period       : [10, 14, 20]
atr_mult         : [1.5, 2.0, 2.5, 3.0, 3.5]
mode             : ["exit_only", "flip_entry"]
timeframe        : [5min, 15min]
```

---

## VB-11 — First Candle of Session Breakout

### Hypothesis

The first completed bar of a session (5-min, 15-min, or 1-h depending on
timeframe) often defines the directional bias for the next 1–4 hours. A strong
directional first bar (large body, close in the upper/lower 20% of the bar)
signals early session momentum. Entering in the direction of the first bar's
close produces a timing advantage over waiting for the full opening range.

### Indicators

- **First session bar:** The first complete bar after session open.
- **Bar strength:** Body size as % of total range; close position within range.
- **Signal:** Strong bullish first bar (body > 60% of range, close in top 20%) → long.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Session open | 08:00 EET (London), 13:00 EET (NY) |
| First bar TF | 5-min, 15-min, 1-h |
| Body pct threshold | > 60%, > 70% of total range |
| Close position | Top/bottom 20%–30% of bar range |
| Stop | Low of first bar (long) or high (short) |
| Target | 1.5–2.0× first bar range |

### Brute-Force Parameter Search Space

```
session          : ["london", "ny"]
bar_tf           : ["5min", "15min", "1h"]
body_pct_min     : [0.50, 0.60, 0.70]
close_pct_min    : [0.70, 0.80, 0.90]   # close in top/bottom pct of bar
atr_stop_mult    : [1.0, 1.5]
target_bar_mult  : [1.0, 1.5, 2.0]
timeframe        : [1min, 5min]          # entry TF (lower than bar_tf)
```

---

## VB-12 — Historical Volatility Percentile Filter

### Hypothesis

Historical Volatility (HV) — the annualized standard deviation of log-returns
over a rolling window — provides a more stationary measure of market regime
than ATR alone. When HV is in the lowest X percentile of its distribution over
a long lookback period, volatility is historically compressed and a significant
expansion is probable. This filter conditions entries from other strategies to
only fire during or immediately after low-volatility regimes.

### Indicators

- **HV(n):** `std(log_returns, n) × sqrt(bars_per_year)`.
- **HV percentile:** `percentile_rank(HV, long_lookback)`.
- **Signal:** `HV_percentile < threshold` → volatility is compressed; heighten
  alertness for breakout conditions.

### Usage

Apply as a meta-filter (same as VB-04 but using HV instead of ATR).

### Brute-Force Parameter Search Space

```
hv_period        : [20, 30, 60]
hv_lookback      : [100, 200, 500]
low_vol_threshold: [10, 20, 30]      # HV percentile thresholds
strategy_action  : ["enter_breakout", "enter_reversion", "filter_only"]
timeframe        : [5min, 15min]
```

---

## VB-13 — Gap Detection and Trade

### Hypothesis

A gap occurs when the current bar's open is significantly different from the
prior bar's close (relevant mainly for instruments with sessions or low-liquidity
periods). Gaps can be traded in two modes: (1) Gap fill — price reverts to
close the gap, especially for small gaps; (2) Gap continuation — a large gap
on high momentum tends to continue, especially gap-and-go after a consolidation.

### Indicators

- **Gap size:** `(Open − Close[−1]) / ATR(14)` — gap in ATR units.
- **Gap direction:** Positive = upward gap; negative = downward gap.
- **Gap fill mode:** Price returns to prior close within N bars → fade the gap.
- **Continuation mode:** Price breaks beyond gap open → trade the gap direction.

> **Note:** Gaps are most relevant for EURUSD on Monday open (weekend gap)
> and around major news events. BTCUSD rarely gaps due to 24-h trading.

### Brute-Force Parameter Search Space

```
gap_atr_min      : [0.3, 0.5, 1.0]    # minimum gap to trade
mode             : ["fill", "continuation"]
fill_bars_max    : [5, 10, 20]         # bars to fill before gap expires
continuation_conf: ["same_dir_bar", "any_bar"]
atr_stop_mult    : [0.5, 1.0, 1.5]
timeframe        : [1min, 5min]
```

---

## VB-14 — Session High/Low Breakout

### Hypothesis

The high and low of the prior session act as significant reference levels for
the current session. Institutions use prior session extremes as stop clusters
and benchmark levels. Breaking above the prior session high signals a
continuation of bullish momentum beyond the prior session's peak; breaking below
the prior session low signals bearish expansion.

### Indicators

- **Prior session high:** Max high of the prior trading session.
- **Prior session low:** Min low of the prior trading session.
- **Signal:** Close above prior session high → long; below prior session low → short.
- **Confirmation:** Volume spike or ATR expansion on breakout bar.

### Standard Parameters

| Parameter | Common values |
|---|---|
| Session definition | London (08:00–16:00 EET), NY (13:00–21:00 EET) |
| Lookback | 1 prior session or prior day |
| Buffer | 0.1× ATR |
| Stop | Opposite side of prior session range |
| Target | 1.0–1.5× prior session range projected |

### Brute-Force Parameter Search Space

```
reference_session: ["prior_london", "prior_ny", "prior_day"]
buffer_atr_mult  : [0.0, 0.05, 0.10, 0.20]
stop_type        : ["opposite_level", "atr_stop"]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_mult      : [1.0, 1.5, 2.0]
volume_filter    : [True, False]
timeframe        : [5min, 15min]
```

---

## VB-15 — Compression-to-Expansion (NR7)

### Hypothesis

The NR7 pattern identifies the narrowest-range bar in the last 7 bars
(bar range = High − Low). Historically, the bar immediately following an NR7
has a higher-than-average probability of being a large directional bar — the
coiled spring releases. Trading the breakout of the NR7 bar's high or low
captures this volatility expansion.

### Indicators

- **NR7 bar:** Bar whose range is the smallest of the past 7 bars.
- **Breakout:** Next bar closes above NR7 high (long) or below NR7 low (short).
- **Confirmation:** Trend direction (EMA slope or prior bias) for directionality.
- **NR4 variant:** Same concept with 4-bar lookback — fires more frequently.

### Standard Parameters

| Parameter | Common values |
|---|---|
| NR lookback | 4 (NR4), 7 (NR7) |
| Breakout buffer | 0, 0.1× ATR |
| Stop | Opposite side of NR bar |
| Target | 1.5–2.0× NR bar range |

### Brute-Force Parameter Search Space

```
nr_lookback      : [4, 5, 7, 10]
buffer_atr_mult  : [0.0, 0.05, 0.10]
direction_filter : ["none", "ema_slope", "adx_di"]
atr_stop_mult    : [1.0, 1.5, 2.0]
target_mult      : [1.0, 1.5, 2.0, 2.5]
timeframe        : [5min, 15min]
```

### Instrument Suitability

All instruments. NR7 is most reliable when followed by a clear trend structure.
Works well on EURUSD during active sessions and BTCUSD during consolidation
phases.

---

## Cross-Strategy Considerations

### Key Principle: Direction Requires a Separate Signal

Volatility-based strategies tell you **when** to trade (when volatility is
compressing or expanding), not **what direction** to trade. Always combine with
a directional filter:

| Directional filter | Source |
|---|---|
| EMA slope | Category 1: Trend-Following |
| ADX +DI/−DI | TF-06 |
| Prior session trend | VB-14 |
| Momentum (ROC) | TF-19 |
| MACD histogram | TF-03, VB-03 |

### Recommended Evaluation Priority

| Priority | Strategy | Reason |
|---|---|---|
| 1 | VB-02 Opening Range Breakout | Most studied; strong institutional basis |
| 2 | VB-03 Volatility Squeeze | Identifies the best pre-breakout setups |
| 3 | VB-01 ATR Expansion Entry | Adaptive; works across all instruments |
| 4 | VB-15 NR7 Compression | Simple; high signal-to-noise ratio |
| 5 | VB-06 Inside Bar Breakout | Objective; easy to implement |
| 6 | VB-08 Pre-Session Breakout | High-quality session-specific signal |
| 7 | VB-04 Volatility Regime Filter | Meta-filter; improves all other strategies |
| 8 | VB-14 Session High/Low Breakout | Institutional level breakout |

---

*Last updated: Phase 1 — initial research. Extend with backtesting results as
experiments are implemented.*
