#!/usr/bin/env python3
"""Run one frozen WHY-NOT baseline over the standard-BBN challenge grid."""

from __future__ import annotations

import argparse
import json
import math
import platform
import resource
import socket
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.why_not_benchmark import (  # noqa: E402
    append_jsonl,
    finite_abundances,
    git_revision,
    json_dump,
    linx_abundances,
    load_abcmb_linx,
    load_linx,
    load_primat,
    load_prymordial,
    load_yaml,
    prymordial_abundances,
    sha256,
    utc_now,
)


def expected_cases(cmb: dict[str, Any], neutron: dict[str, Any]) -> dict[str, dict[str, float]]:
    omega = cmb["main_stage"]
    scenarios = neutron["scenarios"]
    common = {"delta_neff": 0.0}
    return {
        "fiducial": {
            "omega_b_h2": float(omega["mean"]),
            "tau_n_seconds": float(scenarios["N0"]["mean"]),
            **common,
        },
        "omega_b_minus_2sigma": {
            "omega_b_h2": float(omega["mean"] - 2 * omega["sigma"]),
            "tau_n_seconds": float(scenarios["N0"]["mean"]),
            **common,
        },
        "omega_b_plus_2sigma": {
            "omega_b_h2": float(omega["mean"] + 2 * omega["sigma"]),
            "tau_n_seconds": float(scenarios["N0"]["mean"]),
            **common,
        },
        "tau_n_n0_minus_2sigma": {
            "omega_b_h2": float(omega["mean"]),
            "tau_n_seconds": float(scenarios["N0"]["mean"] - 2 * scenarios["N0"]["sigma"]),
            **common,
        },
        "tau_n_n0_plus_2sigma": {
            "omega_b_h2": float(omega["mean"]),
            "tau_n_seconds": float(scenarios["N0"]["mean"] + 2 * scenarios["N0"]["sigma"]),
            **common,
        },
        "tau_n_bottle_n1": {
            "omega_b_h2": float(omega["mean"]),
            "tau_n_seconds": float(scenarios["N1"]["mode"]),
            **common,
        },
        "tau_n_beam_n2": {
            "omega_b_h2": float(omega["mean"]),
            "tau_n_seconds": float(scenarios["N2"]["mean"]),
            **common,
        },
    }


def validate_cases(
    configured: list[dict[str, Any]], expected: dict[str, dict[str, float]]
) -> list[dict[str, Any]]:
    if [case["id"] for case in configured] != list(expected):
        raise ValueError("challenge case IDs or order differ from frozen source derivations")
    for case in configured:
        for key, value in expected[case["id"]].items():
            if not math.isclose(float(case[key]), value, rel_tol=0.0, abs_tol=1.0e-12):
                raise ValueError(f"{case['id']} {key} differs from frozen source derivation")
    return configured


def maximum_repeat_drift(outputs: list[dict[str, float]]) -> float:
    reference = outputs[0]
    return max(
        abs(float(output[key]) - float(reference[key]))
        for output in outputs[1:]
        for key in reference
    )


