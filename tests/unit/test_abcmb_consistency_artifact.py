import hashlib
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "artifacts/numerical/ABCMB-LINX-BATCH-CONSISTENCY-v1" / "run-20260722T113106Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_manifest_is_bound_to_frozen_inputs_and_exact_source() -> None:
    manifest = load_json("run_manifest.json")
    bindings = {
        "scan_config_sha256": ROOT / "configs/benchmarks/abcmb_linx_batch_consistency_v1.yaml",
        "benchmark_config_sha256": ROOT / "configs/benchmarks/why_not_existing_solvers_v1.yaml",
        "observation_config_sha256": ROOT / "configs/data/abundance_OBS-v1.yaml",
        "parameter_schema_sha256": ROOT / "configs/physics/parameter_schema.yaml",
        "environment_lock_sha256": ROOT / "environments/abcmb-v0.3.1/uv.lock",
    }

    assert manifest["status"] == "complete"
    assert manifest["baseline"] == "W3-ABCMB"
    assert manifest["source_revision"] == "5eabbab4ed7e53f264e16024743d1ba517845c37"
    assert manifest["scientific_use"] == ("standard_fiducial_scalar_native_batch_consistency_only")
    for field, path in bindings.items():
        assert manifest[field] == sha256(path)

    registry = yaml.safe_load((RUN.parent / "RESULT_REGISTRY_v1.yaml").read_text())
    assert registry["bundled_linx_tree"] == "59b3ab7b3ada7d7ff6484920e0e29291cf4a084e"
    assert registry["runs"][0]["run"] == RUN.name
    assert registry["runs"][0]["status"] == "complete_not_accepted"
    assert registry["why_not_conclusion"] == "undetermined"


def test_all_cases_completed_but_frozen_plateaus_failed() -> None:
    result = load_json("scan_results.json")
    decision = result["decision"]

    assert len(result["cases"]) == 8
    assert all(case["status"] == "ok" for case in result["cases"].values())
    assert decision["all_required_cases_complete"] is True
    assert decision["candidate_scalar_batch_pass"] is True
    assert decision["repeat_drift_pass"] is True
    assert decision["within_batch_spread_pass"] is True
    assert decision["plateaus"]["tolerance"]["passed"] is False
    assert decision["plateaus"]["weak_rate_sampling"]["passed"] is False
    assert decision["passed"] is False
    assert decision["numerical_consistency_status"] == "not_accepted"
    assert decision["plateaus"]["tolerance"][
        "maximum_difference_observation_sigma"
    ] == pytest.approx(0.004769097101800476)
    assert decision["plateaus"]["weak_rate_sampling"][
        "maximum_difference_observation_sigma"
    ] == pytest.approx(0.02745560673424933)


def test_raw_timing_failure_and_resource_evidence_is_complete() -> None:
    records = [
        json.loads(line)
        for line in (RUN / "timings.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    resources = load_json("resource_report.json")

    assert len(records) == 64
    assert len({record["case_id"] for record in records}) == 8
    assert all(record["status"] == "ok" for record in records)
    assert (RUN / "failures.jsonl").read_bytes() == b""
    assert resources["failed_cases"] == 0
    assert resources["gpu_hours"] == 0.0
    assert resources["estimated_cost_cny"] == pytest.approx(0.23556674655377863)
