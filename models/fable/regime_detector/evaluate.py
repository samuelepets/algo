"""Sanity metrics for regime labels (statistical coherence checks, §7 of the doc)."""

import numpy as np
import pandas as pd


def _run_lengths(labels: pd.Series) -> pd.Series:
    change = labels != labels.shift(1)
    return labels.groupby(change.cumsum()).size()


def summarize(bars: pd.DataFrame, regimes: pd.DataFrame) -> str:
    df = bars.join(regimes[["direction", "volatility"]])
    ret = df["ret"]
    lines: list[str] = []

    lines.append("Direction share (% of bars):")
    for label, share in df["direction"].value_counts(normalize=True).items():
        lines.append(f"  {label:<10} {share:6.1%}")
    lines.append("Volatility share (% of bars):")
    for label, share in df["volatility"].value_counts(normalize=True).items():
        lines.append(f"  {label:<10} {share:6.1%}")

    changes = int((df["direction"] != df["direction"].shift(1)).sum()) - 1
    n_days = df.index.normalize().nunique()
    durations = _run_lengths(df["direction"])
    lines.append(f"Direction regime changes: {changes} ({changes / n_days:.2f}/day)")
    lines.append(
        f"Regime duration (H1 bars): median {durations.median():.0f}, mean {durations.mean():.1f}"
    )

    trend_mask = df["direction"].isin(["TREND_UP", "TREND_DOWN"])
    range_mask = df["direction"] == "RANGE"
    lines.append(
        "Mean |H1 return|: trend "
        f"{ret[trend_mask].abs().mean():.3e} vs range {ret[range_mask].abs().mean():.3e}"
    )
    ac_trend = ret[trend_mask].autocorr(1)
    ac_range = ret[range_mask].autocorr(1)
    lines.append(f"Return autocorr(1): trend {ac_trend:+.3f} vs range {ac_range:+.3f}")

    per_bar_ret = np.where(df["direction"] == "TREND_DOWN", -ret, ret)
    in_trend = pd.Series(per_bar_ret, index=df.index)[trend_mask]
    lines.append(f"Signed return inside trends (sum): {in_trend.sum():+.4f} log-return")

    vol_high = ret[df["volatility"] == "VOL_HIGH"].std()
    vol_low = ret[df["volatility"] == "VOL_LOW"].std()
    lines.append(f"Realized H1 vol: VOL_HIGH {vol_high:.3e} vs VOL_LOW {vol_low:.3e}")

    return "\n".join(lines)
