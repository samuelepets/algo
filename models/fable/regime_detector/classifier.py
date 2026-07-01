"""Stage 1 rule-based regime classifier with hysteresis (dual thresholds +
confirmation delay), as specified in MARKET_REGIME_DETECTION.md."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

TREND_UP = "TREND_UP"
TREND_DOWN = "TREND_DOWN"
RANGE = "RANGE"
VOL_HIGH = "VOL_HIGH"
VOL_NORM = "VOL_NORM"
VOL_LOW = "VOL_LOW"

# Direction codes used by the vectorized path: +1 up, -1 down, 0 range.
AMBIGUOUS = 2  # keep-previous sentinel emitted by raw_signals
_LABEL = {1: TREND_UP, -1: TREND_DOWN, 0: RANGE}


@dataclass(frozen=True)
class Thresholds:
    adx_enter: float = 25.0
    adx_exit: float = 20.0
    er_enter: float = 0.30
    slope_min: float = 0.0  # in ATR units over SLOPE_LAG bars
    confirm_bars: int = 3
    vol_high_enter: float = 0.80
    vol_high_exit: float = 0.70
    vol_low_enter: float = 0.20
    vol_low_exit: float = 0.30


def raw_signals(features: pd.DataFrame, th: Thresholds) -> np.ndarray:
    """Instantaneous direction signal per bar as int8 codes.

    NaN features never satisfy a comparison, so warmup bars fall through to
    AMBIGUOUS (keep previous state), matching the state-machine contract.
    """
    adx = features["adx"].to_numpy(dtype=np.float64)
    er = features["er"].to_numpy(dtype=np.float64)
    ema_fast = features["ema_fast"].to_numpy(dtype=np.float64)
    ema_slow = features["ema_slow"].to_numpy(dtype=np.float64)
    slope = features["slope_norm"].to_numpy(dtype=np.float64)

    trending = (adx > th.adx_enter) & (er > th.er_enter)
    raw = np.full(len(features), AMBIGUOUS, dtype=np.int8)
    raw[adx < th.adx_exit] = 0
    raw[trending & (ema_fast > ema_slow) & (slope > th.slope_min)] = 1
    raw[trending & (ema_fast < ema_slow) & (slope < -th.slope_min)] = -1
    return raw


def confirm(raw: np.ndarray, confirm_bars: int) -> tuple[np.ndarray, np.ndarray]:
    """Commit a direction change only after `confirm_bars` consecutive signals.

    Returns (direction codes, bars_in_regime).
    """
    n = len(raw)
    out = np.empty(n, dtype=np.int8)
    ages = np.empty(n, dtype=np.int64)
    current = 0  # start in RANGE
    candidate = AMBIGUOUS
    count = 0
    age = 0
    for i in range(n):
        sig = raw[i]
        if sig == AMBIGUOUS or sig == current:
            candidate, count = AMBIGUOUS, 0
        else:
            if sig == candidate:
                count += 1
            else:
                candidate, count = sig, 1
            if count >= confirm_bars:
                current = sig
                age = count - 1  # regime effectively started at the first signal
                candidate, count = AMBIGUOUS, 0
        age += 1
        out[i] = current
        ages[i] = age
    return out, ages


def _vol_state(prev: str, pct: float, th: Thresholds) -> str:
    if np.isnan(pct):
        return prev
    if prev == VOL_HIGH:
        if pct >= th.vol_high_exit:
            return VOL_HIGH
    elif prev == VOL_LOW:
        if pct <= th.vol_low_exit:
            return VOL_LOW
    if pct > th.vol_high_enter:
        return VOL_HIGH
    if pct < th.vol_low_enter:
        return VOL_LOW
    return VOL_NORM


def classify(features: pd.DataFrame, th: Thresholds = Thresholds()) -> pd.DataFrame:
    """Label each bar with (direction, volatility) regimes."""
    codes, ages = confirm(raw_signals(features, th), th.confirm_bars)

    atr_pct = features["atr_pct"].to_numpy(dtype=np.float64)
    vols = np.empty(len(features), dtype=object)
    vol = VOL_NORM
    for i in range(len(features)):
        vol = _vol_state(vol, atr_pct[i], th)
        vols[i] = vol

    adx = features["adx"].to_numpy(dtype=np.float64)
    conf = np.where(codes == 0, (th.adx_enter - adx) / th.adx_enter, (adx - th.adx_exit) / th.adx_exit)
    conf = np.nan_to_num(np.clip(conf, 0.0, 1.0))

    return pd.DataFrame(
        {
            "time_close": features["time_close"].to_numpy(),
            "direction": [_LABEL[c] for c in codes],
            "volatility": vols,
            "bars_in_regime": ages,
            "confidence": conf,
        },
        index=features.index,
    )
