"""Unit and integration tests for Zeroshot trial verification loop."""
from pathlib import Path
import pytest

from zeroshot import (
    validate_zeroshot_graph,
    run_zeroshot_verification,
    ZeroshotRunResult,
    ZeroshotMetrics,
)
from zeroshot.runner import resolve_zeroshot_bin


REPO_ROOT = Path(__file__).resolve().parent.parent
ZEROSHOT_DIR = REPO_ROOT / "zeroshot"
GRAPHS_DIR = ZEROSHOT_DIR / "graphs"


def test_zeroshot_binary_resolved():
    bin_path = resolve_zeroshot_bin()
    assert Path(bin_path).exists()
    assert Path(bin_path).name in ("zeroshot", "zeroshot.js")


def test_zeroshot_graph_validation():
    graph_path = GRAPHS_DIR / "single_verification.graph.json"
    runtime_path = GRAPHS_DIR / "single_verification.runtime.json"
    input_path = GRAPHS_DIR / "input.json"

    assert graph_path.exists()
    assert runtime_path.exists()
    assert input_path.exists()

    valid = validate_zeroshot_graph(graph_path, runtime_path, input_path)
    assert valid is True


def test_zeroshot_data_structures():
    metrics = ZeroshotMetrics(
        duration_seconds=12.5,
        iterations=2,
        verdict="accepted",
        syntax_error_detected=True,
        syntax_error_repaired=True,
    )
    res = ZeroshotRunResult(
        success=True,
        exit_code=0,
        metrics=metrics,
        stdout="ok",
        stderr="",
    )
    d = res.to_dict()
    assert d["success"] is True
    assert d["exit_code"] == 0
    assert d["metrics"]["verdict"] == "accepted"
    assert d["metrics"]["syntax_error_repaired"] is True
