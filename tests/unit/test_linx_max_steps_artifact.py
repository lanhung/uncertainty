import hashlib
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "artifacts/numerical/LINX-MAX-STEPS-DIAGNOSTIC-v3/run-20260722T0708Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_v3_manifest_is_bound_to_frozen_protocol() -> None:
    manifest = load_json("run_manifest.json")
    config = ROOT / "configs/benchmarks/linx_max_steps_diagnostic_v3.yaml"

    assert manifest["status"] == "complete_with_failures"
    assert manifest["scan_id"] == "LINX-MAX-STEPS-DIAGNOSTIC-v3"
    assert manifest["scan_config_sha256"] == sha256(config)

    registry = yaml.safe_load((RUN.parent / "RESULT_REGISTRY_v3.yaml").read_text())
    assert registry["runs"][0]["run"] == RUN.name
    assert registry["runs"][0]["decision"]["recommended_follow_up_max_steps"] == 16384


def test_v3_accepts_only_registered_max_steps_invariance() -> None:
    result = load_json("scan_results.json")
    decision = result["decision"]

    assert result["cases"]["max_steps_4096_control"]["status"] == "failed"
    for value in (8192, 16384, 32768):
        case = result["cases"][f"max_steps_{value}"]
        assert case["status"] == "ok"
        assert case["max_steps"] == value
        assert case["maximum_scalar_batch_difference_observation_sigma"] == pytest.approx(
            0.00014939382078014678
        )
    assert decision["passed"] is True
    assert decision["plateaus"]["max_steps_invariance"]["passed"] is True
    assert (
        decision["plateaus"]["max_steps_invariance"]["maximum_difference_observation_sigma"] == 0.0
    )
    assert decision["repeat_drift_pass"] is True
    assert decision["within_batch_spread_pass"] is True


def test_v3_retains_expected_failure_and_resource_cost() -> None:
    failures = [
        json.loads(line)
        for line in (RUN / "failures.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    timings = (RUN / "timings.jsonl").read_text(encoding="utf-8").splitlines()
    resources = load_json("resource_report.json")

    assert len(failures) == 1
    assert failures[0]["case_id"] == "max_steps_4096_control"
    assert "maximum number of solver steps was reached" in failures[0]["traceback"]
    assert len(timings) == 24
    assert resources["failed_cases"] == 1
    assert resources["estimated_cost_cny"] == pytest.approx(0.3076726356297731)
