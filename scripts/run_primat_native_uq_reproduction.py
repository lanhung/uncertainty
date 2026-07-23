#!/usr/bin/env python3
"""Run the frozen PRIMAT v0.3.2 compiled-C native-UQ reproduction.

The run is intentionally an upstream-native calibration reproduction.  It
varies PRIMAT's complete 12-reaction small-network prior and neutron lifetime;
it is not the project's R0/ETR25 prior and is not UQ1 production evidence.

The three registered sample-count prefixes are durable checkpoints.  A
terminated process can resume from the last atomically written checkpoint
without changing the C backend's seed-indexed sample stream.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import resource
import socket
import subprocess
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import numpy as np
import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PROTOCOL_SHA256 = "4cc776daa3c6f31b816c35319e935002f11d9d3dfd7c91ed7b2d91ba7c593303"
EXPECTED_PROTOCOL_ID = "PRIMAT-NATIVE-UQ-REPRODUCTION-v1"
EXPECTED_REVISION = "21ff8f39fa18e3937e9fdf386cfa982361bfdfce"
EXPECTED_QUANTITIES = ("YPBBN", "DoH", "He3oH", "Li7oH")
CHECKPOINT_SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def atomic_npy(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        np.save(stream, values, allow_pickle=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())


def git_output(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def require_protocol(path: Path) -> tuple[dict[str, Any], str]:
    protocol_sha256 = sha256(path)
    if protocol_sha256 != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError(
            "frozen protocol byte drift: "
            f"expected {EXPECTED_PROTOCOL_SHA256}, got {protocol_sha256}"
        )
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict):
        raise TypeError("protocol must be a YAML mapping")
    if (
        protocol.get("schema_version") != 1
        or protocol.get("protocol_id") != EXPECTED_PROTOCOL_ID
        or protocol.get("task_id") != "UQ0-NATIVE-UQ-REPRO"
    ):
        raise RuntimeError("protocol identity drift")
    execution = protocol["execution"]
    if (
        execution["force_backend"] != "c"
        or execution["prohibited_backends"] != ["python"]
        or int(execution["draws"]) != 1000
        or int(execution["seed"]) != 2026072301
        or int(execution["n_jobs"]) != 20
        or int(execution["serial_replay_draws"]) != 16
        or int(execution["serial_replay_n_jobs"]) != 1
        or list(execution["prefix_draws"]) != [100, 300, 1000]
        or tuple(execution["quantities"]) != EXPECTED_QUANTITIES
    ):
        raise RuntimeError("registered execution contract drift")
    boundary = protocol["scientific_boundary"]
    if (
        boundary["claim_level"] != "C0"
        or boundary["production_use_authorized"] is not False
        or boundary["project_nuclear_prior_selected"] is not False
        or boundary["counts_as_R0_prior_validation"] is not False
        or boundary["counts_as_UQ1_direct_MC_truth"] is not False
    ):
        raise RuntimeError("scientific boundary drift or overclaim")
    return protocol, protocol_sha256


def verify_repository_inputs(protocol: dict[str, Any]) -> dict[str, str]:
    paths = {
        "environment_lock": (
            protocol["environment"]["lock"],
            protocol["environment"]["lock_sha256"],
        ),
        "forward_card": (
            protocol["registered_forward_baseline"]["card"],
            protocol["registered_forward_baseline"]["card_sha256"],
        ),
        "parameter_schema": (
            protocol["registered_forward_baseline"]["parameter_schema"],
            protocol["registered_forward_baseline"]["parameter_schema_sha256"],
        ),
    }
    result: dict[str, str] = {}
    for label, (relative, expected) in paths.items():
        path = REPOSITORY_ROOT / relative
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"{label} byte drift at {relative}: expected {expected}, got {actual}"
            )
        result[label] = actual
    return result


def verify_source(source_root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    source_root = source_root.resolve()
    revision = git_output(source_root, "rev-parse", "HEAD")
    if revision != EXPECTED_REVISION or revision != protocol["source"]["revision"]:
        raise RuntimeError(f"PRIMAT revision drift: {revision}")
    dirty = git_output(source_root, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise RuntimeError("PRIMAT source checkout is not clean")
    file_hashes: dict[str, str] = {}
    for relative, expected in protocol["source"]["source_hashes"].items():
        actual = sha256(source_root / relative)
        if actual != expected:
            raise RuntimeError(f"PRIMAT source-byte drift: {relative}")
        file_hashes[relative] = actual

    import primat  # type: ignore[import-not-found]
    from primat import backend  # type: ignore[import-not-found]

    distribution = importlib.metadata.distribution("primat")
    direct_url_text = distribution.read_text("direct_url.json")
    if not direct_url_text:
        raise RuntimeError("installed PRIMAT lacks direct_url.json provenance")
    direct_url = json.loads(direct_url_text)
    parsed = urlparse(str(direct_url.get("url", "")))
    installed_source = Path(unquote(parsed.path)).resolve()
    if parsed.scheme != "file" or installed_source != source_root:
        raise RuntimeError(
            f"installed PRIMAT source {direct_url.get('url')} does not match {source_root}"
        )
    if not backend.HAS_C_BACKEND:
        raise RuntimeError("frozen PRIMAT install has no compiled C backend")
    extension = importlib.util.find_spec("primat._primat_c")
    if extension is None or extension.origin is None:
        raise RuntimeError("compiled primat._primat_c extension is not importable")
    loaded_package = Path(primat.__file__).resolve()
    return {
        "repository": protocol["source"]["repository"],
        "release": protocol["source"]["release"],
        "revision": revision,
        "source_root": str(source_root),
        "source_file_hashes": file_hashes,
        "installed_package": str(loaded_package),
        "direct_url": direct_url,
        "compiled_extension": str(Path(extension.origin).resolve()),
        "compiled_extension_sha256": sha256(Path(extension.origin)),
        "worktree_clean": True,
    }


def verify_environment(protocol: dict[str, Any]) -> dict[str, Any]:
    import scipy

    actual = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    for name, value in actual.items():
        if value != str(protocol["environment"][name]):
            raise RuntimeError(
                f"environment drift for {name}: expected "
                f"{protocol['environment'][name]}, got {value}"
            )
    return {
        **actual,
        "precision": protocol["environment"]["precision"],
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


def solver_parameters(protocol: dict[str, Any]) -> dict[str, Any]:
    standard = protocol["standard_point"]
    solver = protocol["solver_parameters"]
    native = protocol["native_prior"]
    parameters = {
        "Omegabh2": float(standard["Omegabh2"]),
        "DeltaNeff": float(standard["DeltaNeff"]),
        "tau_n": float(standard["tau_n"]),
        "std_tau_n": float(native["neutron_lifetime"]["standard_deviation_seconds"]),
        "tau_n_normalization": bool(native["neutron_lifetime"]["tau_n_normalization"]),
        "network": str(solver["network"]),
        "numerical_precision": float(solver["numerical_precision"]),
        "rescale_nuclear_rates": bool(solver["rescale_nuclear_rates"]),
        "QED_corrections": bool(native["nuclear_qed_corrections"]),
        "nuclear_qed_corrections": bool(native["nuclear_qed_corrections"]),
        "mc_rate_rescale_cap": float(native["mc_rate_rescale_cap"]),
        "verbose": bool(solver["verbose"]),
        "debug": bool(solver["debug"]),
        "show_progress": bool(solver["show_progress"]),
    }
    if parameters != {
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
    }:
        raise RuntimeError("solver/native-prior parameter mapping drift")
    return parameters


def reconstruct_mc(
    names: list[str],
    centrals: list[float],
    samples: np.ndarray,
    seed: int,
    params: dict[str, Any],
) -> Any:
    from primat.main import MCQuantityResult, MCResult  # type: ignore[import-not-found]

    data = {
        name: MCQuantityResult(float(central), samples[:, index])
        for index, (name, central) in enumerate(zip(names, centrals))
    }
    return MCResult(
        data,
        seed=seed,
        params={**params, "verbose": False, "debug": False},
        custom_network=None,
        backend="c",
    )


def load_checkpoint(
    output_dir: Path,
    *,
    protocol_sha256: str,
    source_revision: str,
    seed: int,
    params: dict[str, Any],
) -> tuple[Any | None, int]:
    state_path = output_dir / "checkpoint.json"
    sample_candidates = list(output_dir.glob("checkpoint_samples_*.npy"))
    if not state_path.exists() and not sample_candidates:
        return None, 0
    if not state_path.is_file() or not sample_candidates:
        raise RuntimeError("partial checkpoint: state and samples must both exist")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    samples_name = state.get("samples_file")
    if (
        not isinstance(samples_name, str)
        or Path(samples_name).name != samples_name
        or not samples_name.startswith("checkpoint_samples_")
        or not samples_name.endswith(".npy")
    ):
        raise RuntimeError("checkpoint sample-file pointer is malformed")
    samples_path = output_dir / samples_name
    if not samples_path.is_file():
        raise RuntimeError("partial checkpoint: state and samples must both exist")
    if (
        state.get("schema_version") != CHECKPOINT_SCHEMA_VERSION
        or state.get("protocol_id") != EXPECTED_PROTOCOL_ID
        or state.get("protocol_sha256") != protocol_sha256
        or state.get("source_revision") != source_revision
        or state.get("backend") != "c"
        or state.get("seed") != seed
        or state.get("parameters") != params
        or state.get("samples_sha256") != sha256(samples_path)
    ):
        raise RuntimeError("checkpoint provenance or execution contract drift")
    names = state.get("quantity_names")
    centrals = state.get("centrals")
    completed = state.get("completed_draws")
    if (
        not isinstance(names, list)
        or not isinstance(centrals, list)
        or len(names) != len(set(names))
        or len(names) != len(centrals)
        or not set(EXPECTED_QUANTITIES).issubset(names)
        or completed not in (100, 300, 1000)
    ):
        raise RuntimeError("checkpoint metadata is malformed")
    samples = np.load(samples_path, allow_pickle=False)
    if (
        samples.dtype != np.float64
        or samples.shape != (int(completed), len(names))
        or not np.isfinite(samples).all()
    ):
        raise RuntimeError("checkpoint sample array is malformed")
    if not all(math.isfinite(float(value)) for value in centrals):
        raise RuntimeError("checkpoint centrals are non-finite")
    return reconstruct_mc(names, centrals, samples, seed, params), int(completed)


def write_checkpoint(
    output_dir: Path,
    mc: Any,
    *,
    protocol_sha256: str,
    source_revision: str,
    seed: int,
    params: dict[str, Any],
) -> None:
    names = mc.quantity_names()
    samples = np.asarray(mc.samples_array(), dtype=np.float64)
    samples_name = f"checkpoint_samples_{samples.shape[0]}.npy"
    samples_path = output_dir / samples_name
    atomic_npy(samples_path, samples)
    state = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "protocol_id": EXPECTED_PROTOCOL_ID,
        "protocol_sha256": protocol_sha256,
        "source_revision": source_revision,
        "backend": mc.backend,
        "seed": seed,
        "parameters": params,
        "completed_draws": int(samples.shape[0]),
        "quantity_names": names,
        "centrals": [float(mc[name].central) for name in names],
        "samples_file": samples_name,
        "samples_sha256": sha256(samples_path),
        "updated_at_utc": utc_now(),
    }
    atomic_json(output_dir / "checkpoint.json", state)


def selected_samples(mc: Any) -> np.ndarray:
    return np.column_stack(
        [np.asarray(mc[name].values, dtype=np.float64) for name in EXPECTED_QUANTITIES]
    )


def summarize_prefixes(
    samples: np.ndarray,
    prefix_draws: list[int],
    quantile_probabilities: list[float],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for draws in prefix_draws:
        prefix = samples[:draws]
        quantities: dict[str, Any] = {}
        for index, name in enumerate(EXPECTED_QUANTITIES):
            values = prefix[:, index]
            quantities[name] = {
                "mean": float(np.mean(values)),
                "standard_deviation_ddof1": float(np.std(values, ddof=1)),
                "quantiles": {
                    format(probability, ".3f"): float(np.quantile(values, probability))
                    for probability in quantile_probabilities
                },
            }
        result[str(draws)] = {"draws": draws, "quantities": quantities}
    return result


def samples_tsv(samples: np.ndarray) -> str:
    lines = ["\t".join(EXPECTED_QUANTITIES)]
    lines.extend("\t".join(format(float(value), ".17e") for value in row) for row in samples)
    return "\n".join(lines) + "\n"


def matrix_tsv(kind: str, matrix: np.ndarray, draws: int, seed: int) -> str:
    estimator = (
        "sample covariance (ddof=1)"
        if kind == "covariance"
        else "Pearson correlation derived from sample covariance (ddof=1)"
    )
    lines = [
        f"# {kind}; N={draws}; seed={seed}; {estimator}",
        "quantity\t" + "\t".join(EXPECTED_QUANTITIES),
    ]
    for name, row in zip(EXPECTED_QUANTITIES, matrix):
        lines.append(name + "\t" + "\t".join(format(float(value), ".17e") for value in row))
    return "\n".join(lines) + "\n"


def central_acceptance(central: dict[str, float], protocol: dict[str, Any]) -> dict[str, Any]:
    baseline = protocol["registered_forward_baseline"]
    differences: dict[str, float] = {}
    for name, expected in baseline["central_outputs"].items():
        actual = float(central[name])
        absolute = abs(actual - float(expected))
        allowed = float(baseline["central_output_absolute_tolerance"]) + float(
            baseline["central_output_relative_tolerance"]
        ) * abs(float(expected))
        if not math.isfinite(actual) or absolute > allowed:
            raise RuntimeError(f"central output mismatch for {name}: {actual} vs {expected}")
        differences[name] = absolute
    return {
        "accepted": True,
        "outputs": central,
        "reference_outputs": baseline["central_outputs"],
        "absolute_differences": differences,
        "relative_tolerance": baseline["central_output_relative_tolerance"],
        "absolute_tolerance": baseline["central_output_absolute_tolerance"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPOSITORY_ROOT / "configs/benchmarks/primat_native_uq_reproduction_v1.yaml",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--hourly-price-cny", required=True, type=float)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.hourly_price_cny < 0 or not math.isfinite(args.hourly_price_cny):
        raise ValueError("--hourly-price-cny must be finite and non-negative")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    failures_path = output_dir / "failures.jsonl"
    timings_path = output_dir / "timings.jsonl"
    failures_path.touch(exist_ok=True)
    timings_path.touch(exist_ok=True)

    wall_started = time.perf_counter()
    process_started = time.process_time()
    usage_started = resource.getrusage(resource.RUSAGE_SELF)
    protocol: dict[str, Any] | None = None
    try:
        protocol, protocol_sha256 = require_protocol(args.config.resolve())
        repository_inputs = verify_repository_inputs(protocol)
        source = verify_source(args.source_root, protocol)
        environment = verify_environment(protocol)
        parameters = solver_parameters(protocol)
        execution = protocol["execution"]
        seed = int(execution["seed"])

        from primat.backend import run_mc  # type: ignore[import-not-found]

        mc, completed = load_checkpoint(
            output_dir,
            protocol_sha256=protocol_sha256,
            source_revision=source["revision"],
            seed=seed,
            params=parameters,
        )
        resumed_from = completed
        for target in [int(value) for value in execution["prefix_draws"]]:
            if completed >= target:
                continue
            started = time.perf_counter()
            mc = run_mc(
                target,
                list(EXPECTED_QUANTITIES),
                params=parameters,
                force_backend="c",
                seed=seed,
                n_jobs=int(execution["n_jobs"]),
                prev=mc,
                log_backend=True,
                progress=False,
            )
            elapsed = time.perf_counter() - started
            if mc.backend != "c":
                raise RuntimeError(f"prohibited backend used: {mc.backend!r}")
            if mc.samples_array().shape[0] != target:
                raise RuntimeError("PRIMAT returned an unexpected sample count")
            append_jsonl(
                timings_path,
                {
                    "stage": "parallel_prefix",
                    "target_draws": target,
                    "new_draws": target - completed,
                    "n_jobs": int(execution["n_jobs"]),
                    "backend": "c",
                    "elapsed_seconds": elapsed,
                    "completed_at_utc": utc_now(),
                },
            )
            # Publish the checkpoint pointer only after the corresponding
            # completion event is durable. Versioned sample files mean a crash
            # before this atomic JSON replacement leaves the prior checkpoint
            # fully usable.
            write_checkpoint(
                output_dir,
                mc,
                protocol_sha256=protocol_sha256,
                source_revision=source["revision"],
                seed=seed,
                params=parameters,
            )
            completed = target
            print(f"PROGRESS {completed}/{int(execution['draws'])}", flush=True)

        if mc is None or completed != int(execution["draws"]):
            raise RuntimeError("registered 1,000-draw run did not complete")
        primary = selected_samples(mc)
        if (
            primary.shape != (int(execution["draws"]), len(EXPECTED_QUANTITIES))
            or not np.isfinite(primary).all()
            or not np.all(primary > 0)
        ):
            raise RuntimeError("selected primary abundance samples are invalid")

        replay_started = time.perf_counter()
        replay_mc = run_mc(
            int(execution["serial_replay_draws"]),
            list(EXPECTED_QUANTITIES),
            params=parameters,
            force_backend="c",
            seed=seed,
            n_jobs=int(execution["serial_replay_n_jobs"]),
            prev=None,
            log_backend=True,
            progress=False,
        )
        replay_elapsed = time.perf_counter() - replay_started
        if replay_mc.backend != "c":
            raise RuntimeError("serial replay did not use the compiled C backend")
        replay = selected_samples(replay_mc)
        prefix = primary[: replay.shape[0]]
        if not np.array_equal(replay, prefix):
            maximum = float(np.max(np.abs(replay - prefix)))
            raise RuntimeError(f"parallel/serial seed-prefix replay mismatch: max abs {maximum}")
        append_jsonl(
            timings_path,
            {
                "stage": "serial_prefix_replay",
                "target_draws": int(execution["serial_replay_draws"]),
                "new_draws": int(execution["serial_replay_draws"]),
                "n_jobs": int(execution["serial_replay_n_jobs"]),
                "backend": "c",
                "elapsed_seconds": replay_elapsed,
                "completed_at_utc": utc_now(),
            },
        )

        central = {name: float(mc[name].central) for name in EXPECTED_QUANTITIES}
        central_check = central_acceptance(central, protocol)
        covariance = np.atleast_2d(np.cov(primary, rowvar=False, ddof=1))
        correlation = np.atleast_2d(np.corrcoef(primary, rowvar=False))
        standard_deviations = np.std(primary, axis=0, ddof=1)
        if (
            not np.isfinite(covariance).all()
            or not np.isfinite(correlation).all()
            or not np.all(standard_deviations > 0)
            or not np.array_equal(covariance, covariance.T)
            or not np.allclose(correlation, correlation.T, rtol=0.0, atol=1.0e-15)
            or not np.allclose(np.diag(correlation), 1.0, rtol=0.0, atol=1.0e-15)
        ):
            raise RuntimeError("sample covariance/correlation acceptance failed")

        atomic_npy(output_dir / execution["raw_samples_npy"], primary)
        atomic_text(output_dir / execution["raw_samples_tsv"], samples_tsv(primary))
        atomic_text(
            output_dir / execution["covariance_tsv"],
            matrix_tsv("covariance", covariance, primary.shape[0], seed),
        )
        atomic_text(
            output_dir / execution["correlation_tsv"],
            matrix_tsv("correlation", correlation, primary.shape[0], seed),
        )

        usage_finished = resource.getrusage(resource.RUSAGE_SELF)
        wall_seconds = time.perf_counter() - wall_started
        process_seconds = time.process_time() - process_started
        cpu_seconds_children = max(
            0.0,
            (usage_finished.ru_utime + usage_finished.ru_stime)
            - (usage_started.ru_utime + usage_started.ru_stime),
        )
        timing_records = [
            json.loads(line)
            for line in timings_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        measured_solver_wall_seconds = sum(
            float(record["elapsed_seconds"]) for record in timing_records
        )
        accounted_wall_seconds = max(wall_seconds, measured_solver_wall_seconds)
        resource_report = {
            "schema_version": 1,
            "task_id": protocol["task_id"],
            "protocol_id": protocol["protocol_id"],
            "hostname": socket.gethostname(),
            "logical_cpu_count": os.cpu_count(),
            "wall_seconds": accounted_wall_seconds,
            "current_attempt_wall_seconds": wall_seconds,
            "measured_solver_wall_seconds_all_attempts": measured_solver_wall_seconds,
            "wall_accounting_scope": (
                "max(current_attempt_wall, durable_solver_timings_all_attempts); "
                "resumed-attempt setup time before the current process is unavailable"
            ),
            "process_cpu_seconds": process_seconds,
            "accounted_process_rusage_seconds": cpu_seconds_children,
            "max_rss_kib": int(usage_finished.ru_maxrss),
            "hourly_price_cny": args.hourly_price_cny,
            "estimated_cost_cny": (args.hourly_price_cny * accounted_wall_seconds / 3600.0),
            "gpu_hours": 0.0,
            "completed_at_utc": utc_now(),
        }
        atomic_json(output_dir / execution["resource_report_json"], resource_report)

        files = {
            "samples_npy": execution["raw_samples_npy"],
            "samples_tsv": execution["raw_samples_tsv"],
            "covariance_tsv": execution["covariance_tsv"],
            "correlation_tsv": execution["correlation_tsv"],
            "failures_jsonl": execution["failures_jsonl"],
            "timings_jsonl": execution["timings_jsonl"],
            "resource_report_json": execution["resource_report_json"],
            "checkpoint_json": "checkpoint.json",
            "checkpoint_samples_npy": json.loads(
                (output_dir / "checkpoint.json").read_text(encoding="utf-8")
            )["samples_file"],
        }
        file_evidence = {
            label: {"path": relative, "sha256": sha256(output_dir / relative)}
            for label, relative in files.items()
        }
        prefix_statistics = summarize_prefixes(
            primary,
            [int(value) for value in execution["prefix_draws"]],
            [float(value) for value in execution["quantile_probabilities"]],
        )
        artifact: dict[str, Any] = {
            "schema_version": 1,
            "artifact_id": EXPECTED_PROTOCOL_ID,
            "task_id": protocol["task_id"],
            "status": "completed_upstream_native_compiled_C_calibration",
            "protocol": {
                "path": str(args.config.resolve().relative_to(REPOSITORY_ROOT)),
                "sha256": protocol_sha256,
            },
            "scientific_scope": {
                "claim_level": "C0",
                "upstream_native_calibration_only": True,
                "project_nuclear_prior_selected": False,
                "R0_prior_validated": False,
                "UQ1_direct_MC_truth": False,
                "production_authorized": False,
                "solver_independent_validation": False,
                "novelty_claim": False,
            },
            "source": source,
            "environment": environment,
            "repository_inputs": repository_inputs,
            "execution": {
                "api": execution["api"],
                "backend": mc.backend,
                "force_backend": "c",
                "prohibited_backend_used": False,
                "draws": primary.shape[0],
                "seed": seed,
                "n_jobs": int(execution["n_jobs"]),
                "resumed_from_draws": resumed_from,
                "prefix_draws": execution["prefix_draws"],
                "quantities": list(EXPECTED_QUANTITIES),
                "parameters": parameters,
                "native_thermonuclear_latent_count": int(
                    protocol["native_prior"]["thermonuclear_latents"]["count"]
                ),
            },
            "central_acceptance": central_check,
            "prefix_statistics": prefix_statistics,
            "sample_standard_deviations_ddof1": {
                name: float(value) for name, value in zip(EXPECTED_QUANTITIES, standard_deviations)
            },
            "serial_replay": {
                "draws": replay.shape[0],
                "seed": seed,
                "n_jobs": int(execution["serial_replay_n_jobs"]),
                "backend": replay_mc.backend,
                "exact_parallel_prefix_match": True,
                "maximum_absolute_difference": 0.0,
                "samples": replay.tolist(),
                "samples_sha256": digest_json(replay.tolist()),
            },
            "failure_accounting": {
                "structured_failure_count": 0,
                "failures_file_empty": (output_dir / execution["failures_jsonl"]).stat().st_size
                == 0,
            },
            "acceptance": {
                "compiled_C_backend": True,
                "parallel_serial_prefix_exact": True,
                "all_selected_samples_finite": True,
                "all_selected_abundances_positive": True,
                "all_selected_standard_deviations_positive": True,
                "covariance_finite_and_symmetric": True,
                "correlation_finite_symmetric_unit_diagonal": True,
                "prefix_statistics_diagnostic_only": True,
                "accepted": True,
            },
            "files": file_evidence,
            "resource_summary": {
                "wall_seconds": accounted_wall_seconds,
                "estimated_cost_cny": resource_report["estimated_cost_cny"],
                "gpu_hours": 0.0,
            },
            "known_limitations": protocol["known_limitations"],
            "completed_at_utc": utc_now(),
        }
        if not artifact["failure_accounting"]["failures_file_empty"]:
            raise RuntimeError("successful artifact cannot retain structured failures")
        artifact["evidence_sha256"] = digest_json(artifact)
        atomic_json(output_dir / execution["output_artifact"], artifact)
        print(
            json.dumps(
                {
                    "accepted": True,
                    "artifact": str(output_dir / execution["output_artifact"]),
                    "draws": primary.shape[0],
                    "resumed_from_draws": resumed_from,
                    "evidence_sha256": artifact["evidence_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        append_jsonl(
            failures_path,
            {
                "recorded_at_utc": utc_now(),
                "stage": "native_uq_reproduction",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
                "protocol_id": (
                    protocol.get("protocol_id") if isinstance(protocol, dict) else None
                ),
            },
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
