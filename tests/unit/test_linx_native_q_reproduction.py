from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_module(relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load_module("scripts/run_linx_native_q_reproduction.py")
VALIDATOR = load_module("scripts/validate_linx_native_q_reproduction.py")


def protocol() -> dict:
    return yaml.safe_load(
        (ROOT / "configs/benchmarks/linx_native_q_reproduction_v1.yaml").read_text(encoding="utf-8")
    )


def synthetic_rows() -> tuple[list[dict], list[dict], dict[str, float]]:
    frozen = protocol()
    vectors = RUNNER.q_vectors(frozen)
    central = 2.45e-5
    shifts = {
        "dp_gamma_he3": 1.0e-7,
        "dd_n_he3": -8.0e-8,
        "dd_p_t": -6.0e-8,
    }

    def outputs(q_id: str) -> dict[str, float]:
        doh = central
        if q_id != "q0":
            reaction, sign = q_id.rsplit("_", 1)
            doh += shifts[reaction] * (-1.0 if sign == "m1" else 1.0)
        return {
            "Neff": 3.044,
            "YPBBN": 0.247 + (doh - central) * 100.0,
            "DoH": doh,
            "He3oH": 1.0e-5,
            "Li7oH": 5.0e-10,
        }

    scalar = []
    for case in frozen["numerical_cases"]:
        for q_id, vector in vectors.items():
            for repetition in range(2):
                scalar.append(
                    {
                        "case_id": case["id"],
                        "mode": "scalar",
                        "outputs": outputs(q_id),
                        "proton_denominator": 0.75,
                        "q_id": q_id,
                        "q_vector": vector,
                        "repetition": repetition,
                        "status": "ok",
                    }
                )
    batch = []
    for repetition in range(2):
        for q_id, vector in vectors.items():
            for duplicate in range(2):
                batch.append(
                    {
                        "case_id": "A_candidate",
                        "duplicate": duplicate,
                        "mode": "heterogeneous_batch",
                        "outputs": outputs(q_id),
                        "proton_denominator": 0.75,
                        "q_id": q_id,
                        "q_vector": vector,
                        "repetition": repetition,
                        "row_index": len(batch),
                        "status": "ok",
                    }
                )
    return scalar, batch, {"YPBBN": 0.0013, "DoH": 3.0e-7}


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def synthetic_artifact(root: Path) -> Path:
    frozen = protocol()
    scalar, batch, sigmas = synthetic_rows()
    decision = VALIDATOR.recompute_decision(
        frozen,
        {
            "scalar_rows": scalar,
            "batch_rows": batch,
            "structured_failure_count": 0,
            "observation_sigmas": sigmas,
        },
    )
    results = {
        "batch_rows": batch,
        "decision": decision,
        "observation_sigmas": sigmas,
        "scalar_rows": scalar,
        "schema_version": 1,
        "structured_failure_count": 0,
    }
    write_json(root / "results.json", results)
    write_json(
        root / "resource_report.json",
        {
            "cpu_core_hours": 0.1,
            "cpu_seconds": 360.0,
            "estimated_cost_cny": 0.01,
            "gpu_hours": 0.0,
            "hourly_price_cny": 3.0,
            "max_rss_bytes": 1024,
            "schema_version": 1,
            "wall_seconds": 12.0,
            "worker_hours": 12.0 / 3600.0,
        },
    )
    (root / "failures.jsonl").write_text("", encoding="utf-8")
    timings = [
        {
            "case_id": row["case_id"],
            "elapsed_seconds": 1.0,
            "kind": "scalar",
            "q_id": row["q_id"],
            "repetition": row["repetition"],
            "status": "ok",
        }
        for row in scalar
    ]
    timings.append(
        {
            "batch_size": 14,
            "elapsed_seconds": 1.0,
            "kind": "cold_heterogeneous_batch_compile_and_solve",
            "status": "ok",
        }
    )
    timings.extend(
        {
            "batch_size": 14,
            "elapsed_seconds": 1.0,
            "kind": "warm_heterogeneous_batch",
            "repetition": repetition,
            "status": "ok",
        }
        for repetition in range(2)
    )
    (root / "timings.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in timings),
        encoding="utf-8",
    )
    write_json(
        root / "run_manifest.json",
        {
            "artifact_id": VALIDATOR.ARTIFACT_ID,
            "background_reused_across_q_draws": True,
            "config_sha256": VALIDATOR.EXPECTED_CONFIG_SHA256,
            "environment": {
                "backend": "cpu",
                "jax": "0.4.28",
                "jaxlib": "0.4.28",
                "x64": True,
            },
            "environment_lock_sha256": VALIDATOR.EXPECTED_LOCK_SHA256,
            "mapping_artifact_sha256": VALIDATOR.EXPECTED_MAPPING_SHA256,
            "observation_config_sha256": VALIDATOR.EXPECTED_OBSERVATION_SHA256,
            "parameter_schema_sha256": VALIDATOR.EXPECTED_PARAMETER_SHA256,
            "parameters": frozen["parameter_set"]["values"],
            "schema_version": 1,
            "source_revision": VALIDATOR.EXPECTED_REVISION,
            "source_tracked_tree_clean": True,
            "status": "complete",
            "task_id": "UQ0-NATIVE-UQ-REPRO",
        },
    )
    companions = {
        name: VALIDATOR.sha256(root / name)
        for name in (
            "failures.jsonl",
            "resource_report.json",
            "results.json",
            "run_manifest.json",
            "timings.jsonl",
        )
    }
    artifact = {
        "artifact_id": VALIDATOR.ARTIFACT_ID,
        "claim_boundary": frozen["claim_boundary"],
        "companion_sha256": companions,
        "decision": decision,
        "generated_at_utc": "2026-07-23T00:00:00Z",
        "reproduction_id": VALIDATOR.ARTIFACT_ID,
        "schema_version": 1,
        "scientific_scope": (
            "LINX native scalar-envelope abundance calibration at one frozen "
            "standard-BBN point; not a selected project prior or posterior"
        ),
        "status": "accepted_C0_calibration",
        "task_id": "UQ0-NATIVE-UQ-REPRO",
    }
    artifact["evidence_sha256"] = VALIDATOR.digest_json(artifact)
    artifact_path = root / "reproduction.json"
    write_json(artifact_path, artifact)
    return artifact_path


def test_protocol_freezes_expected_grid_and_claim_boundary() -> None:
    frozen = protocol()
    assert frozen["source"]["revision"] == RUNNER.EXPECTED_REVISION
    assert frozen["source"]["network"] == "key_recommended"
    assert frozen["q_contract"]["indices_zero_based"] == {
        "dp_gamma_he3": 1,
        "dd_n_he3": 2,
        "dd_p_t": 3,
    }
    assert frozen["acceptance"]["expected_scalar_rows"] == 42
    assert frozen["acceptance"]["expected_batch_rows"] == 28
    assert frozen["claim_boundary"]["claim_level"] == "C0"
    assert frozen["claim_boundary"]["production_adapter_unlocked"] is False
    assert frozen["claim_boundary"]["novelty_claim_allowed"] is False


def test_runner_and_independent_validator_accept_complete_synthetic_grid() -> None:
    frozen = protocol()
    scalar, batch, sigmas = synthetic_rows()
    runner_decision = RUNNER.evaluate_results(frozen, scalar, batch, 0, sigmas)
    results = {
        "scalar_rows": scalar,
        "batch_rows": batch,
        "structured_failure_count": 0,
        "observation_sigmas": sigmas,
    }
    validator_decision = VALIDATOR.recompute_decision(frozen, results)

    assert runner_decision == validator_decision
    assert validator_decision["passed"] is True
    assert validator_decision["checks"]["D_over_H_plus_minus_responses"] is True
    assert set(validator_decision["response_checks"]) == {
        "dp_gamma_he3",
        "dd_n_he3",
        "dd_p_t",
    }


@pytest.mark.parametrize(
    ("mutation", "failed_check"),
    [
        ("missing_scalar", "scalar_grid_complete"),
        ("missing_batch", "batch_grid_complete"),
        ("structured_failure", "zero_structured_failures"),
        ("nonfinite", "finite_outputs"),
        ("nonpositive_proton", "positive_proton_denominator"),
        ("scalar_repeat", "zero_scalar_repeat_drift"),
        ("batch_repeat", "zero_batch_repeat_drift"),
        ("scalar_batch", "scalar_batch_budget"),
        ("plateau", "all_plateaus"),
        ("response", "D_over_H_plus_minus_responses"),
    ],
)
def test_validator_rejects_each_acceptance_failure(mutation: str, failed_check: str) -> None:
    frozen = protocol()
    scalar, batch, sigmas = synthetic_rows()
    failures = 0
    if mutation == "missing_scalar":
        scalar.pop()
    elif mutation == "missing_batch":
        batch.pop()
    elif mutation == "structured_failure":
        failures = 1
    elif mutation == "nonfinite":
        scalar[0]["outputs"]["DoH"] = math.nan
    elif mutation == "nonpositive_proton":
        scalar[0]["proton_denominator"] = 0.0
    elif mutation == "scalar_repeat":
        scalar[1]["outputs"]["YPBBN"] += 1.0e-12
    elif mutation == "batch_repeat":
        batch[-1]["outputs"]["YPBBN"] += 1.0e-12
    elif mutation == "scalar_batch":
        batch[0]["outputs"]["YPBBN"] += 0.0013
    elif mutation == "plateau":
        target = next(
            row
            for row in scalar
            if row["case_id"] == "B_tolerance" and row["q_id"] == "q0" and row["repetition"] == 0
        )
        target["outputs"]["YPBBN"] += 0.0013
        matching_repeat = next(
            row
            for row in scalar
            if row["case_id"] == "B_tolerance" and row["q_id"] == "q0" and row["repetition"] == 1
        )
        matching_repeat["outputs"]["YPBBN"] += 0.0013
    elif mutation == "response":
        for row in scalar:
            if row["case_id"] == "A_candidate" and row["q_id"] in {
                "dp_gamma_he3_m1",
                "dp_gamma_he3_p1",
            }:
                row["outputs"]["DoH"] = 2.46e-5
    result = VALIDATOR.recompute_decision(
        frozen,
        {
            "scalar_rows": scalar,
            "batch_rows": batch,
            "structured_failure_count": failures,
            "observation_sigmas": sigmas,
        },
    )
    assert result["passed"] is False
    assert result["checks"][failed_check] is False


def test_validator_rejects_duplicate_and_q_vector_drift() -> None:
    frozen = protocol()
    scalar, batch, sigmas = synthetic_rows()
    duplicate = copy.deepcopy(scalar[0])
    scalar.append(duplicate)
    with pytest.raises(ValueError, match="duplicate scalar row"):
        VALIDATOR.recompute_decision(
            frozen,
            {
                "scalar_rows": scalar,
                "batch_rows": batch,
                "structured_failure_count": 0,
                "observation_sigmas": sigmas,
            },
        )

    scalar, batch, sigmas = synthetic_rows()
    scalar[0]["q_vector"][0] = 1.0
    with pytest.raises(ValueError, match="q-vector"):
        VALIDATOR.recompute_decision(
            frozen,
            {
                "scalar_rows": scalar,
                "batch_rows": batch,
                "structured_failure_count": 0,
                "observation_sigmas": sigmas,
            },
        )


def test_full_validator_recomputes_and_hash_binds_all_companions(
    tmp_path: Path,
) -> None:
    artifact_path = synthetic_artifact(tmp_path)
    result = VALIDATOR.validate(
        artifact_path,
        ROOT / "configs/benchmarks/linx_native_q_reproduction_v1.yaml",
    )
    assert result["accepted"] is True
    assert result["scalar_rows"] == 42
    assert result["batch_rows"] == 28

    results_path = tmp_path / "results.json"
    results_path.write_text(results_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="companion evidence drift"):
        VALIDATOR.validate(
            artifact_path,
            ROOT / "configs/benchmarks/linx_native_q_reproduction_v1.yaml",
        )


def test_full_validator_authenticates_a_completed_rejected_run(tmp_path: Path) -> None:
    artifact_path = synthetic_artifact(tmp_path)
    results_path = tmp_path / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    for row in results["scalar_rows"]:
        if row["case_id"] == "B_tolerance" and row["q_id"] == "q0":
            row["outputs"]["YPBBN"] += 0.001
    results["decision"] = VALIDATOR.recompute_decision(protocol(), results)
    assert results["decision"]["passed"] is False
    write_json(results_path, results)

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["decision"] = results["decision"]
    artifact["status"] = "complete_not_accepted"
    artifact["companion_sha256"]["results.json"] = VALIDATOR.sha256(results_path)
    artifact.pop("evidence_sha256")
    artifact["evidence_sha256"] = VALIDATOR.digest_json(artifact)
    write_json(artifact_path, artifact)

    validated = VALIDATOR.validate(
        artifact_path,
        ROOT / "configs/benchmarks/linx_native_q_reproduction_v1.yaml",
    )
    assert validated["accepted"] is False
    assert validated["native_UQ_task_progress_eligible"] is False


def test_full_validator_rejects_scope_overclaim_with_valid_digest(
    tmp_path: Path,
) -> None:
    artifact_path = synthetic_artifact(tmp_path)
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["scientific_scope"] = "production prior accepted"
    artifact.pop("evidence_sha256")
    artifact["evidence_sha256"] = VALIDATOR.digest_json(artifact)
    write_json(artifact_path, artifact)
    with pytest.raises(ValueError, match="scientific-scope drift"):
        VALIDATOR.validate(
            artifact_path,
            ROOT / "configs/benchmarks/linx_native_q_reproduction_v1.yaml",
        )


def test_runner_cli_help_works_outside_repository(tmp_path: Path) -> None:
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_linx_native_q_reproduction.py"),
            "--help",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
