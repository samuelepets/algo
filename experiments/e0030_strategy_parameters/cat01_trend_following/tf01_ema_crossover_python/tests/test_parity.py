"""Parity tests against the Rust sibling outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

RUST_DIR = Path(__file__).resolve().parents[1] / ".." / "tf01_ema_crossover"
PYTHON_OUTPUTS = Path(__file__).resolve().parents[1] / "outputs"
RUST_OUTPUTS = RUST_DIR / "outputs"


def _load_results(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def python_results() -> list[dict[str, str]]:
    path = PYTHON_OUTPUTS / "results.csv"
    if not path.is_file():
        pytest.skip("Python outputs/results.csv not generated yet")
    return _load_results(path)


@pytest.fixture(scope="module")
def rust_results() -> list[dict[str, str]]:
    path = RUST_OUTPUTS / "results.csv"
    if not path.is_file():
        pytest.skip("Rust outputs/results.csv not available")
    return _load_results(path)


def _key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        row["fast_ema"],
        row["slow_ema"],
        row["atr_stop_mult"],
        row["rr_ratio"],
        row["tf_min"],
    )


def test_results_row_count(python_results: list[dict[str, str]], rust_results: list[dict[str, str]]) -> None:
    assert len(python_results) == len(rust_results) == 3150


def test_results_numerical_parity(python_results: list[dict[str, str]], rust_results: list[dict[str, str]]) -> None:
    py_by_key = {_key(r): r for r in python_results}
    rs_by_key = {_key(r): r for r in rust_results}
    assert set(py_by_key) == set(rs_by_key)

    for key in rs_by_key:
        py = py_by_key[key]
        rs = rs_by_key[key]
        assert py["n_trades"] == rs["n_trades"]
        for field in ("sharpe", "profit_factor", "max_drawdown_r", "total_return"):
            py_v = float(py[field])
            rs_v = float(rs[field])
            tol = max(1e-6, abs(rs_v) * 1e-6)
            assert abs(py_v - rs_v) <= tol, f"{key} {field}: py={py_v} rust={rs_v}"


def test_top10_byte_identical() -> None:
    py_path = PYTHON_OUTPUTS / "top_params.json"
    rs_path = RUST_OUTPUTS / "top_params.json"
    if not py_path.is_file() or not rs_path.is_file():
        pytest.skip("top_params.json missing")
    assert py_path.read_bytes() == rs_path.read_bytes()


def test_top10_parity(python_results: list[dict[str, str]], rust_results: list[dict[str, str]]) -> None:
    py_top_path = PYTHON_OUTPUTS / "top_params.json"
    rs_top_path = RUST_OUTPUTS / "top_params.json"
    if not py_top_path.is_file() or not rs_top_path.is_file():
        pytest.skip("top_params.json missing")

    py_top = json.loads(py_top_path.read_text(encoding="utf-8"))
    rs_top = json.loads(rs_top_path.read_text(encoding="utf-8"))

    assert len(py_top) == len(rs_top) == 10
    for py_row, rs_row in zip(py_top, rs_top, strict=True):
        assert py_row["fast_ema"] == rs_row["fast_ema"]
        assert py_row["slow_ema"] == rs_row["slow_ema"]
        assert py_row["tf_min"] == rs_row["tf_min"]
        assert py_row["n_trades"] == rs_row["n_trades"]
        assert abs(py_row["sharpe"] - rs_row["sharpe"]) <= 1e-6


def test_walkforward_parity() -> None:
    py_path = PYTHON_OUTPUTS / "walkforward.csv"
    rs_path = RUST_OUTPUTS / "walkforward.csv"
    if not py_path.is_file() or not rs_path.is_file():
        pytest.skip("walkforward.csv missing")

    py_rows = _load_results(py_path)
    rs_rows = _load_results(rs_path)
    assert len(py_rows) == len(rs_rows) == 4

    for py, rs in zip(py_rows, rs_rows, strict=True):
        assert py["sel_fast"] == rs["sel_fast"]
        assert py["sel_slow"] == rs["sel_slow"]
        assert py["sel_tf"] == rs["sel_tf"]
        assert py["oos_n_trades"] == rs["oos_n_trades"]
        assert abs(float(py["oos_sharpe"]) - float(rs["oos_sharpe"])) <= 1e-6
