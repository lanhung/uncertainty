from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LINX = ROOT / "artifacts/numerical/LINX-GRADIENT-STABILITY-v1/run-20260722T195438Z"
ABCMB = ROOT / "artifacts/numerical/ABCMB-FULL-COMPONENT-AUDIT-v1/run-20260722T201836Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_linx_negative_gradient_result_is_complete_and_hash_bound() -> None:
    manifest = load(LINX / "run_manifest.json")
    result = load(LINX / "scan_results.json")
    decision = result["decision"]

    assert manifest["status"] == "complete_with_failures"
    assert manifest["source_revision"] == "ec2e9d2ca455e8204137e884da29f5dd13a638fa"
    assert manifest["scan_config_sha256"] == sha256(
        ROOT / "configs/benchmarks/linx_gradient_stability_v1.yaml"
    )
    assert manifest["parameter_schema_sha256"] == sha256(
        ROOT / "configs/physics/parameter_schema_standard_bbn_v1.yaml"
    )
    assert decision["expected_acceptance_record_count"] == 45
    assert decision["acceptance_record_count"] == 45
    assert decision["structured_failure_count"] == 45
    assert decision["silent_nonfinite_count"] == 0
    assert decision["numerical_gradient_status"] == "not_accepted"
    assert decision["passed"] is False
    assert len((LINX / "failures.jsonl").read_text(encoding="utf-8").splitlines()) == 45


def test_linx_heartbeat_replay_is_complete_and_immutable() -> None:
    replay = load(LINX / "heartbeat_replay_report.json")
    outbox = LINX / "heartbeat-outbox-replayed.ndjson"

    assert replay["terminal_event"] == "fail"
    assert replay["event_count"] == 48
    assert replay["duplicate_acknowledgements"] == 0
    assert replay["outbox_drained"] is True
    assert sha256(outbox) == replay["archive_sha256"]


def test_abcmb_spectra_stage_accepts_all_five_cases_only() -> None:
    manifest = load(ABCMB / "run_manifest.json")
    result = load(ABCMB / "results.json")

    assert manifest["status"] == "complete_accepted"
    assert manifest["source_revision"] == "5eabbab4ed7e53f264e16024743d1ba517845c37"
    assert manifest["bundled_linx_tree"] == "59b3ab7b3ada7d7ff6484920e0e29291cf4a084e"
    assert manifest["config_sha256"] == sha256(
        ROOT / "configs/benchmarks/abcmb_full_component_audit_v1.yaml"
    )
    assert result["status"] == "complete_accepted"
    assert len(result["spectra"]) == 5
    assert all(case["status"] == "accepted" for case in result["spectra"])
    assert all(
        case["evaluation"]["maximum_relative_repeat_drift"] == 0 for case in result["spectra"]
    )
    for case in result["spectra"]:
        assert sha256(ABCMB / case["spectra_archive"]) == case["spectra_archive_sha256"]
    assert result["components"]["spectra"]["status"] == "evaluated"
    for component in ("gradient", "toy_fisher", "synthetic_recovery", "hmc_nuts"):
        assert result["components"][component]["status"] == "not_run"
    assert not (ABCMB / "failures.jsonl").read_text(encoding="utf-8")


def test_abcmb_heartbeat_replay_preserves_partial_terminal_block() -> None:
    replay = load(ABCMB / "heartbeat_replay_report.json")
    outbox = ABCMB / "heartbeat-outbox-replayed.ndjson"
    final = json.loads(outbox.read_text(encoding="utf-8").splitlines()[-1])

    assert replay["terminal_event"] == "block"
    assert replay["event_count"] == 40
    assert replay["duplicate_acknowledgements"] == 0
    assert replay["outbox_drained"] is True
    assert sha256(outbox) == replay["archive_sha256"]
    assert final["event"] == "block"
    assert final["current"] == 1.0
    assert final["total"] == 4.0
