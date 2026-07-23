#!/usr/bin/env python3
"""Build non-decisional UQ direct-solver reference arithmetic."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.validate_why_not_runtime import validate_run
except ModuleNotFoundError:  # Direct ``python scripts/<name>.py`` execution.
    from validate_why_not_runtime import validate_run


CALL_COUNTS = (1_000, 10_000, 64_000)
BASELINES = {
    "W0-LINX": {
        "revision": "ec2e9d2ca455e8204137e884da29f5dd13a638fa",
        "run": "run-20260722T0605Z",
        "workload_mode": "native_64_point_batch_at_repeated_standard_input",
        "registry_sha256": "7621f3d9f89a83dc77d72b0fc7857a9d08f0049d56cf7d5131e995a36c990eec",
        "runtime_sha256": "d39404267ed3a0f5c62660c864143922eb697a4765658a2318888a93924d22a2",
        "resource_sha256": "fc3337081312b740c1b76ffefe891f45fe41da0ab297cc05238a3d0f6aeab1bf",
        "manifest_sha256": "1d9f3f5c1641483623fe1cc94c42472f08b4d3471e27568500caecb4ff67b918",
        "timings_sha256": "9da10b59a4c984b255377c736a43a577681226f7caa300c214539ca8a7882a47",
    },
    "W1-PRYM": {
        "revision": "725d8a8db3ad5ea2630580d825c9d0d69ed76533",
        "run": "run-20260722T0753Z",
        "workload_mode": "sequential_64_point_workload",
        "registry_sha256": "a3977fe21f4872ace8a3ee8f8b671a20ad82db24db7e6ba270157b8ac2c822ca",
        "runtime_sha256": "973323651caf9ee8c305a0247dc712f48da08ce594845de780ab5c3bb91cee52",
        "resource_sha256": "fb28ac3fe6d31d77c1bba911f1ffc35e28819100c08c33e1f2b08d3850d59243",
        "manifest_sha256": "6948f5d3eaf275efd4b789759a109c663588eff362b0cef64314bf9495640ade",
        "timings_sha256": "32b866b012c958624b8290d06d76d369e8688b20d78a51e5d34b5993aeeb34f7",
    },
    "W2-PRIMAT": {
        "revision": "21ff8f39fa18e3937e9fdf386cfa982361bfdfce",
        "run": "run-20260722T0535Z",
        "workload_mode": "sequential_64_point_workload",
        "registry_sha256": "9c71c9e10e563ee9db693ce03e7e99467419dadcbca1892dfbd82ab9af7ea5e3",
        "runtime_sha256": "dfbfff9536cc16aa592786a38a41c4e5eb664faa9e4333f829e1b38080c7419f",
        "resource_sha256": "405c44f4e6d863866f3c71c5f79a08a35377bd3144032963db3ca068c054a837",
        "manifest_sha256": "5ea0ca84f87ce98443363398fd2fd940d9d244c2dda7f517df2bfae2d322bd59",
        "timings_sha256": "d1281952768d29f05d736146ca3fb39be93b0dcc035d3da242f723c2f6b54d11",
    },
    "W3-ABCMB": {
        "revision": "5eabbab4ed7e53f264e16024743d1ba517845c37",
        "run": "run-20260722T1118Z",
        "workload_mode": "native_64_point_bundled_LINX_batch_at_repeated_standard_input",
        "registry_sha256": "18f8bb5a69bc18a6d9f29458833d4ae261e0bdde029df9d283d23f9f158fc31e",
        "runtime_sha256": "863adc6fa7eb64ca69b88e2fb193cb476878aca4ff801c3dda3ab68e0b70c839",
        "resource_sha256": "e8ce57b9de0892a3595f78cf581260c1132fa9eb7860e726c531eee2a1e05468",
        "manifest_sha256": "1d1b516982e9ad88e10b4fcca10a033867529e3ba4721ddb38b1a3558a63bc9b",
        "timings_sha256": "6e94f51a2fa5214659e4a3915bb0919e02fe79c50eb5431cd5316659c66e54ab",
    },
}
ADR_PATH = "docs/decisions/ADR-WHY-NOT-001.md"
ADR_SHA256 = "cc48cc755c35972d1035f8fedfc0c2866b640b00f9f4aa91f9ed23debd1ce728"
POSTERIOR_NOT_RUN_SHA256 = "d08969569397d0cc8f2c1208a1ee0b457c699e11f754cc58268b4c7b179fd97e"
EMPTY_FAILURE_LEDGER_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected YAML mapping: {path}")
    return payload


def reference_arithmetic(
    call_count: int,
    seconds_per_point: float,
    hourly_price: float,
) -> dict[str, Any]:
    worker_hours = call_count * seconds_per_point / 3600.0
    return {
        "call_equivalents": call_count,
        "reference_worker_hours_if_identical_call_cost": worker_hours,
        "reference_cost_cny_if_identical_call_cost": worker_hours * hourly_price,
    }


def build(repository_root: Path) -> dict[str, Any]:
    adr = repository_root / ADR_PATH
    if sha256(adr) != ADR_SHA256:
        raise ValueError("WHY-NOT ADR SHA256 drift")

    records = []
    for baseline_id, frozen in BASELINES.items():
        baseline_root = (
            repository_root / "artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1" / baseline_id
        )
        run_root = baseline_root / frozen["run"]
        paths = {
            "registry": baseline_root / "RESULT_REGISTRY_v1.yaml",
            "runtime_summary": run_root / "runtime_summary.json",
            "resource_report": run_root / "resource_report.json",
            "run_manifest": run_root / "run_manifest.json",
            "posterior_metrics": run_root / "posterior_metrics.json",
            "timings": run_root / "timings.jsonl",
            "failures": run_root / "failures.jsonl",
        }
        expected_hash_key = {
            "registry": "registry_sha256",
            "runtime_summary": "runtime_sha256",
            "resource_report": "resource_sha256",
            "run_manifest": "manifest_sha256",
            "posterior_metrics": "posterior_sha256",
            "timings": "timings_sha256",
            "failures": "failures_sha256",
        }
        for key, path in paths.items():
            if key == "posterior_metrics":
                expected = POSTERIOR_NOT_RUN_SHA256
            elif key == "failures":
                expected = EMPTY_FAILURE_LEDGER_SHA256
            else:
                expected = frozen[expected_hash_key[key]]
            if sha256(path) != expected:
                raise ValueError(f"{baseline_id}: {key} SHA256 drift")

        registry = load_yaml(paths["registry"])
        resource = load_json(paths["resource_report"])
        manifest = load_json(paths["run_manifest"])
        integrity = validate_run(repository_root, run_root)
        if registry["source_revision"] != frozen["revision"]:
            raise ValueError(f"{baseline_id}: source revision drift")
        if registry["full_baseline_status"] != "incomplete":
            raise ValueError(f"{baseline_id}: full baseline status unexpectedly changed")
        if registry["why_not_conclusion"] != "undetermined":
            raise ValueError(f"{baseline_id}: WHY-NOT conclusion unexpectedly changed")
        if resource["failure_count"] != 0:
            raise ValueError(f"{baseline_id}: frozen runtime slice contains failures")

        scalar_seconds = float(integrity["timings"]["scalar_median_seconds"])
        workload_seconds = float(integrity["timings"]["batch_64_median_seconds"])
        workload_seconds_per_point = workload_seconds / 64.0
        price = float(resource["hourly_price_cny"])
        records.append(
            {
                "baseline_id": baseline_id,
                "source_revision": frozen["revision"],
                "run_id": manifest["run_id"],
                "run_directory": frozen["run"],
                "source_artifacts": {
                    key: {
                        "path": str(path.relative_to(repository_root)),
                        "sha256": sha256(path),
                    }
                    for key, path in paths.items()
                },
                "registered_scope": registry["slices"][0]["scientific_use"],
                "registered_limitations": registry["slices"][0]["limitations"],
                "full_baseline_status": registry["full_baseline_status"],
                "why_not_conclusion": registry["why_not_conclusion"],
                "raw_runtime_integrity": {
                    "validation_status": integrity["validation_status"],
                    "checks": integrity["checks"],
                    "successful_warm_points": integrity["successful_warm_points"],
                    "timed_warm_points_expected": integrity["timed_warm_points_expected"],
                    "failure_records": integrity["failure_records"],
                },
                "measured_standard_fiducial": {
                    "warm_scalar_median_seconds_per_point": scalar_seconds,
                    "warm_scalar_p95_seconds_per_point": float(
                        integrity["timings"]["scalar_p95_seconds"]
                    ),
                    "warm_64_workload_median_seconds": workload_seconds,
                    "warm_64_workload_median_seconds_per_point": (workload_seconds_per_point),
                    "workload_mode": frozen["workload_mode"],
                    "structured_failures": int(resource["failure_count"]),
                    "hourly_price_cny": price,
                },
                "scalar_path_reference_arithmetic": [
                    reference_arithmetic(call_count, scalar_seconds, price)
                    for call_count in CALL_COUNTS
                ],
                "measured_64_workload_reference_arithmetic": [
                    reference_arithmetic(call_count, workload_seconds_per_point, price)
                    for call_count in CALL_COUNTS
                ],
                "reference_arithmetic_boundary": {
                    "not_a_UQ_cost_projection": True,
                    "q_varying_abundance_calls_measured": False,
                    "rate_marginalization_measured": False,
                    "posterior_recovery_measured": False,
                    "SBC_measured": False,
                    "two_worker_scaling_measured": False,
                    "production_candidate_runtime_measured": False,
                    "warm_standard_point_linear_extrapolation_only": True,
                },
            }
        )

    return {
        "schema_version": 1,
        "artifact_id": "WHY-NOT-UQ-INTERIM-ECONOMICS-v1",
        "task_id": "P0-WHY-NOT-01",
        "status": "interim_reference_arithmetic_full_UQ_economics_undetermined",
        "protocol": {"path": ADR_PATH, "sha256": ADR_SHA256},
        "call_equivalent_scenarios": {
            "1000": (
                "illustrative standard-point reference arithmetic only; "
                "not a UQ1 direct-MC projection"
            ),
            "10000": (
                "illustrative standard-point reference arithmetic only; "
                "not an authorized convergence run"
            ),
            "64000": (
                "illustrative 64x1000 arithmetic scale only; "
                "not the registered Fisher or SBC workload"
            ),
        },
        "baselines": records,
        "decision": {
            "direct_solver_sufficient": "undetermined",
            "emulator_speed_necessity": "undetermined",
            "direct_first_stop_rule_evaluable": False,
            "reason": (
                "Only standard-fiducial forward runtime is measured. The arithmetic is not a "
                "UQ cost projection; actual R0 rate draws, native marginalization, posterior "
                "calls, SBC, fidelity, accepted-config retiming and scaling are pending."
            ),
        },
        "claim_boundary": {
            "P0_WHY_NOT_01_done_allowed": False,
            "progress_credit_memos": 0,
            "UQ0_R0_prior_gate_bypassed": False,
            "production_run_authorized": False,
            "scientific_signoff_provided": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact = build(args.repository_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact["decision"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
