import json
from pathlib import Path

import pytest

from scripts.why_not_benchmark import finite_abundances, quantile, summarize


def test_timing_summary_uses_registered_distribution_statistics() -> None:
    values = [float(value) for value in range(1, 31)]
    summary = summarize(values)

    assert summary["median"] == 15.5
    assert summary["q1"] == 8.25
    assert summary["q3"] == 22.75
    assert summary["p95"] == pytest.approx(28.55)
    assert quantile(values, 0.0) == 1.0
    assert quantile(values, 1.0) == 30.0


def test_nonfinite_solver_output_is_a_structured_failure_boundary() -> None:
    result = {
        "Neff": 3.044,
        "YPBBN": 0.247,
        "YPCMB": 0.246,
        "DoH": float("nan"),
        "He3oH": 1.0e-5,
        "Li7oH": 5.0e-10,
    }

    with pytest.raises(FloatingPointError, match="DoH"):
        finite_abundances(result)


def test_direct_benchmark_entrypoint_declares_required_artifacts() -> None:
    source = (Path(__file__).resolve().parents[2] / "scripts/why_not_benchmark.py").read_text(
        encoding="utf-8"
    )

    for name in (
        "run_manifest.json",
        "timings.jsonl",
        "failures.jsonl",
        "posterior_metrics.json",
        "resource_report.json",
    ):
        assert json.dumps(name)[1:-1] in source
    assert "registered_standard_fiducial_runtime_slice_only" in source
    assert "sequential_calls_no_native_batch_api" in source
