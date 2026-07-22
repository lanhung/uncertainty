import hashlib
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "artifacts/numerical/LINX-EXTENDED-CONVERGENCE-v2/run-20260722T0653Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_v2_manifest_is_bound_to_frozen_protocol() -> None:
    manifest = load_json("run_manifest.json")
    config = ROOT / "configs/benchmarks/linx_extended_convergence_scan_v2.yaml"

    assert manifest["status"] == "complete_with_failures"
    assert manifest["scan_id"] == "LINX-EXTENDED-CONVERGENCE-v2"
    assert manifest["scan_config_sha256"] == sha256(config)
    assert manifest["scientific_use"] == ("standard_fiducial_scalar_native_batch_consistency_only")

    registry = yaml.safe_load((RUN.parent / "RESULT_REGISTRY_v2.yaml").read_text())
    assert registry["runs"][0]["run"] == RUN.name
    assert registry["runs"][0]["status"] == "complete_with_failures_not_accepted"


def test_v2_preserves_maximum_step_failures() -> None:
    result = load_json("scan_results.json")
    completed = [case for case in result["cases"].values() if case["status"] == "ok"]
    failed = [case for case in result["cases"].values() if case["status"] == "failed"]
    failure_records = [
        json.loads(line)
        for line in (RUN / "failures.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert len(completed) == 1
    assert len(failed) == 5
    assert len(failure_records) == 5
    assert all("maximum number of solver steps was reached" in case["error"] for case in failed)
    assert all(record["kind"] == "solver_exception" for record in failure_records)
    assert all(
        "maximum number of solver steps was reached" in record["traceback"]
        for record in failure_records
    )
    assert completed[0]["maximum_scalar_batch_difference_observation_sigma"] == pytest.approx(
        0.0013744523573138289
    )


def test_v2_gate_is_not_accepted_or_imputed() -> None:
    result = load_json("scan_results.json")
    decision = result["decision"]
    resources = load_json("resource_report.json")
    timings = (RUN / "timings.jsonl").read_text(encoding="utf-8").splitlines()

    assert decision["all_required_cases_complete"] is False
    assert decision["passed"] is False
    assert decision["numerical_consistency_status"] == "not_accepted"
    assert decision["plateaus"]["tolerance"]["maximum_difference_observation_sigma"] is None
    assert (
        decision["plateaus"]["weak_rate_sampling"]["maximum_difference_observation_sigma"] is None
    )
    assert resources["failed_cases"] == 5
    assert resources["estimated_cost_cny"] == pytest.approx(0.20829909255504608)
    assert len(timings) == 8
