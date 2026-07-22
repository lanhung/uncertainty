#!/usr/bin/env python3
"""Run a frozen LINX scalar/native-batch numerical consistency scan."""

from __future__ import annotations

import argparse
import json
import platform
import resource
import socket
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.why_not_benchmark import (  # noqa: E402
    append_jsonl,
    git_revision,
    json_dump,
    load_abcmb_linx,
    linx_abundances,
    load_linx,
    load_yaml,
    sha256,
    summarize,
    utc_now,
)


ABUNDANCE_KEYS = ("Neff", "YPBBN", "DoH", "He3oH", "Li7oH")


def observation_sigmas(observation: dict[str, Any]) -> dict[str, float]:
    return {
        "YPBBN": float(observation["main_likelihood"]["helium4_mass_fraction"]["sigma"]),
        "DoH": (float(observation["main_likelihood"]["deuterium_number_ratio"]["sigma"]) * 1.0e-5),
    }


def absolute_differences(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    return {key: abs(float(left[key]) - float(right[key])) for key in ABUNDANCE_KEYS}


def normalized_differences(
    left: dict[str, float], right: dict[str, float], sigmas: dict[str, float]
) -> dict[str, float]:
    return {key: abs(float(left[key]) - float(right[key])) / sigma for key, sigma in sigmas.items()}


def maximum_normalized_difference(
    left: dict[str, float], right: dict[str, float], sigmas: dict[str, float]
) -> float:
    return max(normalized_differences(left, right, sigmas).values())


def evaluate_scan(
    cases: dict[str, dict[str, Any]],
    acceptance: dict[str, Any],
    sigmas: dict[str, float],
) -> dict[str, Any]:
    candidate_ids = list(acceptance["candidate_case_ids"])
    scalar_batch_limit = float(acceptance["maximum_scalar_batch_difference_observation_sigma"])
    plateau_limit = float(acceptance["maximum_plateau_difference_observation_sigma"])
    missing_or_failed = [
        case_id for case_id in candidate_ids if cases.get(case_id, {}).get("status") != "ok"
    ]
    candidate_differences = {
        case_id: cases[case_id]["maximum_scalar_batch_difference_observation_sigma"]
        for case_id in candidate_ids
        if cases.get(case_id, {}).get("status") == "ok"
    }
    scalar_batch_pass = not missing_or_failed and all(
        value <= scalar_batch_limit for value in candidate_differences.values()
    )

    plateau_pairs = acceptance.get("plateau_pairs")
    if plateau_pairs is None:
        plateau_pairs = {
            "tolerance": acceptance["tolerance_plateau_pair"],
            "weak_rate_sampling": acceptance["sampling_plateau_pair"],
        }
    plateau_results: dict[str, Any] = {}
    for name, pair in plateau_pairs.items():
        left_id, right_id = pair
        left = cases.get(left_id)
        right = cases.get(right_id)
        if (
            left is None
            or right is None
            or left.get("status") != "ok"
            or right.get("status") != "ok"
        ):
            plateau_results[name] = {
                "case_ids": [left_id, right_id],
                "maximum_difference_observation_sigma": None,
                "passed": False,
            }
            continue
        scalar_difference = maximum_normalized_difference(
            left["scalar_abundances"], right["scalar_abundances"], sigmas
        )
        batch_difference = maximum_normalized_difference(
            left["batch_abundances"], right["batch_abundances"], sigmas
        )
        maximum_difference = max(scalar_difference, batch_difference)
        plateau_results[name] = {
            "batch_difference_observation_sigma": batch_difference,
            "case_ids": [left_id, right_id],
            "maximum_difference_observation_sigma": maximum_difference,
            "passed": maximum_difference <= plateau_limit,
            "scalar_difference_observation_sigma": scalar_difference,
        }

    completed = [case for case in cases.values() if case.get("status") == "ok"]
    repeat_pass = all(case["maximum_repeat_drift"] == 0.0 for case in completed)
    within_batch_pass = all(case["maximum_within_batch_spread"] == 0.0 for case in completed)
    required_ids = set(candidate_ids)
    for pair in plateau_pairs.values():
        required_ids.update(pair)
    all_required_cases_complete = all(
        cases.get(case_id, {}).get("status") == "ok" for case_id in required_ids
    )
    passed = (
        all_required_cases_complete
        and scalar_batch_pass
        and all(result["passed"] for result in plateau_results.values())
        and (repeat_pass or not acceptance["require_zero_repeat_drift"])
        and (within_batch_pass or not acceptance["require_zero_within_batch_spread"])
    )
    return {
        "all_required_cases_complete": all_required_cases_complete,
        "candidate_case_differences_observation_sigma": candidate_differences,
        "candidate_scalar_batch_pass": scalar_batch_pass,
        "limits_observation_sigma": {
            "plateau": plateau_limit,
            "scalar_batch": scalar_batch_limit,
        },
        "missing_or_failed_candidate_cases": missing_or_failed,
        "numerical_consistency_status": "accepted" if passed else "not_accepted",
        "passed": passed,
        "plateaus": plateau_results,
        "repeat_drift_pass": repeat_pass,
        "scientific_scope": "standard_fiducial_scalar_native_batch_consistency_only",
        "within_batch_spread_pass": within_batch_pass,
    }


def extract_batch(
    raw: Any, batch_size: int, neff: float, jax: Any, np: Any
) -> list[dict[str, float]]:
    matrix = np.asarray(jax.device_get(raw))
    if matrix.shape[-1] != 8 and matrix.shape[0] == 8:
        matrix = np.moveaxis(matrix, 0, -1)
    if matrix.shape[-1] != 8:
        raise ValueError(f"unexpected LINX batch species axis: {matrix.shape}")
    matrix = matrix.reshape((-1, 8))
    if matrix.shape[0] != batch_size:
        raise ValueError(f"unexpected LINX batch size: {matrix.shape[0]} != {batch_size}")
    return [linx_abundances(row.tolist(), neff) for row in matrix]


def run_case(
    case: dict[str, Any],
    abundance_model: Any,
    background: tuple[Any, ...],
    eta_fac: float,
    tau_n_fac: float,
    neff: float,
    batch_size: int,
    repetitions: int,
    sigmas: dict[str, float],
    timings_path: Path,
    jax: Any,
    jnp: Any,
    np: Any,
) -> dict[str, Any]:
    t_vec, a_vec, rho_g, rho_nu, rho_np, pressure_np = background
    rtol = float(case["rtol"])
    atol = float(case["atol"])
    sampling_n_top = int(case["sampling_nTOp"])
    max_steps = int(case.get("max_steps", 4096))

    def solve_raw(eta_value: Any, tau_value: Any) -> Any:
        return abundance_model(
            rho_g,
            rho_nu,
            rho_np,
            pressure_np,
            t_vec=t_vec,
            a_vec=a_vec,
            eta_fac=jnp.asarray(eta_value),
            tau_n_fac=jnp.asarray(tau_value),
            rtol=rtol,
            atol=atol,
            sampling_nTOp=sampling_n_top,
            max_steps=max_steps,
        )

    scalar_started = time.perf_counter()
    scalar_raw = solve_raw(eta_fac, tau_n_fac)
    jax.block_until_ready(scalar_raw)
    scalar_compile_seconds = time.perf_counter() - scalar_started
    scalar_reference = linx_abundances([float(value) for value in jax.device_get(scalar_raw)], neff)
    append_jsonl(
        timings_path,
        {
            "case_id": case["id"],
            "elapsed_seconds": scalar_compile_seconds,
            "kind": "cold_scalar_compile_and_solve",
            "status": "ok",
        },
    )

    scalar_durations: list[float] = []
    maximum_repeat_drift = 0.0
    for repetition in range(repetitions):
        started = time.perf_counter()
        raw = solve_raw(eta_fac, tau_n_fac)
        jax.block_until_ready(raw)
        values = linx_abundances([float(value) for value in jax.device_get(raw)], neff)
        elapsed = time.perf_counter() - started
        scalar_durations.append(elapsed)
        maximum_repeat_drift = max(
            maximum_repeat_drift,
            *(abs(values[key] - scalar_reference[key]) for key in ABUNDANCE_KEYS),
        )
        append_jsonl(
            timings_path,
            {
                "case_id": case["id"],
                "elapsed_seconds": elapsed,
                "kind": "warm_scalar",
                "repetition": repetition,
                "status": "ok",
            },
        )

    batched_solve = jax.jit(jax.vmap(solve_raw, in_axes=(0, 0)))
    eta_values = jnp.full((batch_size,), eta_fac, dtype=jnp.float64)
    tau_values = jnp.full((batch_size,), tau_n_fac, dtype=jnp.float64)
    batch_started = time.perf_counter()
    batch_raw = batched_solve(eta_values, tau_values)
    jax.block_until_ready(batch_raw)
    batch_compile_seconds = time.perf_counter() - batch_started
    rows = extract_batch(batch_raw, batch_size, neff, jax, np)
    batch_reference = rows[0]
    maximum_within_batch_spread = max(
        abs(row[key] - batch_reference[key]) for row in rows for key in ABUNDANCE_KEYS
    )
    append_jsonl(
        timings_path,
        {
            "batch_size": batch_size,
            "case_id": case["id"],
            "elapsed_seconds": batch_compile_seconds,
            "kind": "cold_batch_compile_and_solve",
            "status": "ok",
        },
    )

    batch_durations: list[float] = []
    for repetition in range(repetitions):
        started = time.perf_counter()
        raw = batched_solve(eta_values, tau_values)
        jax.block_until_ready(raw)
        repeat_rows = extract_batch(raw, batch_size, neff, jax, np)
        elapsed = time.perf_counter() - started
        batch_durations.append(elapsed)
        maximum_repeat_drift = max(
            maximum_repeat_drift,
            *(
                abs(row[key] - batch_reference[key])
                for row in repeat_rows
                for key in ABUNDANCE_KEYS
            ),
        )
        maximum_within_batch_spread = max(
            maximum_within_batch_spread,
            *(abs(row[key] - repeat_rows[0][key]) for row in repeat_rows for key in ABUNDANCE_KEYS),
        )
        append_jsonl(
            timings_path,
            {
                "batch_size": batch_size,
                "case_id": case["id"],
                "elapsed_seconds": elapsed,
                "kind": "warm_batch",
                "per_point_seconds": elapsed / batch_size,
                "repetition": repetition,
                "status": "ok",
            },
        )

    return {
        "absolute_scalar_batch_difference": absolute_differences(scalar_reference, batch_reference),
        "atol": atol,
        "batch_abundances": batch_reference,
        "group": case["group"],
        "max_steps": max_steps,
        "maximum_repeat_drift": maximum_repeat_drift,
        "maximum_scalar_batch_difference_observation_sigma": (
            maximum_normalized_difference(scalar_reference, batch_reference, sigmas)
        ),
        "maximum_within_batch_spread": maximum_within_batch_spread,
        "normalized_scalar_batch_difference": normalized_differences(
            scalar_reference, batch_reference, sigmas
        ),
        "rtol": rtol,
        "sampling_nTOp": sampling_n_top,
        "scalar_abundances": scalar_reference,
        "status": "ok",
        "timings_seconds": {
            "cold_batch_compile_and_solve": batch_compile_seconds,
            "cold_scalar_compile_and_solve": scalar_compile_seconds,
            "warm_batch": summarize(batch_durations),
            "warm_scalar": summarize(scalar_durations),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--benchmark-config", required=True, type=Path)
    parser.add_argument("--parameter-schema", required=True, type=Path)
    parser.add_argument("--observation-config", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--environment-lock", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--hourly-price-cny", required=True, type=float)
    parser.add_argument("--yaml-python", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scan, scan_loader = load_yaml(args.config, args.yaml_python)
    benchmark, benchmark_loader = load_yaml(args.benchmark_config, args.yaml_python)
    parameter_schema, schema_loader = load_yaml(args.parameter_schema, args.yaml_python)
    observation, observation_loader = load_yaml(args.observation_config, args.yaml_python)
    if scan["status"] != "protocol_frozen_measurements_pending":
        raise ValueError("LINX scalar/native-batch scan protocol is not frozen")
    if observation["decision_status"] != "frozen":
        raise ValueError("observation normalization source is not frozen")
    if parameter_schema["status"] != "standard_bbn_subset_frozen_extension_semantics_pending":
        raise ValueError("standard-BBN parameter subset is not frozen")
    baseline = scan["baseline"]
    if baseline not in {"W0-LINX", "W3-ABCMB"}:
        raise ValueError(f"unsupported LINX scan baseline: {baseline}")
    if scan["source_revision"] != benchmark["baselines"][baseline]["revision"]:
        raise ValueError("scan and WHY-NOT benchmark source revisions differ")
    if (
        baseline == "W3-ABCMB"
        and scan["bundled_linx_tree"] != benchmark["baselines"][baseline]["bundled_linx_tree"]
    ):
        raise ValueError("scan and WHY-NOT bundled LINX trees differ")
    revision = git_revision(args.source_dir)
    if revision != scan["source_revision"]:
        raise ValueError(f"source revision {revision} != registered {scan['source_revision']}")
    for required in (args.inventory, args.environment_lock):
        if not required.is_file():
            raise FileNotFoundError(required)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=False)
    timings_path = output_dir / "timings.jsonl"
    failures_path = output_dir / "failures.jsonl"
    timings_path.touch()
    failures_path.touch()

    import numpy as np

    import_started = time.perf_counter()
    modules, load_provenance = (
        load_abcmb_linx(args.source_dir) if baseline == "W3-ABCMB" else load_linx(args.source_dir)
    )
    if baseline == "W3-ABCMB" and load_provenance["bundled_linx_tree"] != scan["bundled_linx_tree"]:
        raise ValueError("loaded ABCMB bundled LINX tree differs from frozen scan")
    import_seconds = time.perf_counter() - import_started
    jax = modules["jax"]
    jnp = modules["jnp"]
    const = modules["const"]
    background_model = modules["BackgroundModel"]()
    parameters = parameter_schema["standard_bbn_fiducial"]["values"]
    if baseline == "W3-ABCMB":
        background_numerics = scan["background_numerics"]
        background_raw = background_model(
            jnp.asarray(parameters["delta_neff"]),
            rtol=float(background_numerics["rtol"]),
            atol=float(background_numerics["atol"]),
            max_steps=int(background_numerics["max_steps"]),
        )
    else:
        background_raw = background_model(jnp.asarray(parameters["delta_neff"]))
    jax.block_until_ready(background_raw)
    t_vec, a_vec, rho_g, rho_nu, rho_np, pressure_np, neff_vec = background_raw
    background = (t_vec, a_vec, rho_g, rho_nu, rho_np, pressure_np)
    abundance_model = modules["AbundanceModel"](
        modules["NuclearRates"](nuclear_net=scan["network"])
    )
    eta_fac = parameters["omega_b_h2"] / float(const.Omegabh2)
    tau_n_fac = parameters["tau_n_seconds"] / float(const.tau_n)
    neff = float(jax.device_get(neff_vec[-1]))
    sigmas = observation_sigmas(observation)

    started_at = utc_now()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    cases: dict[str, dict[str, Any]] = {}
    for case in scan["cases"]:
        case_id = case["id"]
        try:
            cases[case_id] = run_case(
                case,
                abundance_model,
                background,
                eta_fac,
                tau_n_fac,
                neff,
                int(scan["batch_size"]),
                int(scan["warm_repetitions"]),
                sigmas,
                timings_path,
                jax,
                jnp,
                np,
            )
        except Exception as exc:  # pragma: no cover - worker failure boundary
            cases[case_id] = {
                "atol": float(case["atol"]),
                "error": repr(exc),
                "group": case["group"],
                "max_steps": int(case.get("max_steps", 4096)),
                "rtol": float(case["rtol"]),
                "sampling_nTOp": int(case["sampling_nTOp"]),
                "status": "failed",
            }
            append_jsonl(
                failures_path,
                {
                    "case_id": case_id,
                    "error": repr(exc),
                    "kind": "solver_exception",
                    "traceback": traceback.format_exc(),
                },
            )
        jax.clear_caches()

    decision = evaluate_scan(cases, scan["acceptance"], sigmas)
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    finished_at = utc_now()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    failures = sum(case["status"] != "ok" for case in cases.values())
    run_id = str(uuid.uuid4())

    json_dump(
        output_dir / "run_manifest.json",
        {
            "benchmark_config": str(args.benchmark_config),
            "benchmark_config_sha256": sha256(args.benchmark_config),
            "baseline": baseline,
            "environment_lock": str(args.environment_lock),
            "environment_lock_sha256": sha256(args.environment_lock),
            "finished_at_utc": finished_at,
            "hardware_inventory": str(args.inventory),
            "hardware_inventory_sha256": sha256(args.inventory),
            "hostname": socket.gethostname(),
            "metadata_loaders": {
                "benchmark": benchmark_loader,
                "observation": observation_loader,
                "parameter_schema": schema_loader,
                "scan": scan_loader,
            },
            "node_name": json.loads(args.inventory.read_text(encoding="utf-8"))["node_name"],
            "observation_config": str(args.observation_config),
            "observation_config_sha256": sha256(args.observation_config),
            "parameter_schema": str(args.parameter_schema),
            "parameter_schema_sha256": sha256(args.parameter_schema),
            "parameters": parameters,
            "platform": platform.platform(),
            "precision": scan["precision"],
            "python": sys.version,
            "run_id": run_id,
            "scan_config": str(args.config),
            "scan_config_sha256": sha256(args.config),
            "scan_id": scan["scan_id"],
            "schema_version": 1,
            "scientific_use": "standard_fiducial_scalar_native_batch_consistency_only",
            "source_dir": str(args.source_dir),
            "source_revision": revision,
            "started_at_utc": started_at,
            "status": "complete" if failures == 0 else "complete_with_failures",
        },
    )
    json_dump(
        output_dir / "scan_results.json",
        {
            "cases": cases,
            "cold_import_seconds": import_seconds,
            "decision": decision,
            "input_mapping": {
                "eta_fac": eta_fac,
                "linx_reference_Omegabh2": float(const.Omegabh2),
                "linx_reference_tau_n_seconds": float(const.tau_n),
                "tau_n_fac": tau_n_fac,
            },
            "jax_x64": bool(jax.config.x64_enabled),
            "load_provenance": load_provenance,
            "observation_sigmas": sigmas,
            "schema_version": 1,
        },
    )
    worker_hours = wall_seconds / 3600.0
    json_dump(
        output_dir / "resource_report.json",
        {
            "cpu_core_hours": cpu_seconds / 3600.0,
            "cpu_seconds": cpu_seconds,
            "estimated_cost_cny": worker_hours * args.hourly_price_cny,
            "failed_cases": failures,
            "gpu_hours": 0.0,
            "hourly_price_cny": args.hourly_price_cny,
            "max_rss_bytes": usage.ru_maxrss * 1024,
            "schema_version": 1,
            "wall_seconds": wall_seconds,
            "worker_hours": worker_hours,
        },
    )
    print(output_dir)
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
