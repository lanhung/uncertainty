import hashlib
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "artifacts/numerical/ABCMB-LINX-EXTENDED-CONVERGENCE-v2" / "run-20260722T134322Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_manifest_is_bound_to_frozen_v2_and_exact_source() -> None:
    manifest = load_json("run_manifest.json")
    bindings = {
        "scan_config_sha256": ROOT / "configs/benchmarks/abcmb_linx_extended_convergence_v2.yaml",
        "benchmark_config_sha256": ROOT / "configs/benchmarks/why_not_existing_solvers_v1.yaml",
        "observation_config_sha256": ROOT / "configs/data/abundance_OBS-v1.yaml",
        "parameter_schema_sha256": ROOT / "configs/physics/parameter_schema_standard_bbn_v1.yaml",
        "environment_lock_sha256": ROOT / "environments/abcmb-v0.3.1/uv.lock",
    }

    assert manifest["status"] == "complete"
    assert manifest["baseline"] == "W3-ABCMB"
    assert manifest["source_revision"] == "5eabbab4ed7e53f264e16024743d1ba517845c37"
    for field, path in bindings.items():
        assert manifest[field] == sha256(path)

    registry = yaml.safe_load((RUN.parent / "RESULT_REGISTRY_v2.yaml").read_text())
    assert registry["runs"][0]["run"] == RUN.name
    assert registry["runs"][0]["status"] == "complete_accepted_narrow_scope"
    assert registry["scientific_task_progress_credit"] == 0
    assert registry["why_not_conclusion"] == "undetermined"


def test_frozen_v2_decision_passed_at_narrow_scope() -> None:
    result = load_json("scan_results.json")
    decision = result["decision"]

    assert len(result["cases"]) == 6
    assert all(case["status"] == "ok" for case in result["cases"].values())
    assert decision["all_required_cases_complete"] is True
    assert decision["candidate_scalar_batch_pass"] is True
    assert decision["repeat_drift_pass"] is True
    assert decision["within_batch_spread_pass"] is True
    assert decision["plateaus"]["tolerance"]["passed"] is True
    assert decision["plateaus"]["weak_rate_sampling"]["passed"] is True
    assert decision["passed"] is True
    assert decision["numerical_consistency_status"] == "accepted"
    assert decision["plateaus"]["tolerance"][
        "maximum_difference_observation_sigma"
    ] == pytest.approx(0.000387133068337529)
    assert decision["plateaus"]["weak_rate_sampling"][
        "maximum_difference_observation_sigma"
    ] == pytest.approx(0.0007711233686420631)


def test_raw_timing_failure_and_resource_evidence_is_complete() -> None:
    records = [
        json.loads(line)
        for line in (RUN / "timings.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    resources = load_json("resource_report.json")

    assert len(records) == 48
    assert len({record["case_id"] for record in records}) == 6
    assert all(record["status"] == "ok" for record in records)
    assert (RUN / "failures.jsonl").read_bytes() == b""
    assert resources["failed_cases"] == 0
    assert resources["gpu_hours"] == 0.0
    assert resources["estimated_cost_cny"] == pytest.approx(0.25799504698067904)
