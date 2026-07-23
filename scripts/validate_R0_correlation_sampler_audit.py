#!/usr/bin/env python3
"""Validate the frozen R0 correlation stress-sampler audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_ARTIFACT_SHA256 = "6453319b60a257331a5edc44ad4e8bc48f6d18c3c8f9a55137257bf24f147d9c"
EXPECTED_CONTRACT_SHA256 = "13e923a28436d67e50dba86bbbe0fb62e25eca201d80b22bce4e0026aa7cd78a"
EXPECTED_COMPARATOR_SHA256 = "0634a74a1e1937b8d6b959282f10e21f505514e7449ccbd05b5e639083f2b5dd"
BASE_SEED = 2026072301


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def model_seed(model_id: str) -> int:
    digest = hashlib.sha256(f"{BASE_SEED}:{model_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def matrix_multiply_left_transpose(lower: list[list[float]]) -> list[list[float]]:
    return [
        [sum(lower[row][k] * lower[column][k] for k in range(3)) for column in range(3)]
        for row in range(3)
    ]


def validate(path: Path, repository_root: Path) -> dict[str, Any]:
    if sha256(path) != EXPECTED_ARTIFACT_SHA256:
        raise ValueError("correlation sampler artifact SHA256 drift")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact["schema_version"] != 1:
        raise ValueError("unsupported correlation sampler schema")
    if artifact["artifact_id"] != "R0-CORRELATION-SAMPLER-AUDIT-v1":
        raise ValueError("unexpected correlation sampler artifact")
    if artifact["status"] != (
        "preregistered_correlation_stress_sampler_numerically_validated_"
        "scientific_covariance_not_inferred"
    ):
        raise ValueError("correlation sampler status drift")

    source = artifact["source"]
    contract_path = repository_root / source["candidate_contract"]
    comparator_path = repository_root / source["coherent_comparators"]
    if (
        source["candidate_contract_sha256"] != EXPECTED_CONTRACT_SHA256
        or sha256(contract_path) != EXPECTED_CONTRACT_SHA256
    ):
        raise ValueError("candidate contract SHA256 drift")
    if (
        source["coherent_comparators_sha256"] != EXPECTED_COMPARATOR_SHA256
        or sha256(comparator_path) != EXPECTED_COMPARATOR_SHA256
    ):
        raise ValueError("coherent comparator SHA256 drift")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    registered = contract["correlation_stress_suite"]
    registered_by_id = {record["model_id"]: record for record in registered["matrices"]}

    sampler = artifact["sampler"]
    if sampler != {
        "algorithm": ("numpy_Generator_PCG64DXSM_standard_normal_then_registered_Cholesky"),
        "base_seed": BASE_SEED,
        "model_seed_derivation": ("big_endian_uint64(first_8_bytes(SHA256(base_seed:model_id)))"),
        "samples_per_model": 200_000,
        "replay_samples": 4_096,
        "float_dtype": "float64",
        "reaction_order": ["dp_gamma_he3", "dd_n_he3", "dd_p_t"],
    }:
        raise ValueError("correlation sampler contract drift")
    if artifact["environment"]["python"] != "3.11.15":
        raise ValueError("correlation sampler Python drift")
    if artifact["environment"]["numpy"] != "2.3.5":
        raise ValueError("correlation sampler NumPy drift")
    if artifact["environment"]["byteorder"] != "little":
        raise ValueError("correlation sampler byte order drift")
    thresholds = artifact["acceptance_thresholds"]
    if thresholds != {
        "Cholesky_max_abs": 1.0e-14,
        "empirical_correlation_max_abs": 0.012,
        "empirical_mean_max_abs": 0.012,
        "empirical_std_minus_one_max_abs": 0.012,
        "coherent_q_reconstruction_max_abs": 1.0e-12,
    }:
        raise ValueError("correlation sampler acceptance threshold drift")

    models = artifact["models"]
    if len(models) != 35 or {model["model_id"] for model in models} != set(registered_by_id):
        raise ValueError("correlation sampler model coverage drift")
    max_correlation = 0.0
    max_mean = 0.0
    max_std = 0.0
    max_q = 0.0
    replay_passed = 0
    for model in models:
        registered_model = registered_by_id[model["model_id"]]
        if model["matrix_sha256"] != registered_model["matrix_sha256"]:
            raise ValueError("correlation matrix SHA256 drift")
        if model["ordered_matrix"] != registered_model["ordered_matrix"]:
            raise ValueError("correlation matrix values drift")
        if model["registered_Cholesky_lower"] != registered_model["Cholesky_lower"]:
            raise ValueError("registered Cholesky values drift")
        reconstructed = matrix_multiply_left_transpose(model["computed_Cholesky_lower"])
        if any(
            not math.isclose(
                reconstructed[i][j],
                model["ordered_matrix"][i][j],
                rel_tol=0.0,
                abs_tol=1.0e-14,
            )
            for i in range(3)
            for j in range(3)
        ):
            raise ValueError("computed Cholesky does not reconstruct the matrix")
        if model["nearest_PSD_projection_used"]:
            raise ValueError("nearest-PSD projection is prohibited")
        cholesky_delta = max(
            abs(
                float(model["computed_Cholesky_lower"][i][j])
                - float(model["registered_Cholesky_lower"][i][j])
            )
            for i in range(3)
            for j in range(3)
        )
        if not math.isclose(
            float(model["max_abs_registered_vs_computed_Cholesky"]),
            cholesky_delta,
            rel_tol=0.0,
            abs_tol=1.0e-16,
        ):
            raise ValueError("stored Cholesky residual drift")
        if model["seed"] != model_seed(model["model_id"]):
            raise ValueError("model seed derivation drift")
        if model["samples"] != 200_000:
            raise ValueError("model sample count drift")
        replay = model["replay"]
        if replay["samples"] != 4_096 or not replay["exact_array_equal"]:
            raise ValueError("fixed-seed replay failed")
        if len(replay["epsilon_little_endian_float64_sha256"]) != 64:
            raise ValueError("fixed-seed replay hash malformed")
        replay_passed += 1

        empirical_correlation_error = max(
            abs(float(model["empirical_correlation"][i][j]) - float(model["ordered_matrix"][i][j]))
            for i in range(3)
            for j in range(3)
        )
        empirical_mean_error = max(abs(float(value)) for value in model["empirical_mean"])
        empirical_std_error = max(abs(float(value) - 1.0) for value in model["empirical_std_ddof1"])
        for field, recomputed_value in (
            ("max_abs_empirical_correlation_error", empirical_correlation_error),
            ("max_abs_empirical_mean", empirical_mean_error),
            ("max_abs_empirical_std_minus_one", empirical_std_error),
        ):
            if not math.isclose(
                float(model[field]),
                recomputed_value,
                rel_tol=0.0,
                abs_tol=1.0e-16,
            ):
                raise ValueError(f"stored correlation sampler metric drift: {field}")

        coherence = model["coherent_temperature_curve_probe"]
        if coherence["draws"] != 16 or coherence["evaluations"] != 2_880:
            raise ValueError("coherent-temperature probe coverage drift")
        if not (
            coherence["one_scalar_q_held_across_temperature_per_reaction"]
            and coherence["all_rates_positive"]
            and coherence["actual_posterior_reconstruction"] is False
        ):
            raise ValueError("coherent-temperature probe claim drift")

        max_correlation = max(
            max_correlation,
            float(model["max_abs_empirical_correlation_error"]),
        )
        max_mean = max(max_mean, float(model["max_abs_empirical_mean"]))
        max_std = max(
            max_std,
            float(model["max_abs_empirical_std_minus_one"]),
        )
        max_q = max(
            max_q,
            float(coherence["max_abs_reconstructed_q_error"]),
        )
        expected_acceptance = {
            "factorization_passed": (
                model["max_abs_registered_vs_computed_Cholesky"] <= thresholds["Cholesky_max_abs"]
            ),
            "empirical_correlation_passed": (
                model["max_abs_empirical_correlation_error"]
                <= thresholds["empirical_correlation_max_abs"]
            ),
            "empirical_mean_passed": (
                model["max_abs_empirical_mean"] <= thresholds["empirical_mean_max_abs"]
            ),
            "empirical_std_passed": (
                model["max_abs_empirical_std_minus_one"]
                <= thresholds["empirical_std_minus_one_max_abs"]
            ),
            "fixed_seed_replay_passed": replay["exact_array_equal"],
            "coherent_temperature_curve_probe_passed": (
                coherence["all_rates_positive"]
                and coherence["max_abs_reconstructed_q_error"]
                <= thresholds["coherent_q_reconstruction_max_abs"]
            ),
        }
        if model["acceptance"] != expected_acceptance or not all(expected_acceptance.values()):
            raise ValueError("per-model correlation sampler acceptance drift")

    summary = artifact["summary"]
    expected_summary = {
        "model_records": len(models),
        "unique_matrix_sha256": len({model["matrix_sha256"] for model in models}),
        "all_model_checks_passed": True,
        "max_abs_empirical_correlation_error": max_correlation,
        "max_abs_empirical_mean": max_mean,
        "max_abs_empirical_std_minus_one": max_std,
        "max_abs_coherent_q_reconstruction_error": max_q,
        "fixed_seed_replay_passed_models": replay_passed,
        "nearest_PSD_projection_used_models": 0,
    }
    if summary != expected_summary:
        raise ValueError("correlation sampler summary drift")
    if summary["unique_matrix_sha256"] != 34:
        raise ValueError("correlation sampler unique matrix count drift")
    claim = artifact["claim_boundary"]
    if claim != {
        "A03_A00_A09_signoffs": "pending",
        "actual_ETR25_cross_reaction_covariance_inferred": False,
        "actual_posterior_reconstruction": False,
        "identity_is_scientific_default": False,
        "production_use": "prohibited",
        "scientific_prior_reactions_accepted": 0,
        "task_done_allowed": False,
    }:
        raise ValueError("correlation sampler claim boundary drift")
    self_hash = artifact["payload_sha256_without_self_hash"]
    if self_hash != payload_sha256({**artifact, "payload_sha256_without_self_hash": None}):
        raise ValueError("correlation sampler payload digest drift")
    return expected_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.artifact, args.repository_root.resolve()),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
