#!/usr/bin/env python3
"""Run a registered direct-solver runtime slice with auditable artifacts.

Adapters are implemented only for explicitly validated frozen sources.
Unsupported baselines fail rather than being redirected to a different solver.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse


def load_yaml(path: Path, yaml_python: Path | None) -> tuple[dict[str, Any], str]:
    try:
        import yaml
    except ModuleNotFoundError:
        if yaml_python is None:
            raise RuntimeError(
                "PyYAML is absent from the exact solver environment; provide --yaml-python"
            ) from None
        helper = (
            "import json,sys,yaml; "
            "print(json.dumps(yaml.safe_load(open(sys.argv[1], encoding='utf-8'))))"
        )
        completed = subprocess.run(
            [str(yaml_python), "-c", helper, str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(completed.stdout), f"isolated_subprocess:{yaml_python}"
    return yaml.safe_load(path.read_text(encoding="utf-8")), "in_process_pyyaml"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values: list[float], probability: float) -> float:
    """Return the linearly interpolated quantile of non-empty values."""
    if not values:
        raise ValueError("quantile requires at least one value")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "median": quantile(values, 0.5),
        "q1": quantile(values, 0.25),
        "q3": quantile(values, 0.75),
        "p95": quantile(values, 0.95),
        "minimum": min(values),
        "maximum": max(values),
    }


def git_revision(source_dir: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip()


def json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def finite_abundances(result: dict[str, Any]) -> dict[str, float]:
    keys = ("Neff", "YPBBN", "YPCMB", "DoH", "He3oH", "Li7oH")
    values: dict[str, float] = {}
    for key in keys:
        value = float(result[key])
        if not math.isfinite(value):
            raise FloatingPointError(f"non-finite PRIMAT result: {key}={value}")
        values[key] = value
    return values


def linx_abundances(raw: list[float], neff: float) -> dict[str, float]:
    if len(raw) != 8:
        raise ValueError(f"expected 8 LINX species, received {len(raw)}")
    values = {
        "Neff": neff,
        "YPBBN": 4.0 * raw[5],
        "DoH": raw[2] / raw[1],
        "He3oH": (raw[3] + raw[4]) / raw[1],
        "Li7oH": (raw[6] + raw[7]) / raw[1],
    }
    for key, value in values.items():
        if not math.isfinite(value):
            raise FloatingPointError(f"non-finite LINX result: {key}={value}")
    return values


def load_linx(source_dir: Path) -> tuple[dict[str, Any], dict[str, str]]:
    sys.path.insert(0, str(source_dir))
    import jax  # type: ignore
    import linx  # type: ignore
    from jax import numpy as jnp  # type: ignore
    from linx import const  # type: ignore
    from linx.abundances import AbundanceModel  # type: ignore
    from linx.background import BackgroundModel  # type: ignore
    from linx.nuclear import NuclearRates  # type: ignore

    loaded_from = Path(linx.__file__).resolve()
    source_root = source_dir.resolve()
    if source_root not in loaded_from.parents:
        raise RuntimeError(f"LINX loaded from {loaded_from}, not frozen source {source_root}")
    if not bool(jax.config.x64_enabled):
        raise RuntimeError("LINX benchmark requires JAX x64 mode")
    modules = {
        "AbundanceModel": AbundanceModel,
        "BackgroundModel": BackgroundModel,
        "NuclearRates": NuclearRates,
        "const": const,
        "jax": jax,
        "jnp": jnp,
    }
    provenance = {
        "jax": jax.__version__,
        "package": str(loaded_from),
    }
    return modules, provenance


def run_w0_linx(
    source_dir: Path,
    parameters: dict[str, float],
    repetitions: int,
    batch_sizes: list[int],
    timings_path: Path,
    failures_path: Path,
) -> tuple[dict[str, Any], int, float]:
    import numpy as np

    import_started = time.perf_counter()
    modules, load_provenance = load_linx(source_dir)
    jax = modules["jax"]
    jnp = modules["jnp"]
    const = modules["const"]
    import_seconds = time.perf_counter() - import_started
    append_jsonl(
        timings_path,
        {
            "batch_size": 0,
            "elapsed_seconds": import_seconds,
            "kind": "cold_import",
            "recorded_at_utc": utc_now(),
        },
    )

    background = modules["BackgroundModel"]()
    background_raw = background(jnp.asarray(parameters["delta_neff"]))
    jax.block_until_ready(background_raw)
    t_vec, a_vec, rho_g, rho_nu, rho_np, pressure_np, neff_vec = background_raw
    abundance_model = modules["AbundanceModel"](
        modules["NuclearRates"](nuclear_net="key_PRIMAT_2023")
    )
    eta_fac = parameters["omega_b_h2"] / float(const.Omegabh2)
    tau_n_fac = parameters["tau_n_seconds"] / float(const.tau_n)

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
            rtol=1.0e-6,
            sampling_nTOp=150,
        )

    def extract_scalar(raw: Any) -> dict[str, float]:
        return linx_abundances(
            [float(value) for value in jax.device_get(raw)],
            float(jax.device_get(neff_vec[-1])),
        )

    cold_started = time.perf_counter()
    reference_raw = solve_raw(eta_fac, tau_n_fac)
    jax.block_until_ready(reference_raw)
    reference = extract_scalar(reference_raw)
    cold_seconds = time.perf_counter() - cold_started
    append_jsonl(
        timings_path,
        {
            "batch_size": 1,
            "elapsed_seconds": cold_seconds,
            "kind": "cold_solve",
            "recorded_at_utc": utc_now(),
            "status": "ok",
        },
    )

    failures = 0
    scalar_durations: list[float] = []
    maximum_absolute_repeat_drift = 0.0
    maximum_absolute_repeat_drift_by_abundance = {key: 0.0 for key in reference}
    batch_reference: dict[str, float] | None = None
    scalar_repetitions = repetitions if 1 in batch_sizes else 0
    for repetition in range(scalar_repetitions):
        started = time.perf_counter()
        successful_points = 0
        try:
            raw = solve_raw(eta_fac, tau_n_fac)
            jax.block_until_ready(raw)
            values = extract_scalar(raw)
            maximum_absolute_repeat_drift = max(
                maximum_absolute_repeat_drift,
                *(abs(values[key] - reference[key]) for key in reference),
            )
            for key in reference:
                maximum_absolute_repeat_drift_by_abundance[key] = max(
                    maximum_absolute_repeat_drift_by_abundance[key],
                    abs(values[key] - reference[key]),
                )
            successful_points = 1
        except Exception as exc:  # pragma: no cover - exercised on worker failures
            failures += 1
            append_jsonl(
                failures_path,
                {
                    "batch_size": 1,
                    "error": repr(exc),
                    "kind": "solver_exception",
                    "repetition": repetition,
                    "traceback": traceback.format_exc(),
                },
            )
        elapsed = time.perf_counter() - started
        scalar_durations.append(elapsed)
        append_jsonl(
            timings_path,
            {
                "batch_size": 1,
                "elapsed_seconds": elapsed,
                "execution_mode": "compiled_scalar_call",
                "kind": "warm_batch",
                "per_point_seconds": elapsed,
                "repetition": repetition,
                "status": "ok" if successful_points == 1 else "failed",
                "successful_points": successful_points,
            },
        )

    native_batch_size = next((value for value in batch_sizes if value != 1), None)
    batch_durations: list[float] = []
    batch_compile_seconds = 0.0
    if native_batch_size is not None:
        batched_solve = jax.jit(jax.vmap(solve_raw, in_axes=(0, 0)))
        eta_values = jnp.full((native_batch_size,), eta_fac, dtype=jnp.float64)
        tau_values = jnp.full((native_batch_size,), tau_n_fac, dtype=jnp.float64)
        compile_started = time.perf_counter()
        compiled_raw = batched_solve(eta_values, tau_values)
        jax.block_until_ready(compiled_raw)
        batch_compile_seconds = time.perf_counter() - compile_started
        append_jsonl(
            timings_path,
            {
                "batch_size": native_batch_size,
                "elapsed_seconds": batch_compile_seconds,
                "kind": "cold_batch_compile_and_solve",
                "recorded_at_utc": utc_now(),
                "status": "ok",
            },
        )
        for repetition in range(repetitions):
            started = time.perf_counter()
            successful_points = 0
            try:
                raw = batched_solve(eta_values, tau_values)
                jax.block_until_ready(raw)
                matrix = np.asarray(jax.device_get(raw))
                if matrix.shape[-1] != 8 and matrix.shape[0] == 8:
                    matrix = np.moveaxis(matrix, 0, -1)
                if matrix.shape[-1] != 8:
                    raise ValueError(f"unexpected LINX batch species axis: {matrix.shape}")
                matrix = matrix.reshape((-1, 8))
                if matrix.shape[0] != native_batch_size:
                    raise ValueError(
                        f"unexpected LINX batch size: {matrix.shape[0]} != {native_batch_size}"
                    )
                for row in matrix:
                    values = linx_abundances(row.tolist(), reference["Neff"])
                    if batch_reference is None:
                        batch_reference = values
                    maximum_absolute_repeat_drift = max(
                        maximum_absolute_repeat_drift,
                        *(abs(values[key] - reference[key]) for key in reference),
                    )
                    for key in reference:
                        maximum_absolute_repeat_drift_by_abundance[key] = max(
                            maximum_absolute_repeat_drift_by_abundance[key],
                            abs(values[key] - reference[key]),
                        )
                successful_points = native_batch_size
            except Exception as exc:  # pragma: no cover - exercised on worker failures
                failures += 1
                append_jsonl(
                    failures_path,
                    {
                        "batch_size": native_batch_size,
                        "error": repr(exc),
                        "kind": "solver_exception",
                        "repetition": repetition,
                        "traceback": traceback.format_exc(),
                    },
                )
            elapsed = time.perf_counter() - started
            batch_durations.append(elapsed)
            append_jsonl(
                timings_path,
                {
                    "batch_size": native_batch_size,
                    "elapsed_seconds": elapsed,
                    "execution_mode": "jax_jit_vmap_native_batch",
                    "kind": "warm_batch",
                    "per_point_seconds": elapsed / native_batch_size,
                    "repetition": repetition,
                    "status": "ok" if successful_points == native_batch_size else "failed",
                    "successful_points": successful_points,
                },
            )

    timings = {"warm_batch_1": summarize(scalar_durations)}
    if native_batch_size is not None:
        timings[f"warm_batch_{native_batch_size}"] = summarize(batch_durations)
    summary = {
        "abundances": reference,
        "batch_reference_abundances": batch_reference,
        "batch_compile_and_first_solve_seconds": batch_compile_seconds,
        "cold_import_seconds": import_seconds,
        "cold_solve_seconds": cold_seconds,
        "input_mapping": {
            "eta_fac": eta_fac,
            "linx_reference_Omegabh2": float(const.Omegabh2),
            "linx_reference_tau_n_seconds": float(const.tau_n),
            "tau_n_fac": tau_n_fac,
        },
        "jax_x64": bool(jax.config.x64_enabled),
        "load_provenance": load_provenance,
        "maximum_absolute_repeat_drift": maximum_absolute_repeat_drift,
        "maximum_absolute_repeat_drift_by_abundance": (maximum_absolute_repeat_drift_by_abundance),
        "network": "key_PRIMAT_2023",
        "numerical_consistency_status": (
            "exact_repeat" if maximum_absolute_repeat_drift == 0.0 else "batch_discrepancy_open"
        ),
        "timings_seconds": timings,
    }
    measured_seconds = (
        import_seconds
        + cold_seconds
        + batch_compile_seconds
        + sum(scalar_durations)
        + sum(batch_durations)
    )
    return summary, failures, measured_seconds


def load_primat(source_dir: Path) -> tuple[Callable[..., dict[str, Any]], dict[str, str]]:
    import primat  # type: ignore
    from primat.backend import run_bbn  # type: ignore

    loaded_from = Path(primat.__file__).resolve()
    source_root = source_dir.resolve()
    direct_url_text = importlib.metadata.distribution("primat").read_text("direct_url.json")
    if direct_url_text is None:
        raise RuntimeError("installed PRIMAT lacks direct_url.json source provenance")
    direct_url = json.loads(direct_url_text)["url"]
    parsed = urlparse(direct_url)
    installed_source = Path(unquote(parsed.path)).resolve()
    if parsed.scheme != "file" or installed_source != source_root:
        raise RuntimeError(
            f"installed PRIMAT provenance {direct_url} does not match frozen source {source_root}"
        )
    extension = importlib.util.find_spec("primat._primat_c")
    if extension is None or extension.origin is None:
        raise RuntimeError("installed frozen PRIMAT has no compiled C extension")
    return run_bbn, {
        "compiled_extension": str(Path(extension.origin).resolve()),
        "direct_url": direct_url,
        "package": str(loaded_from),
    }


def run_w2_primat(
    source_dir: Path,
    parameters: dict[str, float],
    repetitions: int,
    batch_sizes: list[int],
    timings_path: Path,
    failures_path: Path,
) -> tuple[dict[str, Any], int, float]:
    import_started = time.perf_counter()
    run_bbn, load_provenance = load_primat(source_dir)
    import_seconds = time.perf_counter() - import_started
    append_jsonl(
        timings_path,
        {
            "batch_size": 0,
            "elapsed_seconds": import_seconds,
            "kind": "cold_import",
            "recorded_at_utc": utc_now(),
        },
    )

    solver_parameters: dict[str, Any] = {
        "Omegabh2": parameters["omega_b_h2"],
        "DeltaNeff": parameters["delta_neff"],
        "tau_n": parameters["tau_n_seconds"],
        "network": "small",
    }

    def solve() -> dict[str, float]:
        result = run_bbn(solver_parameters, force_backend="c", progress=False)
        return finite_abundances(result)

    cold_started = time.perf_counter()
    reference = solve()
    cold_seconds = time.perf_counter() - cold_started
    append_jsonl(
        timings_path,
        {
            "batch_size": 1,
            "elapsed_seconds": cold_seconds,
            "kind": "cold_solve",
            "recorded_at_utc": utc_now(),
            "status": "ok",
        },
    )

    failures = 0
    durations: dict[str, list[float]] = {}
    maximum_absolute_repeat_drift = 0.0
    for batch_size in batch_sizes:
        label = f"warm_batch_{batch_size}"
        durations[label] = []
        for repetition in range(repetitions):
            started = time.perf_counter()
            successful_points = 0
            try:
                for _ in range(batch_size):
                    values = solve()
                    maximum_absolute_repeat_drift = max(
                        maximum_absolute_repeat_drift,
                        *(abs(values[key] - reference[key]) for key in reference),
                    )
                    successful_points += 1
            except Exception as exc:  # pragma: no cover - exercised on worker failures
                failures += 1
                append_jsonl(
                    failures_path,
                    {
                        "batch_size": batch_size,
                        "error": repr(exc),
                        "kind": "solver_exception",
                        "repetition": repetition,
                        "traceback": traceback.format_exc(),
                    },
                )
            elapsed = time.perf_counter() - started
            durations[label].append(elapsed)
            append_jsonl(
                timings_path,
                {
                    "batch_size": batch_size,
                    "elapsed_seconds": elapsed,
                    "execution_mode": "sequential_calls_no_native_batch_api",
                    "kind": "warm_batch",
                    "per_point_seconds": elapsed / batch_size,
                    "repetition": repetition,
                    "status": "ok" if successful_points == batch_size else "failed",
                    "successful_points": successful_points,
                },
            )

    summary = {
        "abundances": reference,
        "backend": "c",
        "cold_import_seconds": import_seconds,
        "cold_solve_seconds": cold_seconds,
        "load_provenance": load_provenance,
        "maximum_absolute_repeat_drift": maximum_absolute_repeat_drift,
        "network": "small",
        "timings_seconds": {label: summarize(values) for label, values in durations.items()},
    }
    return summary, failures, import_seconds + cold_seconds + sum(map(sum, durations.values()))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", choices=["W0-LINX", "W2-PRIMAT"], required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--parameter-schema", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--environment-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--batch-size", type=int, action="append", dest="batch_sizes")
    parser.add_argument("--hourly-price-cny", type=float, required=True)
    parser.add_argument("--yaml-python", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protocol, protocol_loader = load_yaml(args.config, args.yaml_python)
    parameter_schema, schema_loader = load_yaml(args.parameter_schema, args.yaml_python)
    registered = protocol["baselines"][args.baseline]
    repetitions = args.repetitions or int(protocol["execution"]["warm_repetitions"])
    batch_sizes = args.batch_sizes or [int(value) for value in protocol["execution"]["batch_sizes"]]
    required_repetitions = int(protocol["execution"]["warm_repetitions"])
    registered_batch_sizes = [int(value) for value in protocol["execution"]["batch_sizes"]]
    if repetitions < required_repetitions:
        raise ValueError(
            f"registered benchmark requires at least {required_repetitions} repetitions"
        )
    if sorted(set(batch_sizes)) != sorted(set(registered_batch_sizes)):
        raise ValueError(f"batch sizes must match registered set {registered_batch_sizes}")
    if any(value <= 0 for value in batch_sizes):
        raise ValueError("batch sizes must be positive")

    revision = git_revision(args.source_dir)
    if revision != registered["revision"]:
        raise ValueError(f"source revision {revision} != registered {registered['revision']}")
    if not args.inventory.is_file():
        raise FileNotFoundError(args.inventory)
    if not args.environment_lock.is_file():
        raise FileNotFoundError(args.environment_lock)

    parameters = parameter_schema["standard_bbn_fiducial"]["values"]
    if parameter_schema["status"] != "standard_bbn_subset_frozen_extension_semantics_pending":
        raise ValueError("parameter schema standard-BBN subset is not frozen")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=False)
    timings_path = output_dir / "timings.jsonl"
    failures_path = output_dir / "failures.jsonl"
    timings_path.touch()
    failures_path.touch()

    run_id = str(uuid.uuid4())
    started_at = utc_now()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    runner = run_w0_linx if args.baseline == "W0-LINX" else run_w2_primat
    result, failure_count, measured_solver_seconds = runner(
        args.source_dir, parameters, repetitions, batch_sizes, timings_path, failures_path
    )
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    finished_at = utc_now()
    usage = resource.getrusage(resource.RUSAGE_SELF)

    manifest = {
        "baseline": args.baseline,
        "benchmark_id": protocol["benchmark_id"],
        "batch_sizes": batch_sizes,
        "config": str(args.config),
        "config_sha256": sha256(args.config),
        "environment_lock": str(args.environment_lock),
        "environment_lock_sha256": sha256(args.environment_lock),
        "finished_at_utc": finished_at,
        "hardware_inventory": str(args.inventory),
        "hardware_inventory_sha256": sha256(args.inventory),
        "hostname": socket.gethostname(),
        "metadata_loaders": {
            "parameter_schema": schema_loader,
            "protocol": protocol_loader,
        },
        "node_name": json.loads(args.inventory.read_text(encoding="utf-8"))["node_name"],
        "parameter_schema": str(args.parameter_schema),
        "parameter_schema_sha256": sha256(args.parameter_schema),
        "parameters": parameters,
        "platform": platform.platform(),
        "precision": protocol["execution"]["precision"],
        "python": sys.version,
        "repetitions": repetitions,
        "run_id": run_id,
        "schema_version": 1,
        "scientific_use": "registered_standard_fiducial_runtime_slice_only",
        "source_dir": str(args.source_dir),
        "source_revision": revision,
        "started_at_utc": started_at,
        "status": "complete" if failure_count == 0 else "complete_with_failures",
    }
    json_dump(output_dir / "run_manifest.json", manifest)
    json_dump(output_dir / "runtime_summary.json", result)
    json_dump(
        output_dir / "posterior_metrics.json",
        {
            "reason": "matched posterior contract and old likelihood assets are not available",
            "schema_version": 1,
            "status": "not_run",
        },
    )
    worker_hours = wall_seconds / 3600
    json_dump(
        output_dir / "resource_report.json",
        {
            "cpu_core_hours": cpu_seconds / 3600,
            "cpu_seconds": cpu_seconds,
            "estimated_cost_cny": worker_hours * args.hourly_price_cny,
            "failure_count": failure_count,
            "gpu_hours": 0.0,
            "hourly_price_cny": args.hourly_price_cny,
            "max_rss_bytes": usage.ru_maxrss * 1024,
            "measured_solver_seconds": measured_solver_seconds,
            "schema_version": 1,
            "wall_seconds": wall_seconds,
            "worker_hours": worker_hours,
        },
    )
    print(output_dir)
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
