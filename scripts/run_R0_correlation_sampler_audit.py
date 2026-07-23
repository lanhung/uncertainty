#!/usr/bin/env python3
"""Audit the preregistered R0 correlation stress sampler numerically."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_CONTRACT_SHA256 = "13e923a28436d67e50dba86bbbe0fb62e25eca201d80b22bce4e0026aa7cd78a"
EXPECTED_COMPARATOR_SHA256 = "0634a74a1e1937b8d6b959282f10e21f505514e7449ccbd05b5e639083f2b5dd"
CANONICAL_CONTRACT_PATH = "artifacts/priors/R0-PRIOR-CANDIDATE-CONTRACT-v1/package.json"
CANONICAL_COMPARATOR_PATH = "artifacts/priors/ETR25-R0-COHERENT-COMPARATORS-v1/package.json"
BASE_SEED = 2026072301
SAMPLES_PER_MODEL = 200_000
REPLAY_SAMPLES = 4_096
EMPIRICAL_CORRELATION_ABS_TOLERANCE = 0.012
EMPIRICAL_MEAN_ABS_TOLERANCE = 0.012
EMPIRICAL_STD_ABS_TOLERANCE = 0.012


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_seed(model_id: str) -> int:
    digest = hashlib.sha256(f"{BASE_SEED}:{model_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def payload_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def sample_hash(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values.astype("<f8", copy=False))
    return hashlib.sha256(contiguous.tobytes()).hexdigest()


def coherent_surrogate_probe(
    comparator: dict[str, Any],
    reaction_order: list[str],
    q_values: np.ndarray,
) -> dict[str, Any]:
    max_q_reconstruction_error = 0.0
    minimum_rate = math.inf
    evaluations = 0
    for reaction_index, reaction in enumerate(reaction_order):
        rows = comparator["reactions"][reaction]["rows"]
        for q in q_values[:, reaction_index]:
            q_float = float(q)
            for row in rows:
                median = float(row["source_actual_percentiles"]["p50"])
                surrogate = row["quantile_matched_asymmetric_rank1_surrogate"]
                slope = float(
                    surrogate["lower_log_slope_per_q" if q_float < 0.0 else "upper_log_slope_per_q"]
                )
                log_rate = math.log(median) + slope * q_float
                rate = math.exp(log_rate)
                reconstructed_q = (log_rate - math.log(median)) / slope
                minimum_rate = min(minimum_rate, rate)
                max_q_reconstruction_error = max(
                    max_q_reconstruction_error,
                    abs(reconstructed_q - q_float),
                )
                evaluations += 1
    return {
        "draws": int(q_values.shape[0]),
        "temperature_rows_per_reaction": 60,
        "evaluations": evaluations,
        "one_scalar_q_held_across_temperature_per_reaction": True,
        "minimum_rate": minimum_rate,
        "all_rates_positive": minimum_rate > 0.0,
        "max_abs_reconstructed_q_error": max_q_reconstruction_error,
        "actual_posterior_reconstruction": False,
        "role": "mathematical_curve_coherence_stress_only",
    }


def audit_model(
    record: dict[str, Any],
    comparator: dict[str, Any],
    reaction_order: list[str],
) -> dict[str, Any]:
    model_id = record["model_id"]
    target = np.asarray(record["ordered_matrix"], dtype=np.float64)
    registered_lower = np.asarray(record["Cholesky_lower"], dtype=np.float64)
    computed_lower = np.linalg.cholesky(target)
    factorization_error = float(np.max(np.abs(computed_lower - registered_lower)))

    seed = model_seed(model_id)
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    epsilon = generator.standard_normal((SAMPLES_PER_MODEL, 3), dtype=np.float64)
    draws = epsilon @ registered_lower.T
    empirical_correlation = np.corrcoef(draws, rowvar=False)
    empirical_mean = np.mean(draws, axis=0)
    empirical_std = np.std(draws, axis=0, ddof=1)
    max_correlation_error = float(np.max(np.abs(empirical_correlation - target)))
    max_mean = float(np.max(np.abs(empirical_mean)))
    max_std_error = float(np.max(np.abs(empirical_std - 1.0)))

    replay_a = np.random.Generator(np.random.PCG64DXSM(seed)).standard_normal(
        (REPLAY_SAMPLES, 3),
        dtype=np.float64,
    )
    replay_b = np.random.Generator(np.random.PCG64DXSM(seed)).standard_normal(
        (REPLAY_SAMPLES, 3),
        dtype=np.float64,
    )
    replay_exact = bool(np.array_equal(replay_a, replay_b))
    replay_hash = sample_hash(replay_a)
    coherence = coherent_surrogate_probe(
        comparator,
        reaction_order,
        draws[:16],
    )

    return {
        "model_id": model_id,
        "family": record["family"],
        "matrix_sha256": record["matrix_sha256"],
        "ordered_matrix": target.tolist(),
        "registered_Cholesky_lower": registered_lower.tolist(),
        "computed_Cholesky_lower": computed_lower.tolist(),
        "max_abs_registered_vs_computed_Cholesky": factorization_error,
        "nearest_PSD_projection_used": False,
        "seed": seed,
        "samples": SAMPLES_PER_MODEL,
        "empirical_mean": empirical_mean.tolist(),
        "empirical_std_ddof1": empirical_std.tolist(),
        "empirical_correlation": empirical_correlation.tolist(),
        "max_abs_empirical_correlation_error": max_correlation_error,
        "max_abs_empirical_mean": max_mean,
        "max_abs_empirical_std_minus_one": max_std_error,
        "replay": {
            "samples": REPLAY_SAMPLES,
            "exact_array_equal": replay_exact,
            "epsilon_little_endian_float64_sha256": replay_hash,
        },
        "coherent_temperature_curve_probe": coherence,
        "acceptance": {
            "factorization_passed": factorization_error <= 1.0e-14,
            "empirical_correlation_passed": (
                max_correlation_error <= EMPIRICAL_CORRELATION_ABS_TOLERANCE
            ),
            "empirical_mean_passed": max_mean <= EMPIRICAL_MEAN_ABS_TOLERANCE,
            "empirical_std_passed": (max_std_error <= EMPIRICAL_STD_ABS_TOLERANCE),
            "fixed_seed_replay_passed": replay_exact,
            "coherent_temperature_curve_probe_passed": (
                coherence["all_rates_positive"]
                and coherence["max_abs_reconstructed_q_error"] <= 1.0e-12
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--comparators", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if sha256(args.contract) != EXPECTED_CONTRACT_SHA256:
        raise SystemExit("R0 prior candidate contract SHA256 drift")
    if sha256(args.comparators) != EXPECTED_COMPARATOR_SHA256:
        raise SystemExit("R0 coherent comparator SHA256 drift")
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    comparator = json.loads(args.comparators.read_text(encoding="utf-8"))
    stress = contract["correlation_stress_suite"]
    reaction_order = contract["reaction_order"]
    if stress["model_count"] != 35 or stress["unique_matrix_count"] != 34:
        raise SystemExit("registered stress-suite cardinality drift")
    if stress["nearest_PSD_projection_allowed"]:
        raise SystemExit("nearest-PSD projection must remain prohibited")

    models = [audit_model(record, comparator, reaction_order) for record in stress["matrices"]]
    all_acceptance = [value for model in models for value in model["acceptance"].values()]
    artifact = {
        "schema_version": 1,
        "artifact_id": "R0-CORRELATION-SAMPLER-AUDIT-v1",
        "task_id": "UQ0-R0-RATE-PRIOR",
        "status": (
            "preregistered_correlation_stress_sampler_numerically_validated_"
            "scientific_covariance_not_inferred"
        ),
        "source": {
            "candidate_contract": CANONICAL_CONTRACT_PATH,
            "candidate_contract_sha256": sha256(args.contract),
            "coherent_comparators": CANONICAL_COMPARATOR_PATH,
            "coherent_comparators_sha256": sha256(args.comparators),
        },
        "sampler": {
            "algorithm": "numpy_Generator_PCG64DXSM_standard_normal_then_registered_Cholesky",
            "base_seed": BASE_SEED,
            "model_seed_derivation": (
                "big_endian_uint64(first_8_bytes(SHA256(base_seed:model_id)))"
            ),
            "samples_per_model": SAMPLES_PER_MODEL,
            "replay_samples": REPLAY_SAMPLES,
            "float_dtype": "float64",
            "reaction_order": reaction_order,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "byteorder": sys.byteorder,
        },
        "acceptance_thresholds": {
            "Cholesky_max_abs": 1.0e-14,
            "empirical_correlation_max_abs": (EMPIRICAL_CORRELATION_ABS_TOLERANCE),
            "empirical_mean_max_abs": EMPIRICAL_MEAN_ABS_TOLERANCE,
            "empirical_std_minus_one_max_abs": EMPIRICAL_STD_ABS_TOLERANCE,
            "coherent_q_reconstruction_max_abs": 1.0e-12,
        },
        "models": models,
        "summary": {
            "model_records": len(models),
            "unique_matrix_sha256": len({model["matrix_sha256"] for model in models}),
            "all_model_checks_passed": all(all_acceptance),
            "max_abs_empirical_correlation_error": max(
                model["max_abs_empirical_correlation_error"] for model in models
            ),
            "max_abs_empirical_mean": max(model["max_abs_empirical_mean"] for model in models),
            "max_abs_empirical_std_minus_one": max(
                model["max_abs_empirical_std_minus_one"] for model in models
            ),
            "max_abs_coherent_q_reconstruction_error": max(
                model["coherent_temperature_curve_probe"]["max_abs_reconstructed_q_error"]
                for model in models
            ),
            "fixed_seed_replay_passed_models": sum(
                model["replay"]["exact_array_equal"] for model in models
            ),
            "nearest_PSD_projection_used_models": sum(
                model["nearest_PSD_projection_used"] for model in models
            ),
        },
        "claim_boundary": {
            "actual_ETR25_cross_reaction_covariance_inferred": False,
            "identity_is_scientific_default": False,
            "actual_posterior_reconstruction": False,
            "scientific_prior_reactions_accepted": 0,
            "production_use": "prohibited",
            "task_done_allowed": False,
            "A03_A00_A09_signoffs": "pending",
        },
        "payload_sha256_without_self_hash": None,
    }
    artifact["payload_sha256_without_self_hash"] = payload_sha256(
        {**artifact, "payload_sha256_without_self_hash": None}
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not artifact["summary"]["all_model_checks_passed"]:
        raise SystemExit("one or more correlation sampler audit checks failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
