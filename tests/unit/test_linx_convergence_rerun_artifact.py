import hashlib
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "artifacts/numerical/LINX-CONVERGENCE-RERUN-v4/run-20260722T0722Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_v4_manifest_is_bound_to_frozen_protocol() -> None:
    manifest = load_json("run_manifest.json")
    config = ROOT / "configs/benchmarks/linx_convergence_rerun_v4.yaml"

    assert manifest["status"] == "complete"
    assert manifest["scan_id"] == "LINX-CONVERGENCE-RERUN-v4"
    assert manifest["scan_config_sha256"] == sha256(config)

    registry = yaml.safe_load((RUN.parent / "RESULT_REGISTRY_v4.yaml").read_text())
    assert registry["runs"][0]["run"] == RUN.name
    assert registry["runs"][0]["status"] == ("complete_standard_point_numerical_candidate_accepted")
    assert registry["broader_w0_status"] == "incomplete"


def test_v4_passes_both_frozen_plateaus_without_failures() -> None:
    result = load_json("scan_results.json")
    decision = result["decision"]

    assert len(result["cases"]) == 6
    assert all(case["status"] == "ok" for case in result["cases"].values())
    assert all(case["max_steps"] == 16384 for case in result["cases"].values())
    assert decision["passed"] is True
    assert decision["candidate_scalar_batch_pass"] is True
    assert decision["repeat_drift_pass"] is True
    assert decision["within_batch_spread_pass"] is True
    assert decision["plateaus"]["tolerance"][
        "maximum_difference_observation_sigma"
    ] == pytest.approx(0.00036448324554868704)
    assert decision["plateaus"]["weak_rate_sampling"][
        "maximum_difference_observation_sigma"
    ] == pytest.approx(0.0007738593252529022)
    assert decision["candidate_case_differences_observation_sigma"][
        "production_candidate"
    ] == pytest.approx(0.00014939382078014678)


def test_v4_retains_complete_timing_and_cost_evidence() -> None:
    timings = [
        json.loads(line)
        for line in (RUN / "timings.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    resources = load_json("resource_report.json")

    assert len(timings) == 48
    assert len({record["case_id"] for record in timings}) == 6
    assert all(record["status"] == "ok" for record in timings)
    assert (RUN / "failures.jsonl").read_bytes() == b""
    assert resources["failed_cases"] == 0
    assert resources["estimated_cost_cny"] == pytest.approx(0.5347299850687385)
