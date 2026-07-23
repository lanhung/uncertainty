#!/usr/bin/env python3
"""Run the frozen LINX abundance-level native nuclear_rates_q reproduction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import socket
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.why_not_benchmark import (  # noqa: E402
    linx_abundances,
    load_linx,
    load_yaml,
)


ARTIFACT_ID = "LINX-NATIVE-Q-REPRODUCTION-v1"
TASK_ID = "UQ0-NATIVE-UQ-REPRO"
EXPECTED_REVISION = "ec2e9d2ca455e8204137e884da29f5dd13a638fa"
EXPECTED_CONFIG_SHA256 = "d55d7a9775f1e9a7e4fa41a9869870631137528714dce50051558795e55497b7"
EXPECTED_MAPPING_SHA256 = "6a958225feb3cc531753571c582376a0c5cf3404c1a4e6643482a0d8114e7418"
EXPECTED_PARAMETER_SHA256 = "4dfbf65ee04e4ab6502e18bf6b69c78a447c9c8d8db660033f2c03b560e04d7a"
EXPECTED_OBSERVATION_SHA256 = "02a4a5453afff34c7f1f036a33d46e728d49a954d46a34e52aa45a570f6f7a8c"
EXPECTED_LOCK_SHA256 = "98c8f6de35dfdf7147857a3c28153b10f3ad7d424cb9faeea15de75cacd27556"
OUTPUT_KEYS = ("Neff", "YPBBN", "DoH", "He3oH", "Li7oH")
NORMALIZED_KEYS = ("YPBBN", "DoH")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def git_revision(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def tracked_tree_clean(path: Path) -> bool:
    worktree_clean = (
        subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"],
            cwd=path,
            check=False,
        ).returncode
        == 0
    )
    index_clean = (
        subprocess.run(
            ["git", "diff", "--cached", "--quiet", "HEAD", "--"],
            cwd=path,
            check=False,
        ).returncode
        == 0
    )
    return worktree_clean and index_clean


def observation_sigmas(observation: dict[str, Any]) -> dict[str, float]:
    return {
        "YPBBN": float(observation["main_likelihood"]["helium4_mass_fraction"]["sigma"]),
        "DoH": float(observation["main_likelihood"]["deuterium_number_ratio"]["sigma"]) * 1.0e-5,
    }


def q_vectors(protocol: dict[str, Any]) -> dict[str, list[float]]:
    contract = protocol["q_contract"]
    length = int(contract["vector_length"])
    indices = {str(key): int(value) for key, value in contract["indices_zero_based"].items()}
    vectors: dict[str, list[float]] = {}
    for record in contract["vectors"]:
        vector = [0.0] * length
        reaction = str(record["reaction"])
        if reaction != "central":
            vector[indices[reaction]] = float(record["q"])
        vectors[str(record["id"])] = vector
    return vectors


def extract_abundances(raw: Any, neff: float, jax: Any, np: Any) -> dict[str, float]:
    array = np.asarray(jax.device_get(raw), dtype=float).reshape(-1)
    if array.shape != (8,):
        raise ValueError(f"unexpected LINX scalar abundance shape: {array.shape}")
    if not np.isfinite(array).all():
        raise FloatingPointError("LINX returned non-finite species abundances")
    values = linx_abundances(array.tolist(), neff)
    values["proton_denominator"] = float(array[1])
    if not all(math.isfinite(float(value)) for value in values.values()):
        raise FloatingPointError("LINX returned a non-finite derived abundance")
    return values


def extract_batch(
    raw: Any, expected_size: int, neff: float, jax: Any, np: Any
) -> list[dict[str, float]]:
    array = np.asarray(jax.device_get(raw), dtype=float)
    if array.shape[-1] != 8 and array.shape[0] == 8:
        array = np.moveaxis(array, 0, -1)
    if array.shape[-1] != 8:
        raise ValueError(f"unexpected LINX batch species axis: {array.shape}")
    array = array.reshape((-1, 8))
    if array.shape[0] != expected_size:
        raise ValueError(f"unexpected LINX batch size: {array.shape[0]} != {expected_size}")
    return [extract_abundances(row, neff, jax, np) for row in array]


def _row_values(row: dict[str, Any]) -> dict[str, float]:
    return {key: float(row["outputs"][key]) for key in OUTPUT_KEYS}


def _maximum_absolute_difference(left: dict[str, float], right: dict[str, float]) -> float:
    return max(abs(float(left[key]) - float(right[key])) for key in OUTPUT_KEYS)


def _maximum_normalized_difference(
    left: dict[str, float],
    right: dict[str, float],
    sigmas: dict[str, float],
) -> float:
    return max(
        abs(float(left[key]) - float(right[key])) / float(sigmas[key]) for key in NORMALIZED_KEYS
    )


def evaluate_results(
    protocol: dict[str, Any],
    scalar_rows: list[dict[str, Any]],
    batch_rows: list[dict[str, Any]],
    structured_failures: int,
    sigmas: dict[str, float],
) -> dict[str, Any]:
    """Recompute every frozen acceptance decision from raw abundance rows."""
    acceptance = protocol["acceptance"]
    cases = [str(case["id"]) for case in protocol["numerical_cases"]]
    vector_ids = [str(record["id"]) for record in protocol["q_contract"]["vectors"]]
    repetitions = int(protocol["execution"]["scalar_repetitions_per_case_q"])
    duplicate = int(protocol["execution"]["heterogeneous_batch"]["duplicate_each_q_vector"])
    batch_repetitions = int(protocol["execution"]["heterogeneous_batch"]["warm_repetitions"])
    batch_case = str(protocol["execution"]["heterogeneous_batch"]["numerical_case"])

    scalar_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in scalar_rows:
        key = (str(row["case_id"]), str(row["q_id"]), int(row["repetition"]))
        if key in scalar_by_key:
            raise ValueError(f"duplicate scalar row: {key}")
        scalar_by_key[key] = row
    expected_scalar = {
        (case_id, q_id, repetition)
        for case_id in cases
        for q_id in vector_ids
        for repetition in range(repetitions)
    }
    scalar_grid_complete = set(scalar_by_key) == expected_scalar

    batch_by_key: dict[tuple[int, str, int], dict[str, Any]] = {}
    for row in batch_rows:
        key = (int(row["repetition"]), str(row["q_id"]), int(row["duplicate"]))
        if key in batch_by_key:
            raise ValueError(f"duplicate batch row: {key}")
        batch_by_key[key] = row
        if str(row["case_id"]) != batch_case:
            raise ValueError("batch row numerical-case drift")
    expected_batch = {
        (repetition, q_id, duplicate_index)
        for repetition in range(batch_repetitions)
        for q_id in vector_ids
        for duplicate_index in range(duplicate)
    }
    batch_grid_complete = set(batch_by_key) == expected_batch

    all_rows = scalar_rows + batch_rows
    finite_outputs = True
    positive_protons = True
    row_status_ok = True
    for row in all_rows:
        row_status_ok &= row.get("status") == "ok"
        outputs = row.get("outputs", {})
        finite_outputs &= set(outputs) == set(OUTPUT_KEYS)
        finite_outputs &= all(
            math.isfinite(float(outputs.get(key, math.nan))) for key in OUTPUT_KEYS
        )
        positive_protons &= (
            math.isfinite(float(row.get("proton_denominator", math.nan)))
            and float(row.get("proton_denominator", math.nan)) > 0.0
        )

    maximum_scalar_repeat_drift = 0.0
    if scalar_grid_complete:
        for case_id in cases:
            for q_id in vector_ids:
                reference = _row_values(scalar_by_key[(case_id, q_id, 0)])
                for repetition in range(1, repetitions):
                    maximum_scalar_repeat_drift = max(
                        maximum_scalar_repeat_drift,
                        _maximum_absolute_difference(
                            reference,
                            _row_values(scalar_by_key[(case_id, q_id, repetition)]),
                        ),
                    )
    else:
        maximum_scalar_repeat_drift = math.inf

    maximum_batch_repeat_drift = 0.0
    if batch_grid_complete:
        for q_id in vector_ids:
            reference = _row_values(batch_by_key[(0, q_id, 0)])
            for repetition in range(batch_repetitions):
                for duplicate_index in range(duplicate):
                    maximum_batch_repeat_drift = max(
                        maximum_batch_repeat_drift,
                        _maximum_absolute_difference(
                            reference,
                            _row_values(batch_by_key[(repetition, q_id, duplicate_index)]),
                        ),
                    )
    else:
        maximum_batch_repeat_drift = math.inf

    maximum_scalar_batch_sigma = math.inf
    if scalar_grid_complete and batch_grid_complete:
        maximum_scalar_batch_sigma = 0.0
        for q_id in vector_ids:
            scalar = _row_values(scalar_by_key[(batch_case, q_id, 0)])
            for repetition in range(batch_repetitions):
                for duplicate_index in range(duplicate):
                    maximum_scalar_batch_sigma = max(
                        maximum_scalar_batch_sigma,
                        _maximum_normalized_difference(
                            scalar,
                            _row_values(batch_by_key[(repetition, q_id, duplicate_index)]),
                            sigmas,
                        ),
                    )

    plateau_results: dict[str, Any] = {}
    for name, pair in acceptance["plateau_pairs"].items():
        left, right = (str(value) for value in pair)
        maximum = math.inf
        if scalar_grid_complete:
            maximum = 0.0
            for q_id in vector_ids:
                maximum = max(
                    maximum,
                    _maximum_normalized_difference(
                        _row_values(scalar_by_key[(left, q_id, 0)]),
                        _row_values(scalar_by_key[(right, q_id, 0)]),
                        sigmas,
                    ),
                )
        plateau_results[str(name)] = {
            "case_ids": [left, right],
            "maximum_difference_observation_sigma": (maximum if math.isfinite(maximum) else None),
            "passed": (
                math.isfinite(maximum)
                and maximum <= float(acceptance["maximum_plateau_difference_observation_sigma"])
            ),
        }

    response_results: dict[str, Any] = {}
    response_pass = scalar_grid_complete
    if scalar_grid_complete:
        central = float(scalar_by_key[(batch_case, "q0", 0)]["outputs"]["DoH"])
        for reaction in protocol["q_contract"]["canonical_order"]:
            minus = float(scalar_by_key[(batch_case, f"{reaction}_m1", 0)]["outputs"]["DoH"])
            plus = float(scalar_by_key[(batch_case, f"{reaction}_p1", 0)]["outputs"]["DoH"])
            straddles = min(minus, plus) <= central <= max(minus, plus)
            nonzero = minus != central and plus != central and minus != plus
            passed = straddles and nonzero
            response_results[str(reaction)] = {
                "central": central,
                "minus_one": minus,
                "plus_one": plus,
                "minus_shift": minus - central,
                "plus_shift": plus - central,
                "straddles_central": straddles,
                "nonzero_response": nonzero,
                "passed": passed,
            }
            response_pass &= passed

    checks = {
        "expected_scalar_rows": len(scalar_rows) == int(acceptance["expected_scalar_rows"]),
        "expected_batch_rows": len(batch_rows) == int(acceptance["expected_batch_rows"]),
        "scalar_grid_complete": scalar_grid_complete,
        "batch_grid_complete": batch_grid_complete,
        "zero_structured_failures": structured_failures == 0,
        "row_status_ok": row_status_ok,
        "finite_outputs": finite_outputs,
        "positive_proton_denominator": positive_protons,
        "zero_scalar_repeat_drift": maximum_scalar_repeat_drift == 0.0,
        "zero_batch_repeat_drift": maximum_batch_repeat_drift == 0.0,
        "scalar_batch_budget": (
            math.isfinite(maximum_scalar_batch_sigma)
            and maximum_scalar_batch_sigma
            <= float(acceptance["maximum_scalar_batch_difference_observation_sigma"])
        ),
        "all_plateaus": all(record["passed"] for record in plateau_results.values()),
        "D_over_H_plus_minus_responses": response_pass,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "maximum_batch_repeat_drift": (
            maximum_batch_repeat_drift if math.isfinite(maximum_batch_repeat_drift) else None
        ),
        "maximum_scalar_batch_difference_observation_sigma": (
            maximum_scalar_batch_sigma if math.isfinite(maximum_scalar_batch_sigma) else None
        ),
        "maximum_scalar_repeat_drift": (
            maximum_scalar_repeat_drift if math.isfinite(maximum_scalar_repeat_drift) else None
        ),
        "passed": passed,
        "plateaus": plateau_results,
        "response_checks": response_results,
        "status": "accepted" if passed else "not_accepted",
    }


def validate_frozen_inputs(
    protocol: dict[str, Any],
    config_path: Path,
    parameter_path: Path,
    observation_path: Path,
    mapping_path: Path,
    lock_path: Path,
) -> None:
    expected = {
        config_path: EXPECTED_CONFIG_SHA256,
        parameter_path: EXPECTED_PARAMETER_SHA256,
        observation_path: EXPECTED_OBSERVATION_SHA256,
        mapping_path: EXPECTED_MAPPING_SHA256,
        lock_path: EXPECTED_LOCK_SHA256,
    }
    for path, digest in expected.items():
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"frozen input drift: {path}")
    if (
        protocol["reproduction_id"] != ARTIFACT_ID
        or protocol["task_id"] != TASK_ID
        or protocol["status"] != "protocol_frozen_measurements_pending"
        or protocol["source"]["revision"] != EXPECTED_REVISION
        or protocol["source"]["network"] != "key_recommended"
        or protocol["source"]["precision"] != "float64"
    ):
        raise ValueError("frozen LINX protocol identity drift")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if (
        mapping["artifact_id"] != protocol["prerequisites"]["mapping_artifact"]["artifact_id"]
        or mapping["acceptance"]["passes"] is not True
        or mapping["source"]["revision"] != EXPECTED_REVISION
        or mapping["interface_contract"]["R0_q_indices_zero_based"] != [1, 2, 3]
    ):
        raise ValueError("LINX R0 mapping prerequisite is not accepted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--parameter-schema", type=Path, required=True)
    parser.add_argument("--observation-config", type=Path, required=True)
    parser.add_argument("--mapping-artifact", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--environment-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hourly-price-cny", type=float, required=True)
    parser.add_argument("--yaml-python", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protocol, protocol_loader = load_yaml(args.config, args.yaml_python)
    parameter_schema, parameter_loader = load_yaml(args.parameter_schema, args.yaml_python)
    observation, observation_loader = load_yaml(args.observation_config, args.yaml_python)
    validate_frozen_inputs(
        protocol,
        args.config,
        args.parameter_schema,
        args.observation_config,
        args.mapping_artifact,
        args.environment_lock,
    )
    if observation["decision_status"] != "frozen":
        raise ValueError("observation normalization source is not frozen")
    parameters = protocol["parameter_set"]["values"]
    if parameter_schema["standard_bbn_fiducial"]["values"] != parameters:
        raise ValueError("protocol and parameter-schema fiducial values differ")
    revision = git_revision(args.source_dir)
    if revision != EXPECTED_REVISION:
        raise ValueError(f"LINX revision drift: {revision}")
    if not tracked_tree_clean(args.source_dir):
        raise ValueError("LINX frozen source has tracked modifications")
    if not args.inventory.is_file():
        raise FileNotFoundError(args.inventory)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=False)
    timings_path = output_dir / "timings.jsonl"
    failures_path = output_dir / "failures.jsonl"
    timings_path.touch()
    failures_path.touch()

    os.environ.setdefault("JAX_ENABLE_X64", "True")
    import numpy as np
    import jaxlib

    import_started = time.perf_counter()
    modules, load_provenance = load_linx(args.source_dir)
    import_seconds = time.perf_counter() - import_started
    jax = modules["jax"]
    jnp = modules["jnp"]
    const = modules["const"]
    if (
        not bool(jax.config.x64_enabled)
        or jax.default_backend() != protocol["environment"]["backend"]
        or jax.__version__ != protocol["environment"]["jax"]
        or jaxlib.__version__ != protocol["environment"]["jaxlib"]
    ):
        raise RuntimeError("LINX JAX environment differs from frozen protocol")

    background_model = modules["BackgroundModel"]()
    background_started = time.perf_counter()
    background_raw = background_model(jnp.asarray(parameters["delta_neff"]))
    jax.block_until_ready(background_raw)
    background_seconds = time.perf_counter() - background_started
    t_vec, a_vec, rho_g, rho_nu, rho_np, pressure_np, neff_vec = background_raw
    neff = float(jax.device_get(neff_vec[-1]))
    abundance_model = modules["AbundanceModel"](
        modules["NuclearRates"](nuclear_net=protocol["source"]["network"])
    )
    if len(abundance_model.nuclear_net.reactions) != int(protocol["q_contract"]["vector_length"]):
        raise ValueError("LINX network reaction count differs from q contract")
    if list(abundance_model.nuclear_net.reactions_names) != list(
        protocol["q_contract"]["network_reaction_order"]
    ):
        raise ValueError("LINX native reaction order differs from frozen q contract")

    eta_fac = float(parameters["omega_b_h2"]) / float(const.Omegabh2)
    tau_n_fac = float(parameters["tau_n_seconds"]) / float(const.tau_n)
    vectors = q_vectors(protocol)
    sigmas = observation_sigmas(observation)
    started_at = utc_now()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    scalar_rows: list[dict[str, Any]] = []
    batch_rows: list[dict[str, Any]] = []
    structured_failures = 0
    total_progress = int(protocol["acceptance"]["expected_scalar_rows"]) + int(
        protocol["execution"]["heterogeneous_batch"]["warm_repetitions"]
    )
    progress = 0

    for case in protocol["numerical_cases"]:
        case_id = str(case["id"])

        def solve_scalar(q_vector: Any) -> Any:
            return abundance_model(
                rho_g,
                rho_nu,
                rho_np,
                pressure_np,
                t_vec=t_vec,
                a_vec=a_vec,
                eta_fac=jnp.asarray(eta_fac, dtype=jnp.float64),
                tau_n_fac=jnp.asarray(tau_n_fac, dtype=jnp.float64),
                nuclear_rates_q=jnp.asarray(q_vector, dtype=jnp.float64),
                rtol=float(case["rtol"]),
                atol=float(case["atol"]),
                sampling_nTOp=int(case["sampling_nTOp"]),
                max_steps=int(case["max_steps"]),
            )

        for q_id, vector in vectors.items():
            for repetition in range(int(protocol["execution"]["scalar_repetitions_per_case_q"])):
                row_started = time.perf_counter()
                try:
                    raw = solve_scalar(vector)
                    jax.block_until_ready(raw)
                    values = extract_abundances(raw, neff, jax, np)
                    row = {
                        "case_id": case_id,
                        "mode": "scalar",
                        "outputs": {key: float(values[key]) for key in OUTPUT_KEYS},
                        "proton_denominator": values["proton_denominator"],
                        "q_id": q_id,
                        "q_vector": vector,
                        "repetition": repetition,
                        "status": "ok",
                    }
                    scalar_rows.append(row)
                    status = "ok"
                except Exception as exc:  # pragma: no cover - worker boundary
                    structured_failures += 1
                    status = "failed"
                    append_jsonl(
                        failures_path,
                        {
                            "case_id": case_id,
                            "error": repr(exc),
                            "kind": "scalar_solver_exception",
                            "q_id": q_id,
                            "repetition": repetition,
                            "traceback": traceback.format_exc(),
                        },
                    )
                elapsed = time.perf_counter() - row_started
                append_jsonl(
                    timings_path,
                    {
                        "case_id": case_id,
                        "elapsed_seconds": elapsed,
                        "kind": "scalar",
                        "q_id": q_id,
                        "repetition": repetition,
                        "status": status,
                    },
                )
                progress += 1
                print(f"PROGRESS {progress}/{total_progress}", flush=True)

    heterogeneous = protocol["execution"]["heterogeneous_batch"]
    candidate = next(
        case
        for case in protocol["numerical_cases"]
        if case["id"] == heterogeneous["numerical_case"]
    )
    batch_order = [str(value) for value in heterogeneous["q_vector_order"]]
    duplicate = int(heterogeneous["duplicate_each_q_vector"])
    batch_descriptors = [
        (q_id, duplicate_index) for q_id in batch_order for duplicate_index in range(duplicate)
    ]
    q_matrix = jnp.asarray([vectors[q_id] for q_id, _ in batch_descriptors], dtype=jnp.float64)

    def solve_batch_member(q_vector: Any) -> Any:
        return abundance_model(
            rho_g,
            rho_nu,
            rho_np,
            pressure_np,
            t_vec=t_vec,
            a_vec=a_vec,
            eta_fac=jnp.asarray(eta_fac, dtype=jnp.float64),
            tau_n_fac=jnp.asarray(tau_n_fac, dtype=jnp.float64),
            nuclear_rates_q=q_vector,
            rtol=float(candidate["rtol"]),
            atol=float(candidate["atol"]),
            sampling_nTOp=int(candidate["sampling_nTOp"]),
            max_steps=int(candidate["max_steps"]),
        )

    batched_solve = jax.jit(jax.vmap(solve_batch_member, in_axes=0))
    cold_batch_started = time.perf_counter()
    cold_batch_raw = batched_solve(q_matrix)
    jax.block_until_ready(cold_batch_raw)
    cold_batch_seconds = time.perf_counter() - cold_batch_started
    append_jsonl(
        timings_path,
        {
            "batch_size": len(batch_descriptors),
            "elapsed_seconds": cold_batch_seconds,
            "kind": "cold_heterogeneous_batch_compile_and_solve",
            "status": "ok",
        },
    )
    for repetition in range(int(heterogeneous["warm_repetitions"])):
        batch_started = time.perf_counter()
        try:
            raw = batched_solve(q_matrix)
            jax.block_until_ready(raw)
            values = extract_batch(raw, len(batch_descriptors), neff, jax, np)
            for (q_id, duplicate_index), result in zip(batch_descriptors, values):
                batch_rows.append(
                    {
                        "case_id": str(candidate["id"]),
                        "duplicate": duplicate_index,
                        "mode": "heterogeneous_batch",
                        "outputs": {key: float(result[key]) for key in OUTPUT_KEYS},
                        "proton_denominator": result["proton_denominator"],
                        "q_id": q_id,
                        "q_vector": vectors[q_id],
                        "repetition": repetition,
                        "row_index": len(batch_rows),
                        "status": "ok",
                    }
                )
            status = "ok"
        except Exception as exc:  # pragma: no cover - worker boundary
            structured_failures += 1
            status = "failed"
            append_jsonl(
                failures_path,
                {
                    "error": repr(exc),
                    "kind": "heterogeneous_batch_solver_exception",
                    "repetition": repetition,
                    "traceback": traceback.format_exc(),
                },
            )
        elapsed = time.perf_counter() - batch_started
        append_jsonl(
            timings_path,
            {
                "batch_size": len(batch_descriptors),
                "elapsed_seconds": elapsed,
                "kind": "warm_heterogeneous_batch",
                "repetition": repetition,
                "status": status,
            },
        )
        progress += 1
        print(f"PROGRESS {progress}/{total_progress}", flush=True)

    decision = evaluate_results(protocol, scalar_rows, batch_rows, structured_failures, sigmas)
    finished_at = utc_now()
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    usage = resource.getrusage(resource.RUSAGE_SELF)
    run_id = str(uuid.uuid4())
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))

    results_path = output_dir / "results.json"
    write_json(
        results_path,
        {
            "batch_rows": batch_rows,
            "decision": decision,
            "observation_sigmas": sigmas,
            "scalar_rows": scalar_rows,
            "schema_version": 1,
            "structured_failure_count": structured_failures,
        },
    )
    resource_path = output_dir / "resource_report.json"
    write_json(
        resource_path,
        {
            "cpu_core_hours": cpu_seconds / 3600.0,
            "cpu_seconds": cpu_seconds,
            "estimated_cost_cny": wall_seconds / 3600.0 * args.hourly_price_cny,
            "gpu_hours": 0.0,
            "hourly_price_cny": args.hourly_price_cny,
            "max_rss_bytes": usage.ru_maxrss * 1024,
            "schema_version": 1,
            "wall_seconds": wall_seconds,
            "worker_hours": wall_seconds / 3600.0,
        },
    )
    manifest_path = output_dir / "run_manifest.json"
    write_json(
        manifest_path,
        {
            "artifact_id": ARTIFACT_ID,
            "background_reused_across_q_draws": True,
            "cold_background_seconds": background_seconds,
            "cold_import_seconds": import_seconds,
            "config_sha256": sha256(args.config),
            "environment": {
                "backend": jax.default_backend(),
                "jax": jax.__version__,
                "jaxlib": jaxlib.__version__,
                "python": platform.python_version(),
                "x64": bool(jax.config.x64_enabled),
            },
            "environment_lock_sha256": sha256(args.environment_lock),
            "finished_at_utc": finished_at,
            "hardware_inventory_sha256": sha256(args.inventory),
            "hostname": socket.gethostname(),
            "load_provenance": load_provenance,
            "mapping_artifact_sha256": sha256(args.mapping_artifact),
            "metadata_loaders": {
                "observation": observation_loader,
                "parameter_schema": parameter_loader,
                "protocol": protocol_loader,
            },
            "node_name": inventory["node_name"],
            "observation_config_sha256": sha256(args.observation_config),
            "parameter_schema_sha256": sha256(args.parameter_schema),
            "parameters": parameters,
            "platform": platform.platform(),
            "run_id": run_id,
            "schema_version": 1,
            "source_revision": revision,
            "source_tracked_tree_clean": True,
            "started_at_utc": started_at,
            "status": "complete" if structured_failures == 0 else "complete_with_failures",
            "task_id": TASK_ID,
        },
    )
    evidence = {
        "artifact_id": ARTIFACT_ID,
        "claim_boundary": protocol["claim_boundary"],
        "companion_sha256": {
            "failures.jsonl": sha256(failures_path),
            "resource_report.json": sha256(resource_path),
            "results.json": sha256(results_path),
            "run_manifest.json": sha256(manifest_path),
            "timings.jsonl": sha256(timings_path),
        },
        "decision": decision,
        "generated_at_utc": finished_at,
        "reproduction_id": protocol["reproduction_id"],
        "schema_version": 1,
        "scientific_scope": (
            "LINX native scalar-envelope abundance calibration at one frozen "
            "standard-BBN point; not a selected project prior or posterior"
        ),
        "status": "accepted_C0_calibration" if decision["passed"] else "complete_not_accepted",
        "task_id": TASK_ID,
    }
    evidence["evidence_sha256"] = digest_json(evidence)
    write_json(output_dir / "reproduction.json", evidence)
    print(output_dir)
    return 0 if decision["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
