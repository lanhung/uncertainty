#!/usr/bin/env python3
"""Run the frozen W0 LINX standard-neighborhood gradient diagnostic."""

from __future__ import annotations

import argparse
import json
import math
import platform
import resource
import socket
import subprocess
import sys
import time
import traceback
import uuid
from itertools import product
from pathlib import Path
from typing import Any, Callable, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.why_not_benchmark import (  # noqa: E402
    append_jsonl,
    git_revision,
    json_dump,
    load_linx,
    load_yaml,
    sha256,
    utc_now,
)


DEFAULT_BENCHMARK = Path("configs/benchmarks/why_not_existing_solvers_v1.yaml")
DEFAULT_PARAMETER_SCHEMA = Path("configs/physics/parameter_schema.yaml")
DEFAULT_CMB_CONFIG = Path("configs/data/cmb_data_v1.yaml")
DEFAULT_NEUTRON_CONFIG = Path("configs/physics/neutron_lifetime_v1.yaml")
DEFAULT_OBSERVATION_CONFIG = Path("configs/data/abundance_OBS-v1.yaml")


def _number_token(value: float) -> str:
    sign = "m" if value < 0 else "p"
    magnitude = f"{abs(value):g}".replace(".", "p")
    return f"{sign}{magnitude}"


def expand_acceptance_points(
    scan: dict[str, Any],
    parameter_schema: dict[str, Any],
    cmb_config: dict[str, Any],
    neutron_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Expand the frozen axis and corner specification into 15 unique points."""
    fiducial = parameter_schema["standard_bbn_fiducial"]["values"]
    omega_center = float(cmb_config["main_stage"]["mean"])
    omega_scale = float(cmb_config["main_stage"]["sigma"])
    tau_center = float(neutron_config["scenarios"]["N0"]["mean"])
    tau_scale = float(neutron_config["scenarios"]["N0"]["sigma"])
    delta_scale = float(scan["coordinates"]["delta_neff"]["numerical_scale"])
    if not math.isclose(float(fiducial["omega_b_h2"]), omega_center):
        raise ValueError("parameter schema and CMB center differ")
    if not math.isclose(float(fiducial["tau_n_seconds"]), tau_center):
        raise ValueError("parameter schema and neutron-lifetime center differ")
    if not math.isclose(float(fiducial["delta_neff"]), 0.0):
        raise ValueError("gradient diagnostic requires the standard Delta Neff null")

    points: dict[tuple[float, float, float], dict[str, Any]] = {}

    def register(point_id: str, standardized: tuple[float, float, float]) -> None:
        delta_z, omega_z, tau_z = standardized
        key = (delta_z, omega_z, tau_z)
        physical = {
            "delta_neff": delta_z * delta_scale,
            "omega_b_h2": omega_center + omega_z * omega_scale,
            "tau_n_seconds": tau_center + tau_z * tau_scale,
        }
        candidate = {
            "point_id": point_id,
            "physical": physical,
            "standardized": {
                "delta_neff": delta_z,
                "omega_b_h2": omega_z,
                "tau_n_seconds": tau_z,
            },
        }
        previous = points.get(key)
        if previous is None or point_id == "fiducial":
            points[key] = candidate

    axes = scan["acceptance_points"]["axis_points"]
    axis_specs = (
        ("delta_neff", 0, axes["delta_neff_standardized"]),
        ("omega_b_h2", 1, axes["omega_b_h2_standardized"]),
        ("tau_n_seconds", 2, axes["tau_n_seconds_standardized"]),
    )
    for name, index, values in axis_specs:
        for raw_value in values:
            value = float(raw_value)
            standardized = [0.0, 0.0, 0.0]
            standardized[index] = value
            point_id = "fiducial" if value == 0.0 else f"axis_{name}_{_number_token(value)}"
            register(point_id, tuple(standardized))

    corners = scan["acceptance_points"]["neighborhood_corners"]
    for delta_z, omega_z, tau_z in product(
        corners["delta_neff_standardized"],
        corners["omega_b_h2_standardized"],
        corners["tau_n_seconds_standardized"],
    ):
        values = (float(delta_z), float(omega_z), float(tau_z))
        point_id = "corner_" + "_".join(_number_token(value) for value in values)
        register(point_id, values)

    return sorted(
        points.values(), key=lambda point: (point["point_id"] != "fiducial", point["point_id"])
    )


def scaled_difference(left: Any, right: Any) -> float:
    """Return max |left-right| / max(1, |right|) over an array-like value."""

    def flattened(value: Any) -> list[float]:
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, (list, tuple)):
            return [number for item in value for number in flattened(item)]
        return [float(value)]

    left_values = flattened(left)
    right_values = flattened(right)
    if len(left_values) != len(right_values):
        raise ValueError(f"size mismatch: {len(left_values)} != {len(right_values)}")
    if not all(math.isfinite(value) for value in left_values + right_values):
        return math.inf
    return max(
        (
            abs(left_value - right_value) / max(1.0, abs(right_value))
            for left_value, right_value in zip(left_values, right_values, strict=True)
        ),
        default=0.0,
    )


def five_point_central(
    function: Callable[[list[float]], Any],
    point: Sequence[float],
    coordinate: int,
    step: float,
) -> list[float]:
    """Evaluate the fourth-order five-point central finite difference."""
    if step <= 0:
        raise ValueError("finite-difference step must be positive")
    center = [float(value) for value in point]
    if coordinate < 0 or coordinate >= len(center):
        raise IndexError(coordinate)

    def shifted(multiplier: float) -> list[float]:
        values = center.copy()
        values[coordinate] += multiplier * step
        result = function(values)
        if hasattr(result, "tolist"):
            result = result.tolist()
        return [float(value) for value in result]

    minus_two = shifted(-2.0)
    minus_one = shifted(-1.0)
    plus_one = shifted(1.0)
    plus_two = shifted(2.0)
    lengths = {len(minus_two), len(minus_one), len(plus_one), len(plus_two)}
    if len(lengths) != 1:
        raise ValueError("finite-difference output sizes differ")
    return [
        (value_m2 - 8.0 * value_m1 + 8.0 * value_p1 - value_p2) / (12.0 * step)
        for value_m2, value_m1, value_p1, value_p2 in zip(
            minus_two, minus_one, plus_one, plus_two, strict=True
        )
    ]


def evaluate_decision(
    records: list[dict[str, Any]],
    acceptance: dict[str, Any],
    expected_records: int,
    structured_failures: int,
) -> dict[str, Any]:
    """Apply only the frozen numerical thresholds to acceptance-domain records."""
    finite_forward = sum(bool(record.get("forward_finite")) for record in records)
    finite_jacobian = sum(bool(record.get("jacobian_finite")) for record in records)
    silent_nonfinite_count = sum(int(record.get("silent_nonfinite_count", 0)) for record in records)
    denominator = expected_records or 1
    forward_fraction = finite_forward / denominator
    jacobian_fraction = finite_jacobian / denominator

    def maximum(field: str) -> float:
        values = [float(record[field]) for record in records if field in record]
        return max(values, default=math.inf)

    metrics = {
        "maximum_scaled_repeat_drift": maximum("scaled_repeat_drift"),
        "maximum_ad_mode_scaled_difference": maximum("ad_mode_scaled_difference"),
        "maximum_ad_fd_scaled_difference": maximum("ad_fd_scaled_difference"),
        "maximum_fd_plateau_scaled_difference": maximum("fd_plateau_scaled_difference"),
    }
    checks = {
        "all_records_present": len(records) == expected_records,
        "all_records_ok": all(record.get("status") == "ok" for record in records),
        "finite_forward_fraction": forward_fraction >= float(acceptance["finite_forward_fraction"]),
        "finite_jacobian_fraction": jacobian_fraction
        >= float(acceptance["finite_jacobian_fraction"]),
        "silent_nonfinite_count": silent_nonfinite_count
        <= int(acceptance["maximum_silent_nonfinite_count"]),
        "structured_failures": structured_failures
        <= int(acceptance["maximum_structured_failures"]),
        "repeat_drift": metrics["maximum_scaled_repeat_drift"]
        <= float(acceptance["maximum_scaled_repeat_drift"]),
        "ad_mode_difference": metrics["maximum_ad_mode_scaled_difference"]
        <= float(acceptance["maximum_ad_mode_scaled_difference"]),
        "ad_fd_difference": metrics["maximum_ad_fd_scaled_difference"]
        <= float(acceptance["maximum_ad_fd_scaled_difference"]),
        "fd_plateau_difference": metrics["maximum_fd_plateau_scaled_difference"]
        <= float(acceptance["maximum_fd_plateau_scaled_difference"]),
    }
    passed = all(checks.values())
    return {
        "acceptance_record_count": len(records),
        "checks": checks,
        "expected_acceptance_record_count": expected_records,
        "finite_forward_fraction": forward_fraction,
        "finite_jacobian_fraction": jacobian_fraction,
        **metrics,
        "numerical_gradient_status": "accepted" if passed else "not_accepted",
        "passed": passed,
        "scientific_scope": "standard_neighborhood_three_coordinate_gradient_candidate_only",
        "silent_nonfinite_count": silent_nonfinite_count,
        "structured_failure_count": structured_failures,
    }


def git_is_clean(source_dir: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(source_dir), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return not completed.stdout.strip()


def _device_array(value: Any, jax: Any) -> Any:
    import numpy as np

    jax.block_until_ready(value)
    return np.asarray(jax.device_get(value), dtype=float)


def _finite_or_raise(value: Any, label: str, jax: Any) -> Any:
    import numpy as np

    array = _device_array(value, jax)
    if not np.isfinite(array).all():
        indices = np.argwhere(~np.isfinite(array)).tolist()
        raise FloatingPointError(f"{label} contains non-finite entries at {indices}")
    return array


def _path_function(
    path: str,
    scan: dict[str, Any],
    modules: dict[str, Any],
    background_model: Any,
    abundance_model: Any,
    omega_center: float,
    omega_scale: float,
    tau_center: float,
    tau_scale: float,
    output_sigmas: dict[str, float],
) -> tuple[Callable[[Any], Any], list[int], list[str]]:
    jax = modules["jax"]
    jnp = modules["jnp"]
    const = modules["const"]
    delta_scale = float(scan["coordinates"]["delta_neff"]["numerical_scale"])
    numerics = scan["numerics"]["abundance"]
    rate_count = len(abundance_model.nuclear_net.reactions)
    zero_rates = jnp.zeros(rate_count, dtype=jnp.float64)

    def background(delta_z: Any) -> tuple[Any, ...]:
        return background_model(jnp.asarray(delta_z * delta_scale))

    def abundance(background_raw: tuple[Any, ...], omega_z: Any, tau_z: Any) -> Any:
        t_vec, a_vec, rho_g, rho_nu, rho_np, pressure_np, _ = background_raw
        eta_fac = (omega_center + omega_z * omega_scale) / float(const.Omegabh2)
        tau_fac = (tau_center + tau_z * tau_scale) / float(const.tau_n)
        raw = abundance_model(
            rho_g,
            rho_nu,
            rho_np,
            pressure_np,
            t_vec=t_vec,
            a_vec=a_vec,
            eta_fac=jnp.asarray(eta_fac),
            tau_n_fac=jnp.asarray(tau_fac),
            nuclear_rates_q=zero_rates,
            rtol=float(numerics["rtol"]),
            atol=float(numerics["atol"]),
            sampling_nTOp=int(numerics["sampling_nTOp"]),
            max_steps=int(numerics["max_steps"]),
        )
        yp = 4.0 * raw[5]
        doh = raw[2] / raw[1]
        return jnp.stack([yp / output_sigmas["YPBBN"], doh / output_sigmas["DoH"]])

    if path == "background_only_delta_neff":

        def function(values: Any) -> Any:
            t_vec, a_vec, _, _, _, _, neff_vec = background(values[0])
            return jnp.stack([neff_vec[-1], jnp.log(t_vec[-1]), jnp.log(a_vec[-1])])

        return function, [0], ["delta_neff"]

    if path == "frozen_background_abundance_eta_tau":

        def function(values: Any) -> Any:
            frozen_background = jax.tree_util.tree_map(jax.lax.stop_gradient, background(values[0]))
            return abundance(frozen_background, values[1], values[2])

        return function, [1, 2], ["omega_b_h2", "tau_n_seconds"]

    if path == "full_end_to_end_three_coordinate_jacobian":

        def function(values: Any) -> Any:
            return abundance(background(values[0]), values[1], values[2])

        return function, [0, 1, 2], ["delta_neff", "omega_b_h2", "tau_n_seconds"]

    raise ValueError(f"unsupported gradient path: {path}")


def _compile_ad_methods(
    function: Callable[[Any], Any], coordinate_indices: list[int], jax: Any, jnp: Any
) -> dict[str, Callable[[Any], Any]]:
    raw_jacrev = jax.jacrev(function)
    raw_jacfwd = jax.jacfwd(function)

    def selected_jacrev(values: Any) -> Any:
        return raw_jacrev(values)[:, coordinate_indices]

    def selected_jacfwd(values: Any) -> Any:
        return raw_jacfwd(values)[:, coordinate_indices]

    def jvp_basis(values: Any) -> Any:
        basis = jnp.eye(values.shape[0], dtype=values.dtype)
        columns = [jax.jvp(function, (values,), (basis[index],))[1] for index in coordinate_indices]
        return jnp.stack(columns, axis=1)

    return {
        "jacrev": jax.jit(selected_jacrev),
        "jacfwd": jax.jit(selected_jacfwd),
        "jvp_basis": jax.jit(jvp_basis),
    }


def _run_point(
    path: str,
    point: dict[str, Any],
    scan: dict[str, Any],
    modules: dict[str, Any],
    function: Callable[[Any], Any],
    coordinate_indices: list[int],
    coordinate_names: list[str],
    methods: dict[str, Callable[[Any], Any]],
    timings_path: Path,
) -> dict[str, Any]:
    import numpy as np

    jax = modules["jax"]
    jnp = modules["jnp"]
    standardized = point["standardized"]
    initial = np.asarray(
        [
            standardized["delta_neff"],
            standardized["omega_b_h2"],
            standardized["tau_n_seconds"],
        ],
        dtype=float,
    )
    initial_jax = jnp.asarray(initial, dtype=jnp.float64)
    forward = _finite_or_raise(function(initial_jax), "forward", jax)
    jacobians: dict[str, np.ndarray] = {}
    method_timings: dict[str, float] = {}
    for method_name in scan["ad_methods"]:
        started = time.perf_counter()
        jacobians[method_name] = _finite_or_raise(
            methods[method_name](initial_jax), f"{method_name} Jacobian", jax
        )
        elapsed = time.perf_counter() - started
        method_timings[method_name] = elapsed
        append_jsonl(
            timings_path,
            {
                "elapsed_seconds": elapsed,
                "kind": "ad_compile_or_call",
                "method": method_name,
                "path": path,
                "point_id": point["point_id"],
                "status": "ok",
            },
        )

    repeat_jacobians: list[np.ndarray] = []
    repeat_timings: list[float] = []
    for repetition in range(int(scan["numerics"]["repeats"])):
        started = time.perf_counter()
        repeated = _finite_or_raise(methods["jacrev"](initial_jax), "repeated jacrev Jacobian", jax)
        repeat_timings.append(time.perf_counter() - started)
        repeat_jacobians.append(repeated)
    repeat_drift = max(
        (scaled_difference(value, jacobians["jacrev"]) for value in repeat_jacobians), default=0.0
    )

    def host_function(values: list[float]) -> list[float]:
        return _finite_or_raise(
            function(jnp.asarray(values, dtype=jnp.float64)), "FD forward", jax
        ).tolist()

    fd_by_step: dict[str, np.ndarray] = {}
    fd_timings: dict[str, float] = {}
    for raw_step in scan["finite_difference"]["standardized_steps"]:
        step = float(raw_step)
        started = time.perf_counter()
        columns = [
            five_point_central(host_function, initial, coordinate, step)
            for coordinate in coordinate_indices
        ]
        fd_by_step[f"{step:g}"] = np.stack(columns, axis=1)
        fd_timings[f"{step:g}"] = time.perf_counter() - started
        append_jsonl(
            timings_path,
            {
                "elapsed_seconds": fd_timings[f"{step:g}"],
                "kind": "five_point_finite_difference",
                "path": path,
                "point_id": point["point_id"],
                "status": "ok",
                "step": step,
            },
        )

    ordered_steps = [float(value) for value in scan["finite_difference"]["standardized_steps"]]
    fd_plateau = max(
        scaled_difference(fd_by_step[f"{right:g}"], fd_by_step[f"{left:g}"])
        for left, right in zip(ordered_steps, ordered_steps[1:])
    )
    finest = fd_by_step[f"{ordered_steps[-1]:g}"]
    ad_mode_difference = max(
        scaled_difference(jacobians[method], jacobians["jacrev"])
        for method in ("jacfwd", "jvp_basis")
    )
    return {
        "ad_fd_scaled_difference": scaled_difference(jacobians["jacrev"], finest),
        "ad_mode_scaled_difference": ad_mode_difference,
        "coordinate_names": coordinate_names,
        "fd_jacobians": {key: value.tolist() for key, value in fd_by_step.items()},
        "fd_plateau_scaled_difference": fd_plateau,
        "forward": forward.tolist(),
        "forward_finite": True,
        "jacobian_finite": True,
        "jacobians": {key: value.tolist() for key, value in jacobians.items()},
        "path": path,
        "point_id": point["point_id"],
        "scaled_repeat_drift": repeat_drift,
        "silent_nonfinite_count": 0,
        "standardized_coordinates": initial.tolist(),
        "status": "ok",
        "timings_seconds": {
            "ad_methods": method_timings,
            "finite_difference": fd_timings,
            "jacrev_repeats": repeat_timings,
        },
    }


def _run_upstream_challenge(
    scan: dict[str, Any],
    modules: dict[str, Any],
    background_model: Any,
    abundance_model: Any,
    standard_eta_fac: float,
    standard_tau_fac: float,
) -> dict[str, Any]:
    import numpy as np

    jax = modules["jax"]
    jnp = modules["jnp"]
    if len(abundance_model.nuclear_net.reactions) != 12:
        raise ValueError("historical 15-vector challenge requires exactly 12 registered reactions")

    def objective(parameters: Any) -> Any:
        delta_neff, eta_fac, tau_fac = parameters[:3]
        t_vec, a_vec, rho_g, rho_nu, rho_np, _, _ = background_model(delta_neff)
        raw = abundance_model(
            rho_g,
            rho_nu,
            rho_np,
            rho_np / 3.0,
            t_vec=t_vec,
            a_vec=a_vec,
            eta_fac=eta_fac,
            tau_n_fac=tau_fac,
            nuclear_rates_q=parameters[3:],
        )
        yp = raw[5] * 4.0
        doh = raw[2] / raw[1]
        return ((yp - 0.245) / 0.003) ** 2 + ((doh - 2.547e-5) / 2.5e-7) ** 2

    standard = np.asarray([0.0, standard_eta_fac, standard_tau_fac] + [0.0] * 12, dtype=float)
    vectors = {
        "two_times_ones_15": np.full(15, 2.0),
        "delta_neff_2_only": standard.copy(),
        "eta_fac_2_only": standard.copy(),
        "tau_n_fac_2_only": standard.copy(),
        "all_rates_q_2_only": standard.copy(),
        "all_2_except_delta_neff_0": np.full(15, 2.0),
    }
    vectors["delta_neff_2_only"][0] = 2.0
    vectors["eta_fac_2_only"][1] = 2.0
    vectors["tau_n_fac_2_only"][2] = 2.0
    vectors["all_rates_q_2_only"][3:] = 2.0
    vectors["all_2_except_delta_neff_0"][0] = 0.0
    value_and_grad = jax.jit(jax.value_and_grad(objective))
    cases: dict[str, Any] = {}
    for case_id, vector in vectors.items():
        started = time.perf_counter()
        value, gradient = value_and_grad(jnp.asarray(vector, dtype=jnp.float64))
        jax.block_until_ready((value, gradient))
        value_host = float(jax.device_get(value))
        gradient_host = np.asarray(jax.device_get(gradient), dtype=float)
        cases[case_id] = {
            "elapsed_seconds": time.perf_counter() - started,
            "finite_gradient_fraction": float(np.isfinite(gradient_host).mean()),
            "gradient": gradient_host.tolist(),
            "nonfinite_gradient_indices": np.argwhere(~np.isfinite(gradient_host))
            .flatten()
            .tolist(),
            "objective": value_host,
            "status": "finite"
            if np.isfinite(value_host) and np.isfinite(gradient_host).all()
            else "nonfinite",
        }
    return {
        "affects_acceptance_domain": bool(
            scan["diagnostic_only_upstream_challenge"]["affects_acceptance_domain"]
        ),
        "cases": cases,
        "historical_likelihood_only": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--benchmark-config", default=DEFAULT_BENCHMARK, type=Path)
    parser.add_argument("--parameter-schema", default=DEFAULT_PARAMETER_SCHEMA, type=Path)
    parser.add_argument("--cmb-config", default=DEFAULT_CMB_CONFIG, type=Path)
    parser.add_argument("--neutron-config", default=DEFAULT_NEUTRON_CONFIG, type=Path)
    parser.add_argument("--observation-config", default=DEFAULT_OBSERVATION_CONFIG, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--environment-lock", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--hourly-price-cny", type=float)
    parser.add_argument("--yaml-python", type=Path)
    return parser.parse_args()


def _preflight(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = {
        "scan": args.config,
        "benchmark": args.benchmark_config,
        "parameter_schema": args.parameter_schema,
        "cmb": args.cmb_config,
        "neutron": args.neutron_config,
        "observation": args.observation_config,
    }
    loaded: dict[str, Any] = {}
    loaders: dict[str, str] = {}
    for name, path in paths.items():
        loaded[name], loaders[name] = load_yaml(path, args.yaml_python)
    scan = loaded["scan"]
    if scan["status"] != "protocol_frozen_measurements_pending":
        raise ValueError("LINX gradient protocol is not frozen")
    if scan["source_revision"] != loaded["benchmark"]["baselines"]["W0-LINX"]["revision"]:
        raise ValueError("gradient protocol and W0 source registration differ")
    if scan["precision"] != "float64" or scan["nuclear_rates_q"] != "all_zero":
        raise ValueError("gradient protocol precision or rate boundary changed")
    if scan["finite_difference"]["method"] != "five_point_central":
        raise ValueError("unsupported finite-difference method")
    if scan["ad_methods"] != ["jacrev", "jacfwd", "jvp_basis"]:
        raise ValueError("gradient AD method contract changed")
    expected_paths = {
        "background_only_delta_neff",
        "frozen_background_abundance_eta_tau",
        "full_end_to_end_three_coordinate_jacobian",
    }
    if set(scan["paths"]) != expected_paths:
        raise ValueError("gradient path contract changed")
    if loaded["observation"]["decision_status"] != "frozen":
        raise ValueError("observation normalization is not frozen")
    if loaded["neutron"]["decision_status"] != "frozen":
        raise ValueError("neutron-lifetime input is not frozen")
    if not args.inventory.is_file() or not args.environment_lock.is_file():
        raise FileNotFoundError("inventory or environment lock is absent")
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    if not isinstance(inventory.get("node_name"), str) or not inventory["node_name"]:
        raise ValueError("hardware inventory lacks a non-empty node_name")
    expected_lock = (REPOSITORY_ROOT / scan["environment_lock"]).resolve()
    if args.environment_lock.resolve() != expected_lock:
        raise ValueError(f"environment lock {args.environment_lock} != frozen {expected_lock}")
    expected_observation = (REPOSITORY_ROOT / scan["output_normalization"]).resolve()
    if args.observation_config.resolve() != expected_observation:
        raise ValueError(
            f"observation config {args.observation_config} != frozen {expected_observation}"
        )
    revision = git_revision(args.source_dir)
    if revision != scan["source_revision"]:
        raise ValueError(f"source revision {revision} != frozen {scan['source_revision']}")
    if not git_is_clean(args.source_dir):
        raise ValueError("frozen LINX source checkout is dirty")
    loaded["revision"] = revision
    loaded["loaders"] = loaders
    return loaded, paths


def main() -> int:
    args = parse_args()
    loaded, input_paths = _preflight(args)
    scan = loaded["scan"]
    points = expand_acceptance_points(
        scan, loaded["parameter_schema"], loaded["cmb"], loaded["neutron"]
    )
    if args.preflight:
        report = {
            "acceptance_point_count": len(points),
            "input_sha256": {name: sha256(path) for name, path in input_paths.items()},
            "environment_lock_sha256": sha256(args.environment_lock),
            "hardware_inventory_sha256": sha256(args.inventory),
            "scan_id": scan["scan_id"],
            "source_git_clean": True,
            "source_revision": loaded["revision"],
            "status": "ok",
        }
        print(json.dumps(report, sort_keys=True))
        return 0
    if args.output_dir is None or args.hourly_price_cny is None:
        raise ValueError("measurement mode requires --output-dir and --hourly-price-cny")
    if args.hourly_price_cny < 0:
        raise ValueError("hourly price cannot be negative")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=False)
    timings_path = output_dir / "timings.jsonl"
    failures_path = output_dir / "failures.jsonl"
    timings_path.touch()
    failures_path.touch()

    import_started = time.perf_counter()
    modules, load_provenance = load_linx(args.source_dir)
    import_seconds = time.perf_counter() - import_started
    jax = modules["jax"]
    if not bool(jax.config.x64_enabled):
        raise RuntimeError("LINX gradient diagnostic requires JAX x64 mode")
    background_model = modules["BackgroundModel"]()
    abundance_model = modules["AbundanceModel"](
        modules["NuclearRates"](nuclear_net=scan["network"])
    )
    cmb = loaded["cmb"]["main_stage"]
    neutron = loaded["neutron"]["scenarios"]["N0"]
    observation = loaded["observation"]["main_likelihood"]
    omega_center = float(cmb["mean"])
    omega_scale = float(cmb["sigma"])
    tau_center = float(neutron["mean"])
    tau_scale = float(neutron["sigma"])
    output_sigmas = {
        "YPBBN": float(observation["helium4_mass_fraction"]["sigma"]),
        "DoH": float(observation["deuterium_number_ratio"]["sigma"]) * 1.0e-5,
    }

    started_at = utc_now()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    acceptance_records: list[dict[str, Any]] = []
    acceptance_failures = 0
    group_results: dict[str, Any] = {}
    for group_number, path in enumerate(scan["paths"], start=1):
        function, coordinate_indices, coordinate_names = _path_function(
            path,
            scan,
            modules,
            background_model,
            abundance_model,
            omega_center,
            omega_scale,
            tau_center,
            tau_scale,
            output_sigmas,
        )
        methods = _compile_ad_methods(function, coordinate_indices, jax, modules["jnp"])
        path_records: list[dict[str, Any]] = []
        for point in points:
            try:
                record = _run_point(
                    path,
                    point,
                    scan,
                    modules,
                    function,
                    coordinate_indices,
                    coordinate_names,
                    methods,
                    timings_path,
                )
            except Exception as exc:  # pragma: no cover - worker failure boundary
                acceptance_failures += 1
                record = {
                    "error": repr(exc),
                    "forward_finite": False,
                    "jacobian_finite": False,
                    "path": path,
                    "point_id": point["point_id"],
                    "silent_nonfinite_count": 0,
                    "status": "failed",
                }
                append_jsonl(
                    failures_path,
                    {
                        "acceptance_domain": True,
                        "error": repr(exc),
                        "kind": "gradient_path_failure",
                        "path": path,
                        "point_id": point["point_id"],
                        "traceback": traceback.format_exc(),
                    },
                )
            path_records.append(record)
            acceptance_records.append(record)
        group_results[path] = path_records
        print(f"PROGRESS {group_number}/4", flush=True)

    try:
        const = modules["const"]
        diagnostic = _run_upstream_challenge(
            scan,
            modules,
            background_model,
            abundance_model,
            omega_center / float(const.Omegabh2),
            tau_center / float(const.tau_n),
        )
    except Exception as exc:  # pragma: no cover - diagnostic-only worker boundary
        diagnostic = {"affects_acceptance_domain": False, "error": repr(exc), "status": "failed"}
        append_jsonl(
            failures_path,
            {
                "acceptance_domain": False,
                "error": repr(exc),
                "kind": "upstream_challenge_failure",
                "traceback": traceback.format_exc(),
            },
        )
    print("PROGRESS 4/4", flush=True)

    expected_records = len(points) * len(scan["paths"])
    decision = evaluate_decision(
        acceptance_records, scan["acceptance"], expected_records, acceptance_failures
    )
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    finished_at = utc_now()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    worker_hours = wall_seconds / 3600.0
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    run_status = "complete" if acceptance_failures == 0 else "complete_with_failures"
    run_id = str(uuid.uuid4())
    manifest_names = {
        "scan": "scan_config",
        "benchmark": "benchmark_config",
        "parameter_schema": "parameter_schema",
        "cmb": "cmb_config",
        "neutron": "neutron_config",
        "observation": "observation_config",
    }
    manifest_paths = {manifest_names[name]: str(path) for name, path in input_paths.items()}
    hashes = {f"{manifest_names[name]}_sha256": sha256(path) for name, path in input_paths.items()}

    json_dump(
        output_dir / "run_manifest.json",
        {
            **manifest_paths,
            **hashes,
            "environment_lock": str(args.environment_lock),
            "environment_lock_sha256": sha256(args.environment_lock),
            "finished_at_utc": finished_at,
            "hardware_inventory": str(args.inventory),
            "hardware_inventory_sha256": sha256(args.inventory),
            "hostname": socket.gethostname(),
            "metadata_loaders": loaded["loaders"],
            "node_name": inventory["node_name"],
            "platform": platform.platform(),
            "precision": "float64",
            "python": sys.version,
            "run_id": run_id,
            "scan_id": scan["scan_id"],
            "schema_version": 1,
            "scientific_use": "standard_neighborhood_three_coordinate_gradient_diagnostic_only",
            "source_dir": str(args.source_dir),
            "source_git_clean": True,
            "source_revision": loaded["revision"],
            "started_at_utc": started_at,
            "status": run_status,
        },
    )
    json_dump(
        output_dir / "scan_results.json",
        {
            "acceptance_points": points,
            "cold_import_seconds": import_seconds,
            "decision": decision,
            "diagnostic_only_upstream_challenge": diagnostic,
            "jax_x64": bool(jax.config.x64_enabled),
            "load_provenance": load_provenance,
            "observation_sigmas": output_sigmas,
            "path_results": group_results,
            "schema_version": 1,
        },
    )
    json_dump(
        output_dir / "resource_report.json",
        {
            "acceptance_failures": acceptance_failures,
            "cpu_core_hours": cpu_seconds / 3600.0,
            "cpu_seconds": cpu_seconds,
            "estimated_cost_cny": worker_hours * args.hourly_price_cny,
            "gpu_hours": 0.0,
            "hourly_price_cny": args.hourly_price_cny,
            "max_rss_bytes": usage.ru_maxrss * 1024,
            "schema_version": 1,
            "wall_seconds": wall_seconds,
            "worker_hours": worker_hours,
        },
    )
    print(output_dir)
    return 0 if acceptance_failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
