"""Parameter search spaces for GA optimization of S1–S3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GeneSpec:
    name: str
    low: float
    high: float
    kind: Literal["int", "float"] = "int"


SEARCH_SPACES: dict[str, list[GeneSpec]] = {
    "S1_connors_rsi2": [
        GeneSpec("sma_regime", 50, 500),
        GeneSpec("sma_exit", 3, 30),
        GeneSpec("rsi_period", 2, 10),
        GeneSpec("rsi_oversold", 3.0, 20.0, "float"),
        GeneSpec("rsi_overbought", 80.0, 97.0, "float"),
    ],
    "S2_ema_cross_rsi": [
        GeneSpec("fast_period", 3, 20),
        GeneSpec("slow_period", 10, 80),
        GeneSpec("rsi_period", 5, 21),
        GeneSpec("rsi_overbought", 60.0, 85.0, "float"),
        GeneSpec("rsi_oversold", 15.0, 40.0, "float"),
    ],
    "S3_rsi_centerline_ema": [
        GeneSpec("ema_period", 20, 200),
        GeneSpec("rsi_period", 5, 21),
        GeneSpec("centerline", 45.0, 55.0, "float"),
    ],
}


def genome_length(strategy_key: str) -> int:
    return len(SEARCH_SPACES[strategy_key])


def decode(genome: list[float], strategy_key: str) -> dict[str, int | float]:
    """Map a normalized genome in [0, 1] to strategy constructor kwargs."""
    specs = SEARCH_SPACES[strategy_key]
    if len(genome) != len(specs):
        raise ValueError(f"genome length {len(genome)} != {len(specs)} for {strategy_key}")

    params: dict[str, int | float] = {}
    for gene, spec in zip(genome, specs, strict=True):
        raw = spec.low + float(np_clip(gene, 0.0, 1.0)) * (spec.high - spec.low)
        if spec.kind == "int":
            params[spec.name] = int(round(raw))
        else:
            params[spec.name] = float(raw)
    return params


def validate_params(strategy_key: str, params: dict[str, int | float]) -> bool:
    """Return False for parameter combinations that violate hard constraints."""
    if strategy_key == "S1_connors_rsi2":
        return (
            int(params["sma_regime"]) > int(params["sma_exit"])
            and float(params["rsi_oversold"]) < float(params["rsi_overbought"])
        )
    if strategy_key == "S2_ema_cross_rsi":
        return (
            int(params["fast_period"]) < int(params["slow_period"])
            and float(params["rsi_oversold"]) < float(params["rsi_overbought"])
        )
    if strategy_key == "S3_rsi_centerline_ema":
        return int(params["rsi_period"]) >= 2
    return True


def normalize_params(strategy_key: str, params: dict[str, int | float]) -> dict[str, int | float]:
    """Coerce loaded JSON values to the types expected by strategy constructors."""
    specs = {spec.name: spec for spec in SEARCH_SPACES[strategy_key]}
    out: dict[str, int | float] = {}
    for name, value in params.items():
        spec = specs[name]
        if spec.kind == "int":
            out[name] = int(round(value))
        else:
            out[name] = float(value)
    return out


def np_clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
