#!/usr/bin/env python3
"""Run the frozen PRyMordial native abundance-UQ reproduction.

The upstream solver stores configuration and nuisance parameters in module
globals.  This runner therefore uses spawn-based processes (never threads),
fully assigns every mutable input for every draw, records the exact latent
manifest before execution, and checkpoints every terminal draw.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
import math
import multiprocessing
import os
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "configs/benchmarks/prymordial_native_uq_reproduction_v1.yaml"
EXPECTED_PROTOCOL_SHA256 = "0b3c71d302f18531ce2504aaa8968685e21b1d0165841854ba042b6f9be5c297"
EXPECTED_PROTOCOL_ID = "PRYMORDIAL-NATIVE-UQ-REPRODUCTION-v1"
EXPECTED_TASK_ID = "UQ0-NATIVE-UQ-REPRO"
EXPECTED_REVISION = "725d8a8db3ad5ea2630580d825c9d0d69ed76533"
OUTPUT_FILENAMES = {
    "run_manifest": "run_manifest.json",
    "draw_manifest": "draw_manifest.jsonl",
    "results": "results.jsonl",
    "failures": "failures.jsonl",
    "state": "run_state.json",
    "summary": "summary.json",
}
THREAD_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMBA_NUM_THREADS": "1",
}
RATE_PARAMETER_NAMES = (
    "p_npdg",
    "p_dpHe3g",
    "p_ddHe3n",
    "p_ddtp",
    "p_tpag",
    "p_tdan",
    "p_taLi7g",
    "p_He3ntp",
    "p_He3dap",
    "p_He3aBe7g",
    "p_Be7nLi7p",
    "p_Li7paa",
    "p_Li7paag",
    "p_Be7naa",
    "p_Be7daap",
    "p_daLi6g",
    "p_Li6pBe7g",
    "p_Li6pHe3a",
    "p_B8naap",
    "p_Li6He3aap",
    "p_Li6taan",
    "p_Li6tLi8p",
    "p_Li7He3Li6a",
    "p_Li8He3Li7a",
    "p_Be7tLi6a",
    "p_B8tBe7a",
    "p_B8nLi6He3",
    "p_B8nBe7d",
    "p_Li6tLi7d",
    "p_Li6He3Be7d",
    "p_Li7He3aad",
    "p_Li8He3aat",
    "p_Be7taad",
    "p_Be7tLi7He3",
    "p_B8dBe7He3",
    "p_B8taaHe3",
    "p_Be7He3ppaa",
    "p_ddag",
    "p_He3He3app",
    "p_Be7pB8g",
    "p_Li7daan",
    "p_dntg",
    "p_ttann",
    "p_He3nag",
    "p_He3tad",
    "p_He3tanp",
    "p_Li7taan",
    "p_Li7He3aanp",
    "p_Li8dLi7t",
    "p_Be7taanp",
    "p_Be7He3aapp",
    "p_Li6nta",
    "p_He3tLi6g",
    "p_anpLi6g",
    "p_Li6nLi7g",
    "p_Li6dLi7p",
    "p_Li6dBe7n",
    "p_Li7nLi8g",
    "p_Li7dLi8p",
    "p_Li8paan",
    "p_annHe6g",
    "p_ppndp",
    "p_Li7taann",
)

_UPSTREAM: tuple[Any, Any] | None = None


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def add_record_digest(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["record_sha256"] = digest_json(result)
    return result


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    payload = canonical_json(add_record_digest(record)) + b"\n"
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while appending checkpoint record")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise RuntimeError(f"partial JSONL record: {path}:{line_number}")
            record = json.loads(line)
            stored = record.pop("record_sha256")
            if digest_json(record) != stored:
                raise RuntimeError(f"JSONL record digest mismatch: {path}:{line_number}")
            record["record_sha256"] = stored
            records.append(record)
    return records


def load_evidence_json(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    stored = value.pop("evidence_sha256", None)
    if not isinstance(stored, str) or digest_json(value) != stored:
        raise RuntimeError(f"{label} evidence digest mismatch")
    value["evidence_sha256"] = stored
    return value


def load_protocol(path: Path) -> dict[str, Any]:
    if sha256(path) != EXPECTED_PROTOCOL_SHA256:
        raise ValueError("frozen PRyMordial native-UQ protocol digest drift")
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict):
        raise ValueError("protocol must be a YAML mapping")
    if protocol.get("schema_version") != 1:
        raise ValueError("protocol schema drift")
    if protocol.get("protocol_id") != EXPECTED_PROTOCOL_ID:
        raise ValueError("protocol identity drift")
    if protocol.get("task_id") != EXPECTED_TASK_ID:
        raise ValueError("task identity drift")

    source = protocol["source"]
    execution = protocol["execution"]
    prior = protocol["native_prior"]
    acceptance = protocol["acceptance"]
    if source["revision"] != EXPECTED_REVISION:
        raise ValueError("source revision drift")
    if prior["nuclear_rates"]["count"] != len(RATE_PARAMETER_NAMES):
        raise ValueError("native rate count drift")
    if execution["process_pool_start_method"] != "spawn":
        raise ValueError("process start method must remain spawn")
    if execution["required_thread_environment"] != THREAD_ENVIRONMENT:
        raise ValueError("thread environment contract drift")
    if execution["output_files"] != OUTPUT_FILENAMES:
        raise ValueError("output filename contract drift")
    if execution["checkpoint_every_completed_draws"] != 1:
        raise ValueError("checkpoint interval must remain one draw")
    if execution["no_failure_resampling"] is not True:
        raise ValueError("failure resampling must remain prohibited")
    if acceptance["fail_closed_if_any_contract_check_is_missing"] is not True:
        raise ValueError("fail-closed contract drift")
    if int(protocol["rng"]["draw_count"]) != int(acceptance["expected_attempted_draws"]):
        raise ValueError("draw-count contract is internally inconsistent")
    return protocol


def git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def tracked_worktree_matches_head(root: Path) -> bool:
    return (
        subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", "."],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def validate_source(source_root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    source = protocol["source"]
    if git_revision(source_root) != source["revision"]:
        raise RuntimeError("PRyMordial revision drift")
    if not tracked_worktree_matches_head(source_root):
        raise RuntimeError("PRyMordial tracked worktree differs from frozen HEAD")
    observed_hashes: dict[str, str] = {}
    for relative, details in source["required_files"].items():
        candidate = source_root / relative
        if not candidate.is_file():
            raise RuntimeError(f"required source file missing: {relative}")
        observed_hashes[relative] = sha256(candidate)
        if observed_hashes[relative] != details["sha256"]:
            raise RuntimeError(f"source byte drift: {relative}")

    import numpy as np

    table = np.loadtxt(source_root / "PRyM_Yp_DH_cosmoMC_2023.dat")
    reference = protocol["public_reference"]
    selected = table[
        (table[:, 0] == reference["conditioned_parameters"]["omega_b_h2"])
        & (table[:, 2] == reference["conditioned_parameters"]["delta_neff"])
    ]
    if selected.shape != (1, 8):
        raise RuntimeError("public reference row is missing or non-unique")
    expected = reference["exact_row"]
    expected_row = [
        reference["conditioned_parameters"]["omega_b_h2"],
        expected["eta10"],
        reference["conditioned_parameters"]["delta_neff"],
        expected["Yp_CMB"],
        expected["Yp_BBN"],
        expected["sigma_Yp_BBN"],
        expected["D_over_H"],
        expected["sigma_D_over_H"],
    ]
    if not np.array_equal(selected[0], np.asarray(expected_row, dtype=np.float64)):
        raise RuntimeError("public reference row byte-derived values drift")
    return {
        "repository": source["repository"],
        "revision": source["revision"],
        "license": source["license"],
        "required_file_sha256": observed_hashes,
        "tracked_worktree_matches_HEAD": True,
    }


def validate_environment(protocol: dict[str, Any]) -> dict[str, str]:
    expected = protocol["environment"]
    observed = {
        "python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"),
        "scipy": importlib.metadata.version("scipy"),
        "platform": platform.platform(),
        "precision": str(expected["precision"]),
        "backend": str(expected["backend"]),
        "lock_path": str(expected["lock_path"]),
        "lock_sha256": str(expected["lock_sha256"]),
    }
    for package in ("python", "numpy", "scipy"):
        if observed[package] != str(expected[package]):
            raise RuntimeError(
                f"environment drift for {package}: {observed[package]} != {expected[package]}"
            )
    lock_path = ROOT / expected["lock_path"]
    if not lock_path.is_file() or sha256(lock_path) != expected["lock_sha256"]:
        raise RuntimeError("solver environment lock provenance drift")
    return observed


def generate_draw_manifest(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    import numpy as np

    rng_contract = protocol["rng"]
    prior = protocol["native_prior"]
    root_seed = np.random.SeedSequence(int(rng_contract["master_seed"]))
    children = root_seed.spawn(int(rng_contract["draw_count"]))
    records: list[dict[str, Any]] = []
    for draw_id, child in enumerate(children):
        generator = np.random.Generator(np.random.PCG64DXSM(child))
        tau = float(
            generator.normal(
                float(prior["neutron_lifetime"]["mean_seconds"]),
                float(prior["neutron_lifetime"]["sigma_seconds"]),
            )
        )
        q = [float(value) for value in generator.normal(0.0, 1.0, len(RATE_PARAMETER_NAMES))]
        record = add_record_digest(
            {
                "schema_version": 1,
                "draw_id": draw_id,
                "seed_entropy": int(rng_contract["master_seed"]),
                "seed_spawn_key": list(child.spawn_key),
                "bit_generator": rng_contract["numpy_bit_generator"],
                "tau_n_seconds": tau,
                "nuclear_rate_parameter_names": list(RATE_PARAMETER_NAMES),
                "nuclear_rate_q": q,
            }
        )
        records.append(record)
    return records


def write_draw_manifest(path: Path, records: list[dict[str, Any]]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        for record in records:
            handle.write(canonical_json(record) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def validate_draw_manifest(records: list[dict[str, Any]], protocol: dict[str, Any]) -> None:
    expected_count = int(protocol["rng"]["draw_count"])
    if len(records) != expected_count:
        raise RuntimeError("draw manifest count drift")
    expected_names = list(RATE_PARAMETER_NAMES)
    for expected_id, record in enumerate(records):
        if record["draw_id"] != expected_id:
            raise RuntimeError("draw manifest IDs are not exact and ordered")
        if record["seed_spawn_key"] != [expected_id]:
            raise RuntimeError("draw seed spawn-key drift")
        if record["nuclear_rate_parameter_names"] != expected_names:
            raise RuntimeError("draw parameter ordering drift")
        if len(record["nuclear_rate_q"]) != len(RATE_PARAMETER_NAMES):
            raise RuntimeError("draw latent dimension drift")
        values = [record["tau_n_seconds"], *record["nuclear_rate_q"]]
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
            raise RuntimeError("draw manifest contains a non-finite latent")


def draw_manifest_digest(records: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        b"".join(canonical_json(record) + b"\n" for record in records)
    ).hexdigest()


def _worker_initialize(source_root: str) -> None:
    global _UPSTREAM
    for key, value in THREAD_ENVIRONMENT.items():
        os.environ[key] = value
    root = Path(source_root).resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))
    import PRyM.PRyM_init as init  # type: ignore[import-not-found]
    import PRyM.PRyM_main as main  # type: ignore[import-not-found]

    _UPSTREAM = init, main


def _assign_solver_contract(init: Any, record: dict[str, Any]) -> None:
    init.verbose_flag = False
    init.numba_flag = True
    init.numdiff_flag = False
    init.aTid_flag = True
    init.NP_thermo_flag = False
    init.xi_NP = 1.0
    init.NP_nu_flag = False
    init.NP_e_flag = False
    init.compute_bckg_flag = True
    init.save_bckg_flag = False
    init.compute_nTOp_flag = True
    init.nTOpBorn_flag = False
    init.compute_nTOp_thermal_flag = False
    init.save_nTOp_flag = False
    init.save_nTOp_thermal_flag = False
    init.tau_n_flag = True
    init.NP_nTOp_flag = False
    init.NP_delta_nTOp = 0.0
    init.NP_nuclear_flag = False
    init.smallnet_flag = False
    init.julia_flag = False
    init.nacreii_flag = True
    init.num_reactions = len(RATE_PARAMETER_NAMES)
    init.Omegabh2 = 0.0222
    init.eta0b = init.Omegabh2_to_eta0b * init.Omegabh2
    init.munuOverTnu = 0.0
    init.DeltaNeff = 0.0
    init.tau_n = float(record["tau_n_seconds"])
    if len(record["nuclear_rate_q"]) != len(RATE_PARAMETER_NAMES):
        raise RuntimeError("worker draw latent dimension drift")
    for name, value in zip(RATE_PARAMETER_NAMES, record["nuclear_rate_q"]):
        setattr(init, name, float(value))
        setattr(init, f"NP_delta_{name.removeprefix('p_')}", 0.0)
    init.ReloadKeyRates()


def _worker_draw(record: dict[str, Any]) -> dict[str, Any]:
    if _UPSTREAM is None:
        raise RuntimeError("worker was not initialized")
    init, main = _UPSTREAM
    started = time.perf_counter()
    _assign_solver_contract(init, record)
    raw = main.PRyMclass().PRyMresults()
    yp = float(raw[4])
    dh = float(raw[5]) * 1.0e-5
    if not (math.isfinite(yp) and math.isfinite(dh) and yp > 0.0 and dh > 0.0):
        raise FloatingPointError(f"nonphysical abundance output: Yp={yp}, D/H={dh}")
    return {
        "draw_id": int(record["draw_id"]),
        "input_record_sha256": record["record_sha256"],
        "Yp_BBN": yp,
        "D_over_H": dh,
        "elapsed_seconds": time.perf_counter() - started,
    }


def terminal_records(output_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    successes = load_jsonl(output_dir / OUTPUT_FILENAMES["results"])
    failures = load_jsonl(output_dir / OUTPUT_FILENAMES["failures"])
    ids = [int(record["draw_id"]) for record in [*successes, *failures]]
    if len(ids) != len(set(ids)):
        raise RuntimeError("a draw has multiple terminal records")
    return successes, failures


def write_state(
    output_dir: Path,
    *,
    run_id: str,
    expected: int,
    successes: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    status: str,
) -> None:
    completed_ids = sorted(int(record["draw_id"]) for record in [*successes, *failures])
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "status": status,
        "expected_attempted_draws": expected,
        "completed_draw_ids": completed_ids,
        "successful_draws": len(successes),
        "failed_draws": len(failures),
        "updated_at_utc": utc_now(),
    }
    state["evidence_sha256"] = digest_json(state)
    atomic_json(output_dir / OUTPUT_FILENAMES["state"], state)


def failure_record(draw: dict[str, Any], error: BaseException) -> dict[str, Any]:
    message = str(error)[:2000] or "<empty exception message>"
    trace = traceback.format_exc()[-4000:] or "<traceback unavailable>"
    return {
        "schema_version": 1,
        "draw_id": int(draw["draw_id"]),
        "input_record_sha256": draw["record_sha256"],
        "error_type": type(error).__name__,
        "error_message": message,
        "traceback_tail": trace,
    }


def execute_pending(
    *,
    source_root: Path,
    output_dir: Path,
    run_id: str,
    draws: list[dict[str, Any]],
    workers: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    successes, failures = terminal_records(output_dir)
    terminal_ids = {int(record["draw_id"]) for record in [*successes, *failures]}
    pending = [record for record in draws if int(record["draw_id"]) not in terminal_ids]
    expected = len(draws)
    if not pending:
        write_state(
            output_dir,
            run_id=run_id,
            expected=expected,
            successes=successes,
            failures=failures,
            status="draws_complete",
        )
        return successes, failures

    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        mp_context=context,
        initializer=_worker_initialize,
        initargs=(str(source_root),),
    ) as executor:
        future_to_draw = {executor.submit(_worker_draw, record): record for record in pending}
        for future in concurrent.futures.as_completed(future_to_draw):
            record = future_to_draw[future]
            try:
                result = future.result()
            except BaseException as error:
                append_jsonl(
                    output_dir / OUTPUT_FILENAMES["failures"],
                    failure_record(record, error),
                )
            else:
                append_jsonl(
                    output_dir / OUTPUT_FILENAMES["results"],
                    {"schema_version": 1, **result},
                )
            successes, failures = terminal_records(output_dir)
            write_state(
                output_dir,
                run_id=run_id,
                expected=expected,
                successes=successes,
                failures=failures,
                status="running" if len(successes) + len(failures) < expected else "draws_complete",
            )
            print(f"PROGRESS {len(successes) + len(failures)}/{expected}", flush=True)
    return terminal_records(output_dir)


def run_controls(
    source_root: Path,
    draws: list[dict[str, Any]],
    sentinel_indices: list[int],
    workers: int,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    prior = protocol["native_prior"]
    central = add_record_digest(
        {
            "schema_version": 1,
            "draw_id": -1,
            "seed_entropy": None,
            "seed_spawn_key": [],
            "bit_generator": None,
            "tau_n_seconds": float(prior["neutron_lifetime"]["mean_seconds"]),
            "nuclear_rate_parameter_names": list(RATE_PARAMETER_NAMES),
            "nuclear_rate_q": [0.0] * len(RATE_PARAMETER_NAMES),
        }
    )
    cases = [central, *(draws[index] for index in sentinel_indices)]
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(workers, len(cases)),
        mp_context=context,
        initializer=_worker_initialize,
        initargs=(str(source_root),),
    ) as executor:
        outputs = list(executor.map(_worker_draw, cases))
    return {
        "central": outputs[0],
        "sentinel_repeats": [
            {"draw_id": index, **output} for index, output in zip(sentinel_indices, outputs[1:])
        ],
    }


def bootstrap_sigma_interval(
    values: Any,
    *,
    seed: int,
    resamples: int,
    quantiles: tuple[float, float],
) -> list[float]:
    import numpy as np

    array = np.asarray(values, dtype=np.float64)
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    standard_deviations = np.empty(resamples, dtype=np.float64)
    batch = 256
    for start in range(0, resamples, batch):
        stop = min(start + batch, resamples)
        indices = generator.integers(0, len(array), size=(stop - start, len(array)))
        standard_deviations[start:stop] = np.std(array[indices], axis=1, ddof=1)
    try:
        result = np.quantile(standard_deviations, quantiles, method="linear")
    except TypeError:  # NumPy < 1.22, used only by lightweight local tests.
        result = np.quantile(standard_deviations, quantiles, interpolation="linear")
    return [float(value) for value in result]


def relative_drift(value: float, repeated: float) -> float:
    return abs(value - repeated) / max(abs(value), sys.float_info.min)


def build_summary(
    *,
    protocol: dict[str, Any],
    run_id: str,
    successes: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    controls: dict[str, Any],
) -> dict[str, Any]:
    import numpy as np

    ordered = sorted(successes, key=lambda record: int(record["draw_id"]))
    yp = np.asarray([record["Yp_BBN"] for record in ordered], dtype=np.float64)
    dh = np.asarray([record["D_over_H"] for record in ordered], dtype=np.float64)
    reference = protocol["public_reference"]["exact_row"]
    acceptance = protocol["acceptance"]
    rng = protocol["rng"]
    quantiles = tuple(float(value) for value in acceptance["bootstrap_interval_quantiles"])
    statistics: dict[str, Any] = {}
    for offset, (name, values, center_key, sigma_key) in enumerate(
        (
            ("Yp_BBN", yp, "Yp_BBN", "sigma_Yp_BBN"),
            ("D_over_H", dh, "D_over_H", "sigma_D_over_H"),
        )
    ):
        public_center = float(reference[center_key])
        public_sigma = float(reference[sigma_key])
        sample_sigma = float(np.std(values, ddof=1))
        interval = bootstrap_sigma_interval(
            values,
            seed=int(rng["bootstrap_seed"]) + offset,
            resamples=int(rng["bootstrap_resamples"]),
            quantiles=quantiles,
        )
        statistics[name] = {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "sample_standard_deviation": sample_sigma,
            "sample_quantiles": {
                "q005": float(np.quantile(values, 0.005)),
                "q025": float(np.quantile(values, 0.025)),
                "q160": float(np.quantile(values, 0.16)),
                "q500": float(np.quantile(values, 0.5)),
                "q840": float(np.quantile(values, 0.84)),
                "q975": float(np.quantile(values, 0.975)),
                "q995": float(np.quantile(values, 0.995)),
            },
            "public_center": public_center,
            "public_sigma": public_sigma,
            "median_reference_offset_in_public_sigma": abs(float(np.median(values)) - public_center)
            / public_sigma,
            "sample_to_public_sigma_ratio": sample_sigma / public_sigma,
            "bootstrap_sample_sigma_interval_99_percent": interval,
            "public_sigma_inside_bootstrap_interval": interval[0] <= public_sigma <= interval[1],
        }

    central = controls["central"]
    central_offsets = {
        "Yp_BBN": abs(float(central["Yp_BBN"]) - float(reference["Yp_BBN"]))
        / float(reference["sigma_Yp_BBN"]),
        "D_over_H": abs(float(central["D_over_H"]) - float(reference["D_over_H"]))
        / float(reference["sigma_D_over_H"]),
    }
    by_id = {int(record["draw_id"]): record for record in ordered}
    repeat_rows: list[dict[str, Any]] = []
    maximum_repeat_drift = 0.0
    for repeated in controls["sentinel_repeats"]:
        draw_id = int(repeated["draw_id"])
        original = by_id.get(draw_id)
        if original is None:
            repeat_rows.append({"draw_id": draw_id, "original_success": False})
            maximum_repeat_drift = math.inf
            continue
        yp_drift = relative_drift(float(original["Yp_BBN"]), float(repeated["Yp_BBN"]))
        dh_drift = relative_drift(float(original["D_over_H"]), float(repeated["D_over_H"]))
        maximum_repeat_drift = max(maximum_repeat_drift, yp_drift, dh_drift)
        repeat_rows.append(
            {
                "draw_id": draw_id,
                "original_success": True,
                "input_record_sha256": repeated["input_record_sha256"],
                "repeated_Yp_BBN": float(repeated["Yp_BBN"]),
                "repeated_D_over_H": float(repeated["D_over_H"]),
                "repeated_elapsed_seconds": float(repeated["elapsed_seconds"]),
                "Yp_BBN_relative_drift": yp_drift,
                "D_over_H_relative_drift": dh_drift,
            }
        )

    attempted = len(successes) + len(failures)
    sigma_low, sigma_high = (float(value) for value in acceptance["public_sigma_ratio_interval"])
    checks = {
        "attempted_draw_count_exact": attempted == int(acceptance["expected_attempted_draws"]),
        "minimum_successful_draws_met": len(successes)
        >= int(acceptance["minimum_successful_draws"]),
        "maximum_failure_fraction_met": len(failures) / attempted
        <= float(acceptance["maximum_failure_fraction"]),
        "all_outputs_finite_and_positive": bool(
            len(ordered)
            and np.all(np.isfinite(yp))
            and np.all(np.isfinite(dh))
            and np.all(yp > 0.0)
            and np.all(dh > 0.0)
        ),
        "central_reference_offsets_met": all(
            value <= float(acceptance["maximum_central_reference_offset_in_public_sigma"])
            for value in central_offsets.values()
        ),
        "median_reference_offsets_met": all(
            item["median_reference_offset_in_public_sigma"]
            <= float(acceptance["maximum_median_reference_offset_in_public_sigma"])
            for item in statistics.values()
        ),
        "public_sigma_ratios_met": all(
            sigma_low <= item["sample_to_public_sigma_ratio"] <= sigma_high
            for item in statistics.values()
        ),
        "public_sigmas_inside_bootstrap_intervals": all(
            item["public_sigma_inside_bootstrap_interval"] for item in statistics.values()
        ),
        "sentinel_repeats_met": maximum_repeat_drift
        <= float(acceptance["maximum_repeat_relative_drift"]),
    }
    covariance = np.cov(np.vstack((yp, dh)), ddof=1)
    correlation = np.corrcoef(np.vstack((yp, dh)))
    summary = {
        "schema_version": 1,
        "artifact_id": EXPECTED_PROTOCOL_ID,
        "task_id": EXPECTED_TASK_ID,
        "run_id": run_id,
        "status": "accepted_C0_native_abundance_MC"
        if all(checks.values())
        else "rejected_fail_closed",
        "scientific_boundary": protocol["scientific_boundary"],
        "attempted_draws": attempted,
        "successful_draws": len(successes),
        "failed_draws": len(failures),
        "failure_fraction": len(failures) / attempted,
        "statistics": statistics,
        "joint_abundance_covariance_order": ["Yp_BBN", "D_over_H"],
        "joint_abundance_covariance": covariance.tolist(),
        "joint_abundance_correlation": correlation.tolist(),
        "central_result": central,
        "central_reference_offset_in_public_sigma": central_offsets,
        "sentinel_repeat_results": repeat_rows,
        "maximum_sentinel_repeat_relative_drift": maximum_repeat_drift,
        "acceptance_checks": checks,
        "accepted": all(checks.values()),
    }
    summary["evidence_sha256"] = digest_json(summary)
    return summary


def prepare_run(
    *,
    protocol_path: Path,
    source_root: Path,
    output_dir: Path,
    resume: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    protocol = load_protocol(protocol_path)
    source = validate_source(source_root, protocol)
    environment = validate_environment(protocol)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / OUTPUT_FILENAMES["run_manifest"]
    draw_path = output_dir / OUTPUT_FILENAMES["draw_manifest"]

    if manifest_path.exists():
        if not resume:
            raise RuntimeError("output directory already contains a run; pass --resume")
        allowed_names = set(OUTPUT_FILENAMES.values())
        unexpected = [path.name for path in output_dir.iterdir() if path.name not in allowed_names]
        if unexpected:
            raise RuntimeError(f"resume directory contains unexpected entries: {unexpected}")
        manifest = load_evidence_json(manifest_path, "run manifest")
        draws = load_jsonl(draw_path)
        validate_draw_manifest(draws, protocol)
        if manifest["config_sha256"] != sha256(protocol_path):
            raise RuntimeError("resume protocol digest drift")
        if manifest["source"] != source or manifest["environment"] != environment:
            raise RuntimeError("resume source or environment drift")
        if manifest["draw_manifest_sha256"] != draw_manifest_digest(draws):
            raise RuntimeError("resume draw-manifest digest drift")
        state_path = output_dir / OUTPUT_FILENAMES["state"]
        if not state_path.is_file():
            raise RuntimeError("resume state is missing")
        state = load_evidence_json(state_path, "run state")
        if state.get("run_id") != manifest["run_id"] or state.get(
            "expected_attempted_draws"
        ) != len(draws):
            raise RuntimeError("resume state identity drift")
        successes, failures = terminal_records(output_dir)
        terminal_ids = {int(record["draw_id"]) for record in [*successes, *failures]}
        state_ids = state.get("completed_draw_ids")
        if not isinstance(state_ids, list) or not set(state_ids).issubset(terminal_ids):
            raise RuntimeError("resume state is ahead of durable terminal records")
        summary_path = output_dir / OUTPUT_FILENAMES["summary"]
        if summary_path.exists():
            existing_summary = load_evidence_json(summary_path, "summary")
            if existing_summary.get("run_id") != manifest["run_id"]:
                raise RuntimeError("resume summary identity drift")
        return protocol, draws, manifest["run_id"]

    unexpected = [path for path in output_dir.iterdir()]
    if unexpected:
        raise RuntimeError("non-empty output directory lacks a valid run manifest")
    draws = generate_draw_manifest(protocol)
    validate_draw_manifest(draws, protocol)
    write_draw_manifest(draw_path, draws)
    draw_digest = draw_manifest_digest(draws)
    run_id = digest_json(
        {
            "protocol_sha256": sha256(protocol_path),
            "source_revision": source["revision"],
            "draw_manifest_sha256": draw_digest,
        }
    )
    manifest = {
        "schema_version": 1,
        "protocol_id": EXPECTED_PROTOCOL_ID,
        "task_id": EXPECTED_TASK_ID,
        "run_id": run_id,
        "config_path": str(protocol_path),
        "config_sha256": sha256(protocol_path),
        "source": source,
        "environment": environment,
        "draw_manifest_sha256": draw_digest,
        "output_files": OUTPUT_FILENAMES,
        "created_at_utc": utc_now(),
    }
    manifest["evidence_sha256"] = digest_json(manifest)
    atomic_json(manifest_path, manifest)
    (output_dir / OUTPUT_FILENAMES["results"]).touch(exist_ok=False)
    (output_dir / OUTPUT_FILENAMES["failures"]).touch(exist_ok=False)
    write_state(
        output_dir,
        run_id=run_id,
        expected=len(draws),
        successes=[],
        failures=[],
        status="initialized",
    )
    return protocol, draws, run_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    protocol_path = args.protocol.resolve()
    source_root = args.source_root.resolve()
    output_dir = args.output_dir.resolve()
    protocol, draws, run_id = prepare_run(
        protocol_path=protocol_path,
        source_root=source_root,
        output_dir=output_dir,
        resume=args.resume,
    )
    default_workers = int(protocol["execution"]["default_workers"])
    workers = default_workers if args.workers is None else args.workers
    maximum_workers = int(protocol["execution"]["maximum_workers"])
    if workers < 1 or workers > maximum_workers:
        raise ValueError(f"workers must be in [1, {maximum_workers}]")
    for key, value in THREAD_ENVIRONMENT.items():
        os.environ[key] = value

    successes, failures = execute_pending(
        source_root=source_root,
        output_dir=output_dir,
        run_id=run_id,
        draws=draws,
        workers=workers,
    )
    controls = run_controls(
        source_root,
        draws,
        [int(value) for value in protocol["execution"]["sentinel_repeat_draw_indices"]],
        workers,
        protocol,
    )
    summary = build_summary(
        protocol=protocol,
        run_id=run_id,
        successes=successes,
        failures=failures,
        controls=controls,
    )
    atomic_json(output_dir / OUTPUT_FILENAMES["summary"], summary)
    write_state(
        output_dir,
        run_id=run_id,
        expected=len(draws),
        successes=successes,
        failures=failures,
        status="accepted" if summary["accepted"] else "rejected",
    )
    print(f"METRIC successful_draws={len(successes)}", flush=True)
    print(f"METRIC failed_draws={len(failures)}", flush=True)
    print(f"METRIC accepted={int(summary['accepted'])}", flush=True)
    print(json.dumps(summary["acceptance_checks"], indent=2, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
