#!/usr/bin/env python3
"""Run the frozen ABCMB full-component spectra audit safely.

The harness deliberately implements the spectra stage first. Gradient, toy
Fisher, synthetic-recovery, and HMC/NUTS claims are emitted as structured
``not_run`` components until dedicated implementations satisfy the frozen
protocol. A completed S0 result is required before any lmax=2500 case.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
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


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs/benchmarks/abcmb_full_component_audit_v1.yaml"
REQUIRED_ARTIFACTS = (
    "run_manifest.json",
    "results.json",
    "failures.jsonl",
    "resource_report.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def load_yaml(path: Path, yaml_python: Path | None) -> tuple[dict[str, Any], str]:
    try:
        import yaml
    except ModuleNotFoundError:
        if yaml_python is None:
            raise RuntimeError(
                "PyYAML is absent; pass --yaml-python pointing to an isolated Python with PyYAML"
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


def git_revision(source_dir: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip()


def git_tree_revision(source_dir: Path, tree_path: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_dir), "rev-parse", f"HEAD:{tree_path}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip()


def validate_protocol(protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if protocol.get("schema_version") != 1:
        raise ValueError("unsupported ABCMB audit schema")
    if protocol.get("audit_id") != "ABCMB-FULL-COMPONENT-AUDIT-v1":
        raise ValueError("unexpected ABCMB audit id")
    if protocol.get("status") != "protocol_frozen_measurements_pending":
        raise ValueError("ABCMB audit protocol is not frozen for measurement")
    if protocol.get("backend") != "jax_cpu" or protocol.get("precision") != "float64":
        raise ValueError("this harness supports only the frozen float64 JAX CPU contract")

    cases = protocol.get("spectra_cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("spectra_cases must be a non-empty list")
    by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in by_id:
            raise ValueError("every spectra case needs a unique non-empty id")
        if case.get("bbn_type") not in {"Table", "linx"}:
            raise ValueError(f"unsupported bbn_type for {case_id}")
        if not isinstance(case.get("lmax"), int) or int(case["lmax"]) < 2:
            raise ValueError(f"invalid lmax for {case_id}")
        if not isinstance(case.get("lensing"), bool):
            raise ValueError(f"invalid lensing flag for {case_id}")
        if case["bbn_type"] == "linx":
            if case.get("linx_reaction_net") != "key_PRIMAT_2023":
                raise ValueError(f"unapproved LINX network for {case_id}")
            if case.get("nuclear_rates_q") != "all_zero":
                raise ValueError(f"only all-zero technical rates are allowed for {case_id}")
        by_id[case_id] = case

    repetitions = protocol.get("spectra_repetitions", {})
    if repetitions.get("cold") != 1 or int(repetitions.get("warm", 0)) < 1:
        raise ValueError("spectra repetitions require one cold and at least one warm solve")
    if protocol.get("resource_limits", {}).get("dry_run_case") not in by_id:
        raise ValueError("dry-run case is absent from spectra_cases")
    if protocol.get("spectra_outputs") != ["ClTT", "ClTE", "ClEE", "Pk", "YHe", "Neff"]:
        raise ValueError("unexpected spectra output contract")
    return by_id


def prepare_output_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {path}")
    path.mkdir(parents=True, exist_ok=True)


def installed_abcmb_provenance(expected_revision: str) -> dict[str, str]:
    distribution = importlib.metadata.distribution("ABCMB")
    direct_url_text = distribution.read_text("direct_url.json")
    if not direct_url_text:
        raise RuntimeError("installed ABCMB lacks direct_url.json source provenance")
    direct_url = json.loads(direct_url_text)
    commit = direct_url.get("vcs_info", {}).get("commit_id")
    if commit != expected_revision:
        raise RuntimeError(
            f"installed ABCMB commit {commit!r} does not match frozen {expected_revision!r}"
        )
    return {
        "distribution_version": distribution.version,
        "installed_commit": commit,
        "direct_url": str(direct_url.get("url", "")),
    }


def preflight_checks(
    protocol: dict[str, Any], source_dir: Path, environment_lock: Path
) -> dict[str, Any]:
    source_revision = git_revision(source_dir)
    bundled_tree = git_tree_revision(source_dir, "abcmb/linx")
    if source_revision != protocol["source_revision"]:
        raise RuntimeError(
            f"ABCMB source revision {source_revision} != frozen {protocol['source_revision']}"
        )
    if bundled_tree != protocol["bundled_linx_tree"]:
        raise RuntimeError(
            f"ABCMB bundled LINX tree {bundled_tree} != frozen {protocol['bundled_linx_tree']}"
        )
    if not (source_dir / "abcmb/main.py").is_file():
        raise FileNotFoundError("ABCMB source is missing abcmb/main.py")
    if not environment_lock.is_file():
        raise FileNotFoundError(f"environment lock is absent: {environment_lock}")
    package = installed_abcmb_provenance(protocol["source_revision"])
    return {
        "status": "passed",
        "source_revision": source_revision,
        "bundled_linx_tree": bundled_tree,
        "environment_lock": str(environment_lock),
        "environment_lock_sha256": sha256(environment_lock),
        "package": package,
        "python": sys.version,
        "platform": platform.platform(),
    }


def _array_summary(value: Any) -> tuple[Any, dict[str, Any]]:
    import numpy as np

    array = np.asarray(value)
    finite = np.isfinite(array)
    summary: dict[str, Any] = {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "size": int(array.size),
        "finite_count": int(finite.sum()),
        "all_finite": bool(finite.all()),
    }
    if array.size:
        summary.update(
            {
                "minimum": float(array.min()),
                "maximum": float(array.max()),
                "maximum_absolute": float(np.max(np.abs(array))),
            }
        )
    return array, summary


def evaluate_spectra_outputs(
    reference: dict[str, Any],
    repeats: list[dict[str, Any]],
    case: dict[str, Any],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    import numpy as np

    summaries: dict[str, Any] = {}
    arrays: dict[str, Any] = {}
    for name, value in reference.items():
        arrays[name], summaries[name] = _array_summary(value)

    expected_ell_count = int(case["lmax"]) - 1
    shape_ok = all(
        summaries[name]["shape"] == [expected_ell_count] for name in ("ClTT", "ClTE", "ClEE")
    )
    shape_ok = shape_ok and summaries["Pk"]["size"] > 0
    shape_ok = shape_ok and summaries["YHe"]["shape"] == [] and summaries["Neff"]["shape"] == []
    all_finite = all(item["all_finite"] for item in summaries.values())

    negative_ratios: dict[str, float] = {}
    negative_limit = float(acceptance["maximum_negative_noise_fraction_of_maximum"])
    negativity_ok = True
    for name in ("ClTT", "ClEE", "Pk"):
        array = arrays[name]
        maximum_absolute = max(float(np.max(np.abs(array))), np.finfo(float).tiny)
        ratio = max(0.0, -float(np.min(array))) / maximum_absolute
        negative_ratios[name] = ratio
        negativity_ok = negativity_ok and ratio <= negative_limit

    drift_by_repeat: list[dict[str, float]] = []
    maximum_drift = 0.0
    for repeat in repeats:
        repeat_drift: dict[str, float] = {}
        for name, reference_array in arrays.items():
            comparison = np.asarray(repeat[name])
            denominator = max(float(np.max(np.abs(reference_array))), np.finfo(float).tiny)
            drift = float(np.max(np.abs(comparison - reference_array))) / denominator
            repeat_drift[name] = drift
            maximum_drift = max(maximum_drift, drift)
        drift_by_repeat.append(repeat_drift)

    drift_ok = maximum_drift <= float(acceptance["maximum_relative_repeat_drift"])
    accepted = all_finite and shape_ok and negativity_ok and drift_ok
    return {
        "accepted": accepted,
        "all_finite": all_finite,
        "expected_shapes": shape_ok,
        "negative_noise_fraction_of_maximum": negative_ratios,
        "negative_noise_accepted": negativity_ok,
        "maximum_relative_repeat_drift": maximum_drift,
        "repeat_drift_accepted": drift_ok,
        "drift_by_repeat": drift_by_repeat,
        "summaries": summaries,
    }


def run_spectra_case(
    protocol: dict[str, Any],
    case: dict[str, Any],
    source_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    # These settings precede the first JAX/ABCMB import in this process.
    os.environ["JAX_PLATFORM_NAME"] = "cpu"
    os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
    sys.path.insert(0, str(source_dir))

    import jax
    import numpy as np

    jax.config.update("jax_enable_x64", True)
    from abcmb.main import Model

    if not jax.config.jax_enable_x64:
        raise RuntimeError("ABCMB audit requires JAX x64 mode")
    devices = [str(device) for device in jax.devices()]
    if any(getattr(device, "platform", "") != "cpu" for device in jax.devices()):
        raise RuntimeError(f"frozen audit requires CPU-only JAX devices, received {devices}")

    model_options: dict[str, Any] = {
        "bbn_type": case["bbn_type"],
        "l_min": 2,
        "l_max": int(case["lmax"]),
        "lensing": bool(case["lensing"]),
    }
    if case["bbn_type"] == "linx":
        model_options["linx_reaction_net"] = case["linx_reaction_net"]

    model = Model(**model_options)
    params: dict[str, Any] = {}
    if case["bbn_type"] == "linx":
        params["nuclear_rates_q"] = np.zeros(len(model.abundanceModel.nuclear_net.reactions))

    def solve() -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        output = model(params)
        jax.block_until_ready(output.ClTT)
        elapsed = time.perf_counter() - started
        values = {
            "ClTT": np.asarray(output.ClTT),
            "ClTE": np.asarray(output.ClTE),
            "ClEE": np.asarray(output.ClEE),
            "Pk": np.asarray(output.Pk),
            "YHe": np.asarray(output.params["YHe"]),
            "Neff": np.asarray(output.params["Neff"]),
        }
        return values, elapsed

    reference, cold_seconds = solve()
    warm_outputs: list[dict[str, Any]] = []
    warm_seconds: list[float] = []
    for _ in range(int(protocol["spectra_repetitions"]["warm"])):
        values, elapsed = solve()
        warm_outputs.append(values)
        warm_seconds.append(elapsed)

    evaluation = evaluate_spectra_outputs(
        reference,
        warm_outputs,
        case,
        protocol["spectra_acceptance"],
    )
    arrays_path = output_dir / f"{case['id']}_spectra.npz"
    np.savez_compressed(arrays_path, **reference)
    return {
        "case_id": case["id"],
        "status": "accepted" if evaluation["accepted"] else "not_accepted",
        "case": case,
        "backend": "cpu",
        "devices": devices,
        "jax_version": jax.__version__,
        "jax_x64": bool(jax.config.jax_enable_x64),
        "cold_seconds": cold_seconds,
        "warm_seconds": warm_seconds,
        "evaluation": evaluation,
        "spectra_archive": arrays_path.name,
        "spectra_archive_sha256": sha256(arrays_path),
    }


def validate_dry_run_evidence(
    evidence_path: Path,
    protocol: dict[str, Any],
    config_hash: str,
) -> dict[str, Any]:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("audit_id") != protocol["audit_id"]:
        raise ValueError("dry-run evidence belongs to another audit")
    if evidence.get("config_sha256") != config_hash:
        raise ValueError("dry-run evidence was generated from a different config")
    if evidence.get("source_revision") != protocol["source_revision"]:
        raise ValueError("dry-run evidence used a different ABCMB source")
    expected_case = protocol["resource_limits"]["dry_run_case"]
    matches = [case for case in evidence.get("spectra", []) if case.get("case_id") == expected_case]
    if len(matches) != 1 or matches[0].get("status") != "accepted":
        raise ValueError("dry-run evidence does not contain one accepted S0 case")
    return {
        "path": str(evidence_path),
        "sha256": sha256(evidence_path),
        "case_id": expected_case,
    }


def component_statuses(spectra_executed: bool) -> dict[str, dict[str, str]]:
    return {
        "spectra": {
            "status": "evaluated" if spectra_executed else "not_run",
            "reason": "selected frozen spectra cases" if spectra_executed else "preflight_only",
        },
        "gradient": {
            "status": "not_run",
            "reason": "gradient stage is not implemented in this spectra-first harness",
        },
        "toy_fisher": {
            "status": "not_run",
            "reason": "toy Fisher stage awaits accepted gradient evidence",
        },
        "synthetic_recovery": {
            "status": "not_run",
            "reason": "Asimov recovery stage awaits accepted spectra and Fisher evidence",
        },
        "hmc_nuts": {
            "status": "not_run",
            "reason": "the frozen exact environment has no registered likelihood or sampler",
        },
    }


def spectra_component_complete(
    selected_case_ids: list[str],
    cases_by_id: dict[str, dict[str, Any]],
    spectra_results: list[dict[str, Any]],
) -> bool:
    return (
        set(selected_case_ids) == set(cases_by_id)
        and len(spectra_results) == len(cases_by_id)
        and all(item.get("status") == "accepted" for item in spectra_results)
    )


def resource_report(started_wall: float, started_cpu: float, status: str) -> dict[str, Any]:
    wall_seconds = time.perf_counter() - started_wall
    cpu_seconds = time.process_time() - started_cpu
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "status": status,
        "node": socket.gethostname(),
        "wall_seconds": wall_seconds,
        "worker_hours": wall_seconds / 3600.0,
        "process_cpu_seconds": cpu_seconds,
        "cpu_core_hours": cpu_seconds / 3600.0,
        "gpu_hours": 0.0,
        "monetary_cost_cny": None,
        "max_rss_bytes": usage.ru_maxrss * 1024,
        "cost_note": "node price is not part of this frozen component protocol",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--yaml-python", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument(
        "--dry-run-evidence",
        type=Path,
        help="results.json from an accepted S0 run; required before any lmax=2500 case",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    config_path = args.config.resolve()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    prepare_output_dir(output_dir)
    failures_path = output_dir / "failures.jsonl"
    failures_path.touch()

    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at_utc": utc_now(),
        "status": "in_progress",
        "config": str(config_path),
        "source_dir": str(source_dir),
        "preflight_only": bool(args.preflight),
        "selected_cases": args.cases or [],
    }
    results: dict[str, Any] = {"run_id": run_id, "status": "in_progress"}
    status = "failed"
    try:
        protocol, yaml_loader = load_yaml(config_path, args.yaml_python)
        cases_by_id = validate_protocol(protocol)
        config_hash = sha256(config_path)
        # Frozen paths are repository-relative.  Resolve them from the selected
        # config rather than from this script so that a reviewed harness can be
        # copied to /tmp for a remote preflight without changing provenance.
        config_repository_root = config_path.parents[2]
        environment_lock = config_repository_root / protocol["environment_lock"]
        manifest.update(
            {
                "audit_id": protocol["audit_id"],
                "task_id": protocol["task_id"],
                "execution_task_id": protocol["execution_task_id"],
                "config_sha256": config_hash,
                "environment_lock": protocol["environment_lock"],
                "environment_lock_sha256": sha256(environment_lock),
                "source_revision": protocol["source_revision"],
                "bundled_linx_tree": protocol["bundled_linx_tree"],
                "yaml_loader": yaml_loader,
                "scientific_boundary": protocol["scientific_boundary"],
                "prohibited_current_claims": protocol["prohibited_current_claims"],
            }
        )
        preflight = preflight_checks(protocol, source_dir, environment_lock)
        results.update(
            {
                "audit_id": protocol["audit_id"],
                "config_sha256": config_hash,
                "source_revision": protocol["source_revision"],
                "preflight": preflight,
                "scientific_boundary": protocol["scientific_boundary"],
                "prohibited_current_claims": protocol["prohibited_current_claims"],
            }
        )

        if args.preflight:
            if args.cases or args.dry_run_evidence:
                raise ValueError("--preflight cannot be combined with --case or --dry-run-evidence")
            results["spectra"] = []
            results["components"] = component_statuses(False)
            status = "preflight_complete"
        else:
            selected_case_ids = args.cases or [protocol["resource_limits"]["dry_run_case"]]
            manifest["selected_cases"] = selected_case_ids
            if len(selected_case_ids) != len(set(selected_case_ids)):
                raise ValueError("duplicate --case selections are not allowed")
            unknown = sorted(set(selected_case_ids) - set(cases_by_id))
            if unknown:
                raise ValueError(f"unknown spectra cases: {unknown}")
            dry_run_id = protocol["resource_limits"]["dry_run_case"]
            needs_evidence = any(
                int(cases_by_id[item]["lmax"]) >= 2500 for item in selected_case_ids
            )
            dry_run_evidence = None
            if needs_evidence and dry_run_id not in selected_case_ids:
                if args.dry_run_evidence is None:
                    raise ValueError(
                        "lmax=2500 cases require --dry-run-evidence from an accepted S0 run"
                    )
                dry_run_evidence = validate_dry_run_evidence(
                    args.dry_run_evidence.resolve(), protocol, config_hash
                )
            elif args.dry_run_evidence is not None:
                dry_run_evidence = validate_dry_run_evidence(
                    args.dry_run_evidence.resolve(), protocol, config_hash
                )

            spectra_results = []
            for case_id in selected_case_ids:
                case_result = run_spectra_case(
                    protocol, cases_by_id[case_id], source_dir, output_dir
                )
                spectra_results.append(case_result)
                if case_result["status"] != "accepted":
                    append_jsonl(
                        failures_path,
                        {
                            "case_id": case_id,
                            "kind": "spectra_acceptance_failure",
                            "recorded_at_utc": utc_now(),
                            "evaluation": case_result["evaluation"],
                        },
                    )
                    break

            complete_spectra = spectra_component_complete(
                selected_case_ids, cases_by_id, spectra_results
            )
            results["spectra"] = spectra_results
            results["dry_run_evidence"] = dry_run_evidence
            results["components"] = component_statuses(complete_spectra)
            accepted = len(spectra_results) == len(selected_case_ids) and all(
                item["status"] == "accepted" for item in spectra_results
            )
            if complete_spectra:
                print("PROGRESS 1/4", flush=True)
            status = "complete_accepted" if accepted else "complete_not_accepted"
    except Exception as error:  # preserve structured evidence for every failure
        append_jsonl(
            failures_path,
            {
                "kind": "exception",
                "recorded_at_utc": utc_now(),
                "exception_type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        results["exception"] = {"type": type(error).__name__, "message": str(error)}
        results.setdefault("components", component_statuses(False))
        status = "failed"
    finally:
        finished_at = utc_now()
        manifest["status"] = status
        manifest["finished_at_utc"] = finished_at
        results["status"] = status
        results["finished_at_utc"] = finished_at
        json_dump(output_dir / "run_manifest.json", manifest)
        json_dump(output_dir / "results.json", results)
        json_dump(
            output_dir / "resource_report.json",
            resource_report(started_wall, started_cpu, status),
        )

    return 0 if status in {"preflight_complete", "complete_accepted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
