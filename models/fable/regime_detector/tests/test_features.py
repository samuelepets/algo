import numpy as np
import pandas as pd

from features import compute_features, efficiency_ratio


def make_bars(close: np.ndarray) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=len(close), freq="1h")
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.0005,
            "low": close - 0.0005,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )
    df["time_close"] = df.index + pd.Timedelta(hours=1)
    return df


def test_efficiency_ratio_is_one_for_monotonic_series():
    close = pd.Series(np.linspace(1.0, 1.1, 60))
    er = efficiency_ratio(close, period=20)
    assert np.allclose(er.dropna(), 1.0)


def test_efficiency_ratio_low_for_oscillating_series():
    close = pd.Series(1.0 + 0.001 * np.tile([1.0, -1.0], 40))
    er = efficiency_ratio(close, period=20)
    assert (er.dropna() < 0.15).all()


def test_no_lookahead_features_match_on_truncated_prefix():
    # Features computed on a prefix must equal the same rows computed on the
    # full series: nothing at bar t may depend on bars after t.
    rng = np.random.default_rng(42)
    close = 1.10 + np.cumsum(rng.normal(0, 1e-4, 500))
    full = compute_features(make_bars(close))
    prefix = compute_features(make_bars(close[:300]))
    cols = ["atr", "adx", "er", "ema_fast", "ema_slow", "slope_norm", "bb_width", "atr_pct"]
    pd.testing.assert_frame_equal(full[cols].iloc[:300], prefix[cols])
