import json
from pathlib import Path

import pytest

from scripts.why_not_benchmark import (
    finite_abundances,
    linx_abundances,
    load_yaml,
    quantile,
    summarize,
)


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


def test_linx_species_are_converted_to_common_abundances() -> None:
    raw = [1.0e-10, 0.75, 2.0e-5, 1.0e-8, 8.0e-6, 0.062, 1.0e-11, 4.0e-10]
    result = linx_abundances(raw, 3.044)

    assert result["Neff"] == 3.044
    assert result["YPBBN"] == 0.248
    assert result["DoH"] == pytest.approx(2.0e-5 / 0.75)
    assert result["He3oH"] == pytest.approx((1.0e-8 + 8.0e-6) / 0.75)
    assert result["Li7oH"] == pytest.approx((1.0e-11 + 4.0e-10) / 0.75)


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
    assert "direct_url.json" in source
    assert "primat._primat_c" in source
    assert "jax_jit_vmap_native_batch" in source
    assert "matrix = np.asarray(jax.device_get(raw))" in source
    assert "matrix = np.moveaxis(matrix, 0, -1)" in source
    assert "matrix = matrix.reshape((-1, 8))" in source
    assert "unexpected LINX batch size" in source
    assert "batch_reference_abundances" in source
    assert "maximum_absolute_repeat_drift_by_abundance" in source
    assert "batch_discrepancy_open" in source


def test_yaml_loader_records_in_process_parser(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("answer: 42\n", encoding="utf-8")

    result, loader = load_yaml(config, None)

    assert result == {"answer": 42}
    assert loader == "in_process_pyyaml"