def build_solver(
    baseline: str,
    source_dir: Path,
    config: dict[str, Any],
) -> tuple[Callable[[dict[str, float]], dict[str, float]], dict[str, Any]]:
    if baseline in {"W0-LINX", "W3-ABCMB"}:
        modules, provenance = (
            load_abcmb_linx(source_dir) if baseline == "W3-ABCMB" else load_linx(source_dir)
        )
        jax = modules["jax"]
        jnp = modules["jnp"]
        const = modules["const"]
        background_model = modules["BackgroundModel"]()
        abundance_model = modules["AbundanceModel"](
            modules["NuclearRates"](nuclear_net="key_PRIMAT_2023")
        )
        numerics = config["linx_numerics"]
        abundance_numerics = numerics["abundance"]

        def solve(parameters: dict[str, float]) -> dict[str, float]:
            delta_neff = jnp.asarray(parameters["delta_neff"])
            if baseline == "W3-ABCMB":
                background_numerics = numerics["background"][baseline]
                raw_background = background_model(
                    delta_neff,
                    rtol=float(background_numerics["rtol"]),
                    atol=float(background_numerics["atol"]),
                    max_steps=int(background_numerics["max_steps"]),
                )
            else:
                raw_background = background_model(delta_neff)
            jax.block_until_ready(raw_background)
            t_vec, a_vec, rho_g, rho_nu, rho_np, pressure_np, neff_vec = raw_background
            raw = abundance_model(
                rho_g,
                rho_nu,
                rho_np,
                pressure_np,
                t_vec=t_vec,
                a_vec=a_vec,
                eta_fac=jnp.asarray(parameters["omega_b_h2"] / float(const.Omegabh2)),
                tau_n_fac=jnp.asarray(parameters["tau_n_seconds"] / float(const.tau_n)),
                rtol=float(abundance_numerics["rtol"]),
                atol=float(abundance_numerics["atol"]),
                sampling_nTOp=int(abundance_numerics["sampling_nTOp"]),
                max_steps=int(abundance_numerics["max_steps"]),
            )
            jax.block_until_ready(raw)
            values = linx_abundances(
                [float(value) for value in jax.device_get(raw)],
                float(jax.device_get(neff_vec[-1])),
            )
            return finite_abundances(values)

        return solve, provenance

    if baseline == "W1-PRYM":
        prym_config, solver_class, provenance = load_prymordial(source_dir)
        prym_config.aTid_flag = True
        prym_config.compute_bckg_flag = True
        prym_config.compute_nTOp_flag = True
        prym_config.compute_nTOp_thermal_flag = False
        prym_config.save_bckg_flag = False
        prym_config.save_nTOp_flag = False
        prym_config.save_nTOp_thermal_flag = False
        prym_config.smallnet_flag = True
        prym_config.nacreii_flag = False
        prym_config.rates_dir = "key_primat_rates/"
        prym_config.julia_flag = False
        prym_config.verbose_flag = False

        def solve(parameters: dict[str, float]) -> dict[str, float]:
            prym_config.Omegabh2 = parameters["omega_b_h2"]
            prym_config.eta0b = prym_config.Omegabh2_to_eta0b * prym_config.Omegabh2
            prym_config.DeltaNeff = parameters["delta_neff"]
            prym_config.tau_n = parameters["tau_n_seconds"] * prym_config.second
            return finite_abundances(prymordial_abundances(solver_class().PRyMresults().tolist()))

        return solve, provenance

    if baseline == "W2-PRIMAT":
        run_bbn, provenance = load_primat(source_dir)

        def solve(parameters: dict[str, float]) -> dict[str, float]:
            return finite_abundances(
                run_bbn(
                    {
                        "Omegabh2": parameters["omega_b_h2"],
                        "DeltaNeff": parameters["delta_neff"],
                        "tau_n": parameters["tau_n_seconds"],
                        "network": "small",
                    },
                    force_backend="c",
                    progress=False,
                )
            )

        return solve, provenance
    raise ValueError(f"unsupported baseline: {baseline}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--cmb-config", required=True, type=Path)
    parser.add_argument("--neutron-config", required=True, type=Path)
    parser.add_argument("--parameter-schema", required=True, type=Path)
    parser.add_argument("--observation-config", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--environment-lock", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--hourly-price-cny", required=True, type=float)
    parser.add_argument("--yaml-python", type=Path)
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config, config_loader = load_yaml(args.config, args.yaml_python)
    cmb, cmb_loader = load_yaml(args.cmb_config, args.yaml_python)
    neutron, neutron_loader = load_yaml(args.neutron_config, args.yaml_python)
    parameter_schema, schema_loader = load_yaml(args.parameter_schema, args.yaml_python)
    observation, observation_loader = load_yaml(args.observation_config, args.yaml_python)
    if config["status"] != "protocol_frozen_measurements_pending":
        raise ValueError("challenge protocol is not frozen")
    if parameter_schema["status"] != "standard_bbn_subset_frozen_extension_semantics_pending":
        raise ValueError("standard-BBN parameter subset is not frozen")
    if observation["decision_status"] != "frozen":
        raise ValueError("observation normalization is not frozen")
    if args.baseline not in config["baselines"]:
        raise ValueError(f"baseline is absent from frozen grid: {args.baseline}")
    cases = validate_cases(config["cases"], expected_cases(cmb, neutron))
    revision = git_revision(args.source_dir)
    if revision != config["baselines"][args.baseline]["source_revision"]:
        raise ValueError("source revision differs from frozen challenge grid")
    for path in (args.inventory, args.environment_lock):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.preflight:
        print(json.dumps({"baseline": args.baseline, "cases": len(cases), "ok": True}))
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=False)
    points_path = args.output_dir / "points.jsonl"
    failures_path = args.output_dir / "failures.jsonl"
    points_path.touch()
    failures_path.touch()
    started_at = utc_now()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    import_started = time.perf_counter()
    solve, load_provenance = build_solver(args.baseline, args.source_dir, config)
    import_seconds = time.perf_counter() - import_started
    repetitions = int(config["repetitions_per_point"])
    case_results: dict[str, Any] = {}
    failure_count = 0
    for case_number, case in enumerate(cases, start=1):
        parameters = {
            key: float(case[key]) for key in ("omega_b_h2", "tau_n_seconds", "delta_neff")
        }
        outputs: list[dict[str, float]] = []
        durations: list[float] = []
        for repetition in range(repetitions):
            started = time.perf_counter()
            try:
                result = solve(parameters)
                elapsed = time.perf_counter() - started
                outputs.append(result)
                durations.append(elapsed)
                append_jsonl(
                    points_path,
                    {
                        "case_id": case["id"],
                        "elapsed_seconds": elapsed,
                        "outputs": result,
                        "parameters": parameters,
                        "repetition": repetition,
                        "status": "ok",
                    },
                )
            except Exception as exc:  # pragma: no cover - worker failure boundary
                elapsed = time.perf_counter() - started
                failure_count += 1
                append_jsonl(
                    failures_path,
                    {
                        "case_id": case["id"],
                        "elapsed_seconds": elapsed,
                        "error": repr(exc),
                        "repetition": repetition,
                        "stage": "solve",
                        "traceback": traceback.format_exc(),
                    },
                )
        complete = len(outputs) == repetitions
        drift = maximum_repeat_drift(outputs) if len(outputs) > 1 else None
        case_results[case["id"]] = {
            "complete": complete,
            "maximum_absolute_repeat_drift": drift,
            "outputs": outputs[0] if outputs else None,
            "parameters": parameters,
            "repetitions_completed": len(outputs),
            "wall_seconds": sum(durations),
        }
        print(f"PROGRESS {case_number}/{len(cases)}", flush=True)

    acceptance = config["acceptance"]
    passed = (
        failure_count <= int(acceptance["maximum_structured_failures"])
        and all(result["complete"] for result in case_results.values())
        and all(
            result["maximum_absolute_repeat_drift"]
            <= float(acceptance["maximum_absolute_repeat_drift"])
            for result in case_results.values()
        )
    )
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    usage = resource.getrusage(resource.RUSAGE_SELF)
    json_dump(
        args.output_dir / "challenge_results.json",
        {
            "baseline": args.baseline,
            "cases": case_results,
            "decision": {
                "baseline_reliability_status": "accepted" if passed else "not_accepted",
                "cross_baseline_differences": "descriptive_only",
                "passed": passed,
            },
            "load_provenance": load_provenance,
            "schema_version": 1,
        },
    )
    json_dump(
        args.output_dir / "run_manifest.json",
        {
            "baseline": args.baseline,
            "cmb_config": str(args.cmb_config),
            "cmb_config_sha256": sha256(args.cmb_config),
            "config": str(args.config),
            "config_loader": config_loader,
            "config_sha256": sha256(args.config),
            "environment_lock": str(args.environment_lock),
            "environment_lock_sha256": sha256(args.environment_lock),
            "finished_at_utc": utc_now(),
            "hardware_inventory": str(args.inventory),
            "hardware_inventory_sha256": sha256(args.inventory),
            "hostname": socket.gethostname(),
            "metadata_loaders": {
                "cmb": cmb_loader,
                "neutron": neutron_loader,
                "observation": observation_loader,
                "parameter_schema": schema_loader,
            },
            "neutron_config": str(args.neutron_config),
            "neutron_config_sha256": sha256(args.neutron_config),
            "observation_config": str(args.observation_config),
            "observation_config_sha256": sha256(args.observation_config),
            "parameter_schema": str(args.parameter_schema),
            "parameter_schema_sha256": sha256(args.parameter_schema),
            "platform": platform.platform(),
            "precision": config["precision"],
            "python": sys.version,
            "run_id": str(uuid.uuid4()),
            "scientific_use": config["scientific_scope"],
            "source_dir": str(args.source_dir),
            "source_revision": revision,
            "started_at_utc": started_at,
            "status": "complete" if failure_count == 0 else "complete_with_failures",
        },
    )
    worker_hours = wall_seconds / 3600.0
    json_dump(
        args.output_dir / "resource_report.json",
        {
            "cpu_core_hours": cpu_seconds / 3600.0,
            "cpu_seconds": cpu_seconds,
            "estimated_cost_cny": worker_hours * args.hourly_price_cny,
            "failed_cases": failure_count,
            "gpu_hours": 0.0,
            "hourly_price_cny": args.hourly_price_cny,
            "import_seconds": import_seconds,
            "max_rss_bytes": usage.ru_maxrss * 1024,
            "schema_version": 1,
            "wall_seconds": wall_seconds,
            "worker_hours": worker_hours,
        },
    )
    print(args.output_dir)
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
