import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.why_not_benchmark import summarize


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1/W0-LINX/run-20260722T0605Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_linx_runtime_manifest_is_bound_to_registered_inputs() -> None:
    manifest = load_json("run_manifest.json")
    protocol_path = ROOT / "configs/benchmarks/why_not_existing_solvers_v1.yaml"
    schema_path = ROOT / "configs/physics/parameter_schema.yaml"
    lock_path = ROOT / "environments/linx-v0.1.2/uv.lock"
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "complete"
    assert manifest["scientific_use"] == "registered_standard_fiducial_runtime_slice_only"
    assert manifest["source_revision"] == protocol["baselines"]["W0-LINX"]["revision"]
    assert manifest["config_sha256"] == sha256(protocol_path)
    assert manifest["parameter_schema_sha256"] == sha256(schema_path)
    assert manifest["environment_lock_sha256"] == sha256(lock_path)
    assert manifest["repetitions"] == 30
    assert manifest["batch_sizes"] == [1, 64]

    registry = yaml.safe_load((RUN.parent / "RESULT_REGISTRY_v1.yaml").read_text(encoding="utf-8"))
    assert registry["slices"][0]["run"] == RUN.name
    assert registry["slices"][0]["status"] == "complete_with_batch_discrepancy_open"
    assert registry["full_baseline_status"] == "incomplete"


def test_linx_preserves_all_native_batch_timings_and_open_discrepancy() -> None:
    records = [
        json.loads(line)
        for line in (RUN / "timings.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    warm = [record for record in records if record["kind"] == "warm_batch"]
    scalar = [record for record in warm if record["batch_size"] == 1]
    batch = [record for record in warm if record["batch_size"] == 64]
    cold_batch = [record for record in records if record["kind"] == "cold_batch_compile_and_solve"]

    assert len(records) == 63
    assert len(scalar) == 30
    assert len(batch) == 30
    assert len(cold_batch) == 1
    assert sum(record["successful_points"] for record in warm) == 1950
    assert all(record["status"] == "ok" for record in warm)
    assert all(record["execution_mode"] == "jax_jit_vmap_native_batch" for record in batch)
    assert (RUN / "failures.jsonl").read_bytes() == b""

    summary = load_json("runtime_summary.json")
    assert summary["jax_x64"] is True
    assert summary["numerical_consistency_status"] == "batch_discrepancy_open"
    assert summary["maximum_absolute_repeat_drift"] == pytest.approx(
        summary["maximum_absolute_repeat_drift_by_abundance"]["YPBBN"]
    )
    assert summary["maximum_absolute_repeat_drift"] > 0
    assert summary["batch_reference_abundances"] != summary["abundances"]
    assert summarize([record["elapsed_seconds"] for record in scalar])["median"] == pytest.approx(
        summary["timings_seconds"]["warm_batch_1"]["median"]
    )
    assert summarize([record["elapsed_seconds"] for record in batch])["median"] == pytest.approx(
        summary["timings_seconds"]["warm_batch_64"]["median"]
    )


def test_linx_runtime_slice_does_not_accept_gradient_or_posterior_evidence() -> None:
    report = (ROOT / "docs/inventory/WHY_NOT_LINX_RUNTIME_v1.md").read_text(encoding="utf-8")
    posterior = load_json("posterior_metrics.json")
    resources = load_json("resource_report.json")

    assert posterior["status"] == "not_run"
    assert "not yet an accepted\ngradient/HMC baseline" in report
    assert "batch_discrepancy_open" in report
    assert resources["failure_count"] == 0
    assert resources["gpu_hours"] == 0.0
