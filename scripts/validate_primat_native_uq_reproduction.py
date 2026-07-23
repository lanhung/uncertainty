#!/usr/bin/env python3
"""Fail-closed validator for PRIMAT-NATIVE-UQ-REPRODUCTION-v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_ARTIFACT_ID = "PRIMAT-NATIVE-UQ-REPRODUCTION-v1"
EXPECTED_PROTOCOL_SHA256 = "4cc776daa3c6f31b816c35319e935002f11d9d3dfd7c91ed7b2d91ba7c593303"
EXPECTED_REVISION = "21ff8f39fa18e3937e9fdf386cfa982361bfdfce"
EXPECTED_QUANTITIES = ("YPBBN", "DoH", "He3oH", "Li7oH")
DERIVED_TABLE_CROSS_PLATFORM_RTOL = 1.0e-12
EXPECTED_FILE_KEYS = {
    "samples_npy",
    "samples_tsv",
    "covariance_tsv",
    "correlation_tsv",
    "failures_jsonl",
    "timings_jsonl",
    "resource_report_json",
    "checkpoint_json",
    "checkpoint_samples_npy",
}
EXPECTED_FILE_PATHS = {
    "samples_npy": "samples.npy",
    "samples_tsv": "samples.tsv",
    "covariance_tsv": "covariance.tsv",
    "correlation_tsv": "correlation.tsv",
    "failures_jsonl": "failures.jsonl",
    "timings_jsonl": "timings.jsonl",
    "resource_report_json": "resource_report.json",
    "checkpoint_json": "checkpoint.json",
    "checkpoint_samples_npy": "checkpoint_samples_1000.npy",
}
EXPECTED_SOURCE_HASHES = {
    "primat/backend.py": "307b25c9f407323105c773de7cc216f5e0fb295c06fe07319aba272f65e347e5",
    "primat/main.py": "5d0a3d5fb68759bfb3346ac07a8d28da3078bc0595db2a4b4d2e71f10f1c5779",
    "primat/config.py": "ec3f905975f98d90f976456e2d2827b93e933ba92b9fef16d5f6445421fd2ce2",
    "primat/network_data.py": "96a771b2e6c23b9d17500740f8ffc9bfecb41d89c23904de4f1a356ca677e1ec",
    "primat-c/src/mc.c": "1ab18ef79a39bba73638760835e5cd011cc674bff255396ee39fdd28aad86116",
    "primat-c/src/network_data.c": "48d02ac8cb95fd3776f98a8dccf29061da0f7d52705208c29408606e2747ae54",
    "primat-c/include/mc.h": "7f0a97cc6edb696595a99e430f980727d8d5a7cfb229ce87deaa334e9161bdfd",
    "primat/_primat_c_src/_wrapper.c": "eda39de43a442736bc3d4e564f067fc74e31d455ec2be0223e44e5aca0c0fdcb",
    "primat/data/nuclear/networks/small.txt": "358a6c141f281e75fda3bba0e2993f9f4b3f1c036b2621a2755e4281488a2981",
    "pyproject.toml": "0937b27c4585949cddb7d95823eef75ec88ff46bf584e951fe49fde4a0083eec",
}
EXPECTED_REPOSITORY_INPUTS = {
    "environment_lock": "45f60efbea16955ae3ca2740d6d55e9ae969fe9a5e33d5ef9d71d92d12f3c723",
    "forward_card": "33e1de0cfc768e017b2a9f76fb22867177d7bb2646941be5d04498a17ac1bc7b",
    "parameter_schema": "61dc9c3ec1fdc9eb455f9ed64ad604a49d801e2b7de361db8db74a883b8c3c9e",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def exact_float(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=2.0e-15, abs_tol=0.0)


def parse_samples_tsv(path: Path) -> np.ndarray:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or tuple(lines[0].split("\t")) != EXPECTED_QUANTITIES:
        raise ValueError("samples.tsv header drift")
    rows = [[float(value) for value in line.split("\t")] for line in lines[1:]]
    return np.asarray(rows, dtype=np.float64)


def parse_matrix_tsv(path: Path, kind: str) -> np.ndarray:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 2 + len(EXPECTED_QUANTITIES):
        raise ValueError(f"{kind} TSV row count drift")
    if not lines[0].startswith(f"# {kind}; N=1000; seed=2026072301;"):
        raise ValueError(f"{kind} TSV provenance header drift")
    if tuple(lines[1].split("\t")[1:]) != EXPECTED_QUANTITIES:
        raise ValueError(f"{kind} TSV column header drift")
    values: list[list[float]] = []
    for expected, line in zip(EXPECTED_QUANTITIES, lines[2:]):
        fields = line.split("\t")
        if fields[0] != expected or len(fields) != 1 + len(EXPECTED_QUANTITIES):
            raise ValueError(f"{kind} TSV row header drift")
        values.append([float(value) for value in fields[1:]])
    return np.asarray(values, dtype=np.float64)


def compare_array(actual: np.ndarray, expected: np.ndarray, label: str) -> None:
    if (
        actual.shape != expected.shape
        or not np.isfinite(actual).all()
        or not np.allclose(
            actual,
            expected,
            rtol=DERIVED_TABLE_CROSS_PLATFORM_RTOL,
            atol=0.0,
        )
    ):
        raise ValueError(f"{label} does not reproduce raw samples")


def validate(path: Path) -> dict[str, Any]:
    artifact = load_json(path)
    stored_digest = artifact.pop("evidence_sha256", None)
    if not isinstance(stored_digest, str) or digest_json(artifact) != stored_digest:
        raise ValueError("artifact evidence digest mismatch")
    artifact["evidence_sha256"] = stored_digest
    if (
        artifact.get("schema_version") != 1
        or artifact.get("artifact_id") != EXPECTED_ARTIFACT_ID
        or artifact.get("task_id") != "UQ0-NATIVE-UQ-REPRO"
        or artifact.get("status") != "completed_upstream_native_compiled_C_calibration"
    ):
        raise ValueError("artifact identity or status drift")
    if artifact["protocol"] != {
        "path": "configs/benchmarks/primat_native_uq_reproduction_v1.yaml",
        "sha256": EXPECTED_PROTOCOL_SHA256,
    }:
        raise ValueError("protocol provenance drift")

    scope = artifact["scientific_scope"]
    if scope != {
        "claim_level": "C0",
        "upstream_native_calibration_only": True,
        "project_nuclear_prior_selected": False,
        "R0_prior_validated": False,
        "UQ1_direct_MC_truth": False,
        "production_authorized": False,
        "solver_independent_validation": False,
        "novelty_claim": False,
    }:
        raise ValueError("scientific boundary drift or overclaim")
    source = artifact["source"]
    if (
        source["repository"] != "https://github.com/CyrilPitrou/primat"
        or source["release"] != "v0.3.2"
        or source["revision"] != EXPECTED_REVISION
        or source["worktree_clean"] is not True
        or source["source_file_hashes"] != EXPECTED_SOURCE_HASHES
        or not source["compiled_extension"]
        or len(source["compiled_extension_sha256"]) != 64
    ):
        raise ValueError("source/backend provenance drift")
    if artifact["repository_inputs"] != EXPECTED_REPOSITORY_INPUTS:
        raise ValueError("repository input provenance drift")
    environment = artifact["environment"]
    if (
        environment["python"] != "3.11.15"
        or environment["numpy"] != "2.3.5"
        or environment["scipy"] != "1.16.3"
        or environment["precision"] != "float64"
    ):
        raise ValueError("environment drift")

    execution = artifact["execution"]
    if (
        execution["api"] != "primat.run_mc"
        or execution["backend"] != "c"
        or execution["force_backend"] != "c"
        or execution["prohibited_backend_used"] is not False
        or execution["draws"] != 1000
        or execution["seed"] != 2026072301
        or execution["n_jobs"] != 20
        or execution["prefix_draws"] != [100, 300, 1000]
        or tuple(execution["quantities"]) != EXPECTED_QUANTITIES
        or execution["native_thermonuclear_latent_count"] != 12
        or execution["resumed_from_draws"] not in (0, 100, 300, 1000)
    ):
        raise ValueError("execution contract drift")
    expected_parameters = {
        "Omegabh2": 0.02237,
        "DeltaNeff": 0.0,
        "tau_n": 878.3,
        "std_tau_n": 0.5,
        "tau_n_normalization": True,
        "network": "small",
        "numerical_precision": 1.0e-7,
        "rescale_nuclear_rates": False,
        "QED_corrections": True,
        "nuclear_qed_corrections": True,
        "mc_rate_rescale_cap": 30.0,
        "verbose": False,
        "debug": False,
        "show_progress": False,
    }
    if execution["parameters"] != expected_parameters:
        raise ValueError("solver/native-prior parameter mapping drift")

    files = artifact["files"]
    if set(files) != EXPECTED_FILE_KEYS:
        raise ValueError("artifact file registry drift")
    if {label: record.get("path") for label, record in files.items()} != EXPECTED_FILE_PATHS:
        raise ValueError("artifact file path drift")
    root = path.parent
    for label, record in files.items():
        candidate = root / record["path"]
        if not candidate.is_file() or sha256(candidate) != record["sha256"]:
            raise ValueError(f"file evidence mismatch: {label}")
    failures = root / files["failures_jsonl"]["path"]
    if failures.read_bytes() != b"":
        raise ValueError("structured failure ledger is not empty")
    failure_accounting = artifact["failure_accounting"]
    if failure_accounting != {
        "structured_failure_count": 0,
        "failures_file_empty": True,
    }:
        raise ValueError("failure accounting drift")

    samples_path = root / files["samples_npy"]["path"]
    samples = np.load(samples_path, allow_pickle=False)
    if (
        samples.dtype != np.float64
        or samples.shape != (1000, 4)
        or not np.isfinite(samples).all()
        or not np.all(samples > 0)
    ):
        raise ValueError("raw selected samples are invalid")
    tsv_samples = parse_samples_tsv(root / files["samples_tsv"]["path"])
    compare_array(tsv_samples, samples, "samples TSV")

    covariance = np.atleast_2d(np.cov(samples, rowvar=False, ddof=1))
    correlation = np.atleast_2d(np.corrcoef(samples, rowvar=False))
    covariance_tsv = parse_matrix_tsv(root / files["covariance_tsv"]["path"], "covariance")
    correlation_tsv = parse_matrix_tsv(root / files["correlation_tsv"]["path"], "correlation")
    compare_array(covariance_tsv, covariance, "covariance TSV")
    compare_array(correlation_tsv, correlation, "correlation TSV")
    if (
        not np.array_equal(covariance, covariance.T)
        or not np.allclose(correlation, correlation.T, rtol=0.0, atol=1.0e-15)
        or not np.allclose(np.diag(correlation), 1.0, rtol=0.0, atol=1.0e-15)
    ):
        raise ValueError("covariance/correlation structural acceptance failed")

    stored_std = artifact["sample_standard_deviations_ddof1"]
    for index, name in enumerate(EXPECTED_QUANTITIES):
        recomputed = float(np.std(samples[:, index], ddof=1))
        if (
            recomputed <= 0
            or not exact_float(float(stored_std[name]), recomputed)
            or not exact_float(covariance[index, index], recomputed**2)
        ):
            raise ValueError(f"standard deviation drift: {name}")

    quantile_probabilities = (0.025, 0.16, 0.5, 0.84, 0.975)
    prefix_statistics = artifact["prefix_statistics"]
    if set(prefix_statistics) != {"100", "300", "1000"}:
        raise ValueError("prefix-statistics key drift")
    for draws in (100, 300, 1000):
        record = prefix_statistics[str(draws)]
        if record["draws"] != draws or set(record["quantities"]) != set(EXPECTED_QUANTITIES):
            raise ValueError("prefix-statistics structure drift")
        for index, name in enumerate(EXPECTED_QUANTITIES):
            values = samples[:draws, index]
            stored = record["quantities"][name]
            if not exact_float(float(stored["mean"]), float(np.mean(values))):
                raise ValueError(f"prefix mean drift: {draws}/{name}")
            if not exact_float(
                float(stored["standard_deviation_ddof1"]),
                float(np.std(values, ddof=1)),
            ):
                raise ValueError(f"prefix std drift: {draws}/{name}")
            expected_quantiles = {
                format(probability, ".3f"): float(np.quantile(values, probability))
                for probability in quantile_probabilities
            }
            if set(stored["quantiles"]) != set(expected_quantiles):
                raise ValueError("prefix quantile key drift")
            for probability, expected in expected_quantiles.items():
                if not exact_float(float(stored["quantiles"][probability]), expected):
                    raise ValueError(f"prefix quantile drift: {draws}/{name}/{probability}")

    central = artifact["central_acceptance"]
    references = {
        "YPBBN": 0.24695513077748688,
        "DoH": 2.4447361728164994e-5,
    }
    if (
        central["accepted"] is not True
        or central["reference_outputs"] != references
        or central["relative_tolerance"] != 1.0e-10
        or central["absolute_tolerance"] != 1.0e-14
        or set(central["outputs"]) != set(EXPECTED_QUANTITIES)
        or set(central["absolute_differences"]) != set(references)
    ):
        raise ValueError("central forward baseline was not accepted")
    for name, expected in references.items():
        actual = float(central["outputs"][name])
        allowed = 1.0e-14 + 1.0e-10 * abs(expected)
        difference = abs(actual - expected)
        if difference > allowed or not exact_float(
            float(central["absolute_differences"][name]), difference
        ):
            raise ValueError(f"central baseline mismatch: {name}")

    replay = artifact["serial_replay"]
    replay_samples = np.asarray(replay["samples"], dtype=np.float64)
    if (
        replay["draws"] != 16
        or replay["seed"] != 2026072301
        or replay["n_jobs"] != 1
        or replay["backend"] != "c"
        or replay["exact_parallel_prefix_match"] is not True
        or replay["maximum_absolute_difference"] != 0.0
        or replay_samples.shape != (16, 4)
        or not np.array_equal(replay_samples, samples[:16])
        or replay["samples_sha256"] != digest_json(replay["samples"])
    ):
        raise ValueError("parallel/serial exact prefix replay failed")

    checkpoint = load_json(root / files["checkpoint_json"]["path"])
    checkpoint_samples = np.load(root / files["checkpoint_samples_npy"]["path"], allow_pickle=False)
    if (
        checkpoint["schema_version"] != 1
        or checkpoint["protocol_id"] != EXPECTED_ARTIFACT_ID
        or checkpoint["protocol_sha256"] != EXPECTED_PROTOCOL_SHA256
        or checkpoint["source_revision"] != EXPECTED_REVISION
        or checkpoint["backend"] != "c"
        or checkpoint["seed"] != 2026072301
        or checkpoint["completed_draws"] != 1000
        or checkpoint["parameters"] != expected_parameters
        or checkpoint["samples_file"] != files["checkpoint_samples_npy"]["path"]
        or checkpoint["samples_sha256"] != sha256(root / files["checkpoint_samples_npy"]["path"])
        or checkpoint_samples.dtype != np.float64
        or checkpoint_samples.shape[0] != 1000
        or checkpoint_samples.shape[1] != len(checkpoint["quantity_names"])
        or not set(EXPECTED_QUANTITIES).issubset(checkpoint["quantity_names"])
        or not np.isfinite(checkpoint_samples).all()
    ):
        raise ValueError("durable checkpoint acceptance failed")
    selected_indices = [checkpoint["quantity_names"].index(name) for name in EXPECTED_QUANTITIES]
    if not np.array_equal(checkpoint_samples[:, selected_indices], samples):
        raise ValueError("final artifact differs from durable checkpoint")

    timing_lines = (root / files["timings_jsonl"]["path"]).read_text(encoding="utf-8").splitlines()
    if not timing_lines:
        raise ValueError("timing ledger is empty")
    timings = [json.loads(line) for line in timing_lines]
    if not all(
        row.get("backend") == "c"
        and math.isfinite(float(row.get("elapsed_seconds", math.nan)))
        and float(row["elapsed_seconds"]) >= 0
        for row in timings
    ):
        raise ValueError("timing ledger contains invalid records")
    replay_records = [row for row in timings if row["stage"] == "serial_prefix_replay"]
    if not replay_records or any(
        row["target_draws"] != 16 or row["n_jobs"] != 1 for row in replay_records
    ):
        raise ValueError("serial replay timing accounting drift")
    parallel_targets = [
        int(row["target_draws"]) for row in timings if row["stage"] == "parallel_prefix"
    ]
    parallel_records = [row for row in timings if row["stage"] == "parallel_prefix"]
    if any(
        row["target_draws"] not in (100, 300, 1000)
        or row["n_jobs"] != 20
        or row["new_draws"] != {100: 100, 300: 200, 1000: 700}[row["target_draws"]]
        for row in parallel_records
    ):
        raise ValueError("parallel prefix timing contract drift")
    if not all(target in parallel_targets for target in (100, 300, 1000)):
        raise ValueError("checkpoint/resume timing sequence is incomplete")
    # A process can terminate after recording completion but before advancing
    # the atomic checkpoint pointer. Such a target may legitimately appear
    # more than once after recovery, but target order can never move backward.
    if parallel_targets != sorted(parallel_targets):
        raise ValueError("checkpoint/resume timing sequence drift")
    first_serial = next(
        (index for index, row in enumerate(timings) if row["stage"] == "serial_prefix_replay"),
        len(timings),
    )
    if any(row["stage"] == "parallel_prefix" for row in timings[first_serial + 1 :]):
        raise ValueError("parallel prefix recorded after serial replay")
    if any(row["stage"] not in {"parallel_prefix", "serial_prefix_replay"} for row in timings):
        raise ValueError("unregistered timing stage")

    resources = load_json(root / files["resource_report_json"]["path"])
    for key in (
        "wall_seconds",
        "current_attempt_wall_seconds",
        "measured_solver_wall_seconds_all_attempts",
        "process_cpu_seconds",
        "accounted_process_rusage_seconds",
        "hourly_price_cny",
        "estimated_cost_cny",
        "gpu_hours",
    ):
        if not math.isfinite(float(resources[key])) or float(resources[key]) < 0:
            raise ValueError(f"invalid resource accounting: {key}")
    if resources["gpu_hours"] != 0.0:
        raise ValueError("CPU reproduction cannot claim GPU hours")
    expected_cost = float(resources["hourly_price_cny"]) * float(resources["wall_seconds"]) / 3600.0
    if not exact_float(float(resources["estimated_cost_cny"]), expected_cost):
        raise ValueError("resource cost arithmetic drift")
    durable_solver_seconds = sum(float(row["elapsed_seconds"]) for row in timings)
    if not exact_float(
        float(resources["measured_solver_wall_seconds_all_attempts"]),
        durable_solver_seconds,
    ):
        raise ValueError("durable timing/resource accounting drift")
    if float(resources["wall_seconds"]) + 1.0e-15 < max(
        float(resources["current_attempt_wall_seconds"]), durable_solver_seconds
    ):
        raise ValueError("wall-time accounting understates durable evidence")
    if artifact["resource_summary"] != {
        "wall_seconds": resources["wall_seconds"],
        "estimated_cost_cny": resources["estimated_cost_cny"],
        "gpu_hours": 0.0,
    }:
        raise ValueError("artifact/resource report mismatch")

    acceptance = artifact["acceptance"]
    if acceptance != {
        "compiled_C_backend": True,
        "parallel_serial_prefix_exact": True,
        "all_selected_samples_finite": True,
        "all_selected_abundances_positive": True,
        "all_selected_standard_deviations_positive": True,
        "covariance_finite_and_symmetric": True,
        "correlation_finite_symmetric_unit_diagonal": True,
        "prefix_statistics_diagnostic_only": True,
        "accepted": True,
    }:
        raise ValueError("acceptance flags drift")
    return {
        "accepted": True,
        "draws": 1000,
        "quantities": list(EXPECTED_QUANTITIES),
        "backend": "c",
        "serial_replay_draws": 16,
        "structured_failure_count": 0,
        "evidence_sha256": stored_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.artifact), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
