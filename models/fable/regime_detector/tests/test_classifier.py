import numpy as np
import pandas as pd

from classifier import RANGE, TREND_UP, VOL_HIGH, VOL_NORM, Thresholds, classify


def make_features(adx, er=0.5, ema_fast=1.1, ema_slow=1.0, slope=0.5, atr_pct=0.5):
    n = len(adx)
    idx = pd.date_range("2025-01-01", periods=n, freq="1h")
    return pd.DataFrame(
        {
            "adx": adx,
            "er": [er] * n,
            "ema_fast": [ema_fast] * n,
            "ema_slow": [ema_slow] * n,
            "slope_norm": [slope] * n,
            "atr_pct": atr_pct if isinstance(atr_pct, list) else [atr_pct] * n,
            "time_close": idx + pd.Timedelta(hours=1),
        },
        index=idx,
    )


def test_trend_requires_confirmation():
    # ADX jumps above the enter threshold: the label must switch only after
    # confirm_bars consecutive trend signals.
    feats = make_features(adx=[10, 10, 30, 30, 30, 30])
    out = classify(feats, Thresholds(confirm_bars=3))
    assert list(out["direction"]) == [RANGE, RANGE, RANGE, RANGE, TREND_UP, TREND_UP]


def test_short_blip_does_not_switch():
    feats = make_features(adx=[10, 30, 30, 10, 10, 10])
    out = classify(feats, Thresholds(confirm_bars=3))
    assert list(out["direction"]) == [RANGE] * 6


def test_hysteresis_keeps_label_in_ambiguous_zone():
    # After entering a trend, ADX in (exit, enter) is ambiguous: keep TREND_UP.
    feats = make_features(adx=[30, 30, 30, 22, 22, 22])
    out = classify(feats, Thresholds(confirm_bars=1))
    assert list(out["direction"]) == [TREND_UP] * 6


def test_exit_to_range_below_exit_threshold():
    feats = make_features(adx=[30, 30, 30, 15, 15, 15])
    out = classify(feats, Thresholds(confirm_bars=2))
    assert list(out["direction"])[-1] == RANGE


def test_vol_hysteresis():
    # Enters VOL_HIGH above 0.80, stays while above 0.70, exits below.
    feats = make_features(adx=[10] * 5, atr_pct=[0.5, 0.85, 0.75, 0.75, 0.65])
    out = classify(feats, Thresholds())
    assert list(out["volatility"]) == [VOL_NORM, VOL_HIGH, VOL_HIGH, VOL_HIGH, VOL_NORM]


def test_nan_features_keep_previous_state():
    feats = make_features(adx=[np.nan, np.nan, 10, 10])
    out = classify(feats, Thresholds())
    assert list(out["direction"]) == [RANGE] * 4
    assert out["confidence"].iloc[0] == 0.0
