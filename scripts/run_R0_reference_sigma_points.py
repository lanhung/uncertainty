#!/usr/bin/env python3
"""Run the frozen nine-point Stage-R0 reference-prior solver smoke."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import platform
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.R0_reference_adapter import (  # noqa: E402
    REACTIONS,
    curve_manifest,
    digest_json,
    install_prymordial_arrays,
    linx_q_vector,
    load_etr25_rows,
    patch_linx_network,
    prymordial_constructor_args,
    restore_prymordial_arrays,
    sha256,
    tau_n_seconds,
    validate_protocol,
    validate_source_revision,
)
from scripts.run_linx_native_q_reproduction import extract_batch  # noqa: E402
from scripts.why_not_benchmark import (  # noqa: E402
    load_linx,
    load_prymordial,
    load_yaml,
    prymordial_abundances,
)


ARTIFACT_ID = "R0-REFERENCE-SIGMA-POINTS-v1"
REPRESENTATION = "R0_P0_ETR25_scalar_lognormal"
PRYMORDIAL_RATE_NAMES = (
    "npdg",
    "dpHe3g",
    "ddHe3n",
    "ddtp",
    "tpag",
    "tdan",
    "taLi7g",
    "He3ntp",
    "He3dap",
    "He3aBe7g",
    "Be7nLi7p",
    "Li7paa",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, allow_nan=False) + "\n")


def project_revision() -> str:
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def node_records(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"node_id": str(node["id"]), "q": [float(value) for value in node["q"]]}
        for node in protocol["sigma_point_design"]["nodes"]
    ]


def curve_records(
    rows: dict[str, list[dict[str, Any]]],
    nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {node["node_id"]: curve_manifest(rows, REPRESENTATION, node["q"][:3]) for node in nodes}


def source_manifest(
    *,
    protocol_path: Path,
    protocol: dict[str, Any],
    solver: str,
    source_dir: Path,
    inventory: Path | None,
) -> dict[str, Any]:
    solver_contract = protocol["solver_paths"][solver]
    return {
        "artifact_id": ARTIFACT_ID,
        "claim_boundary": protocol["claim_boundary"],
        "config": str(protocol_path),
        "config_sha256": sha256(protocol_path),
        "environment": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "generated_at_utc": utc_now(),
        "inventory": str(inventory) if inventory else None,
        "project_revision": project_revision(),
        "protocol_id": protocol["protocol_id"],
        "representation": REPRESENTATION,
        "solver": solver,
        "solver_revision": solver_contract["revision"],
        "source_dir": str(source_dir),
        "tasks": protocol["tasks"],
    }


def linx_reverse_audit(
    modules: dict[str, Any],
    rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    jax = modules["jax"]
    records: dict[str, Any] = {}
    for target_index, specification in enumerate(REACTIONS):
        maximum = 0.0
        defined = 0
        for q in (-1.0, 1.0):
            reaction_q = [0.0] * len(REACTIONS)
            reaction_q[target_index] = q
            network = patch_linx_network(modules, rows, REPRESENTATION, reaction_q)
            reaction = next(
                candidate
                for candidate in network.reactions
                if candidate.name == specification.native_id
            )
            for source in rows[specification.canonical_id]:
                t9 = float(source["T9"])
                forward = float(jax.device_get(reaction.frwrd_rate_param(t9 * 1.0e9, q)))
                reverse = float(jax.device_get(reaction.bkwrd_rate_param(t9 * 1.0e9, q)))
                expected = (
                    float(reaction.alpha)
                    * t9 ** float(reaction.beta)
                    * math.exp(float(reaction.gamma) / t9)
                    * forward
                )
                if (
                    math.isfinite(expected)
                    and math.isfinite(reverse)
                    and expected > sys.float_info.min
                    and reverse > sys.float_info.min
                ):
                    defined += 1
                    maximum = max(maximum, abs(reverse / expected - 1.0))
        records[specification.canonical_id] = {
            "defined_rows": defined,
            "maximum_relative_error": maximum,
            "same_perturbed_forward_used_by_reverse": True,
        }
    return records


def run_linx(
    *,
    protocol: dict[str, Any],
    source_dir: Path,
    rows: dict[str, list[dict[str, Any]]],
    nodes: list[dict[str, Any]],
    timings_path: Path,
    failures_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    os.environ.setdefault("JAX_ENABLE_X64", "True")
    import numpy as np

    imported_at = time.perf_counter()
    modules, provenance = load_linx(source_dir)
    import_seconds = time.perf_counter() - imported_at
    jax = modules["jax"]
    jnp = modules["jnp"]
    const = modules["const"]
    if not bool(jax.config.x64_enabled):
        raise RuntimeError("LINX fast-track run requires JAX x64")

    numerical = protocol["solver_paths"]["LINX"]["numerical"]
    fiducial = protocol["fiducial"]
    background_model = modules["BackgroundModel"]()
    background_started = time.perf_counter()
    background = background_model(jnp.asarray(float(fiducial["delta_neff"])))
    jax.block_until_ready(background)
    background_seconds = time.perf_counter() - background_started
    t_vec, a_vec, rho_g, rho_nu, rho_np, pressure_np, neff_vec = background
    neff = float(jax.device_get(neff_vec[-1]))

    # P0 uses the same median and factor-uncertainty arrays for every q sign.
    network = patch_linx_network(
        modules,
        rows,
        REPRESENTATION,
        [0.0] * len(REACTIONS),
    )
    abundance_model = modules["AbundanceModel"](network)
    q_matrix = jnp.asarray(
        [linx_q_vector(node["q"][:3]) for node in nodes],
        dtype=jnp.float64,
    )
    tau = jnp.asarray(
        [tau_n_seconds(fiducial, node["q"][3]) / float(const.tau_n) for node in nodes],
        dtype=jnp.float64,
    )
    eta = jnp.asarray(
        [float(fiducial["omega_b_h2"]) / float(const.Omegabh2)] * len(nodes),
        dtype=jnp.float64,
    )

    def solve_member(q_vector: Any, tau_fac: Any, eta_fac: Any) -> Any:
        return abundance_model(
            rho_g,
            rho_nu,
            rho_np,
            pressure_np,
            t_vec=t_vec,
            a_vec=a_vec,
            eta_fac=eta_fac,
            tau_n_fac=tau_fac,
            nuclear_rates_q=q_vector,
            rtol=float(numerical["rtol"]),
            atol=float(numerical["atol"]),
            sampling_nTOp=int(numerical["sampling_nTOp"]),
            max_steps=int(numerical["max_steps"]),
        )

    solve_batch = jax.jit(jax.vmap(solve_member, in_axes=(0, 0, 0)))
    result_rows: list[dict[str, Any]] = []
    for repetition in range(2):
        started = time.perf_counter()
        try:
            raw = solve_batch(q_matrix, tau, eta)
            jax.block_until_ready(raw)
            values = extract_batch(raw, len(nodes), neff, jax, np)
            for node, output in zip(nodes, values):
                result_rows.append(
                    {
                        "node_id": node["node_id"],
                        "outputs": {
                            key: float(output[key])
                            for key in ("Neff", "YPBBN", "DoH", "He3oH", "Li7oH")
                        },
                        "q": node["q"],
                        "repetition": repetition,
                        "status": "ok",
                        "tau_n_seconds": tau_n_seconds(fiducial, node["q"][3]),
                    }
                )
            status = "ok"
        except Exception as error:  # pragma: no cover - worker boundary
            status = "failed"
            append_jsonl(
                failures_path,
                {
                    "error": repr(error),
                    "kind": "LINX_batch_exception",
                    "repetition": repetition,
                    "traceback": traceback.format_exc(),
                },
            )
        elapsed = time.perf_counter() - started
        append_jsonl(
            timings_path,
            {
                "batch_size": len(nodes),
                "elapsed_seconds": elapsed,
                "kind": "cold_compile_and_solve" if repetition == 0 else "warm_repeat",
                "repetition": repetition,
                "status": status,
            },
        )
        print(f"SIGMA_PROGRESS {min(repetition + 1, 1) * len(nodes)}/{len(nodes)}", flush=True)

    reverse = linx_reverse_audit(modules, rows)
    accounting = {
        "background_seconds": background_seconds,
        "import_seconds": import_seconds,
        "jax": jax.__version__,
        "jax_backend": jax.default_backend(),
        "numpy": importlib.metadata.version("numpy"),
    }
    return result_rows, reverse, {"load_provenance": provenance, **accounting}


def configure_prymordial(
    config: Any,
    *,
    fiducial: dict[str, Any],
    node: dict[str, Any],
) -> None:
    config.Omegabh2 = float(fiducial["omega_b_h2"])
    config.eta0b = config.Omegabh2_to_eta0b * config.Omegabh2
    config.DeltaNeff = float(fiducial["delta_neff"])
    config.tau_n = tau_n_seconds(fiducial, node["q"][3]) * config.second
    config.aTid_flag = True
    config.compute_bckg_flag = True
    config.compute_nTOp_flag = True
    config.compute_nTOp_thermal_flag = False
    config.save_bckg_flag = False
    config.save_nTOp_flag = False
    config.save_nTOp_thermal_flag = False
    config.smallnet_flag = True
    config.nacreii_flag = False
    config.rates_dir = "key_primat_rates/"
    config.julia_flag = False
    config.verbose_flag = False
    config.NP_nuclear_flag = False
    config.NP_nTOp_flag = False
    config.NP_delta_nTOp = 0.0
    for native_id, q in zip(PRYMORDIAL_RATE_NAMES, prymordial_constructor_args(node["q"][:3])):
        setattr(config, f"p_{native_id}", float(q))
        setattr(config, f"NP_delta_{native_id}", 0.0)


def run_prymordial(
    *,
    source_dir: Path,
    protocol: dict[str, Any],
    rows: dict[str, list[dict[str, Any]]],
    nodes: list[dict[str, Any]],
    timings_path: Path,
    failures_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    imported_at = time.perf_counter()
    config, solver_class, provenance = load_prymordial(source_dir)
    import_seconds = time.perf_counter() - imported_at
    fiducial = protocol["fiducial"]
    repeated = set(protocol["sigma_point_design"]["repeated_nodes"])
    result_rows: list[dict[str, Any]] = []
    saved: dict[str, Any] = {}
    try:
        # Load the selected native family once, then replace only the three
        # project-owned R0 arrays before each solver-class construction.
        configure_prymordial(config, fiducial=fiducial, node=nodes[0])
        config.ReloadKeyRates()
        for node in nodes:
            repetitions = 2 if node["node_id"] in repeated else 1
            for repetition in range(repetitions):
                configure_prymordial(config, fiducial=fiducial, node=node)
                saved = install_prymordial_arrays(
                    config,
                    rows,
                    REPRESENTATION,
                    node["q"][:3],
                )
                started = time.perf_counter()
                try:
                    raw = solver_class().PRyMresults().tolist()
                    output = prymordial_abundances(raw)
                    result_rows.append(
                        {
                            "node_id": node["node_id"],
                            "outputs": {
                                key: float(output[key])
                                for key in ("Neff", "YPBBN", "DoH", "He3oH", "Li7oH")
                            },
                            "q": node["q"],
                            "repetition": repetition,
                            "status": "ok",
                            "tau_n_seconds": tau_n_seconds(fiducial, node["q"][3]),
                        }
                    )
                    status = "ok"
                except Exception as error:  # pragma: no cover - worker boundary
                    status = "failed"
                    append_jsonl(
                        failures_path,
                        {
                            "error": repr(error),
                            "kind": "PRyMordial_scalar_exception",
                            "node_id": node["node_id"],
                            "repetition": repetition,
                            "traceback": traceback.format_exc(),
                        },
                    )
                finally:
                    restore_prymordial_arrays(config, saved)
                    saved = {}
                append_jsonl(
                    timings_path,
                    {
                        "batch_size": 1,
                        "elapsed_seconds": time.perf_counter() - started,
                        "kind": "scalar_solve",
                        "node_id": node["node_id"],
                        "repetition": repetition,
                        "status": status,
                    },
                )
            print(f"SIGMA_PROGRESS {len({row['node_id'] for row in result_rows})}/9", flush=True)
    finally:
        if saved:
            restore_prymordial_arrays(config, saved)

    # PRyMordial's accepted mapping regression already establishes the exact
    # same-forward detailed-balance contract for the injected array interface.
    reverse = {
        reaction.canonical_id: {
            "mapping_evidence": (
                "artifacts/priors/PRYMORDIAL-R0-MAPPING-REGRESSION-v1/regression.json"
            ),
            "same_perturbed_forward_used_by_reverse": True,
        }
        for reaction in REACTIONS
    }
    return (
        result_rows,
        reverse,
        {
            "import_seconds": import_seconds,
            "load_provenance": provenance,
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", choices=("LINX", "PRyMordial"), required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/benchmarks/R0_reference_fast_track_v1.yaml"),
    )
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--yaml-python", type=Path)
    args = parser.parse_args()

    protocol, yaml_loader = load_yaml(args.config, args.yaml_python)
    validate_protocol(protocol, ROOT)
    validate_source_revision(
        args.source_dir,
        protocol["solver_paths"][args.solver]["revision"],
    )
    if args.inventory is not None and not args.inventory.is_file():
        raise FileNotFoundError(args.inventory)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    timings_path = args.output_dir / "timings.jsonl"
    failures_path = args.output_dir / "failures.jsonl"
    timings_path.touch()
    failures_path.touch()
    rows = load_etr25_rows(ROOT / protocol["frozen_inputs"]["ETR25_tables"]["path"])
    nodes = node_records(protocol)
    curves = curve_records(rows, nodes)
    manifest = source_manifest(
        protocol_path=args.config,
        protocol=protocol,
        solver=args.solver,
        source_dir=args.source_dir,
        inventory=args.inventory,
    )
    manifest["yaml_loader"] = yaml_loader
    write_json(args.output_dir / "run_manifest.json", manifest)
    write_json(args.output_dir / "curve_manifest.json", curves)

    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    if args.solver == "LINX":
        results, reverse, environment = run_linx(
            protocol=protocol,
            source_dir=args.source_dir,
            rows=rows,
            nodes=nodes,
            timings_path=timings_path,
            failures_path=failures_path,
        )
    else:
        results, reverse, environment = run_prymordial(
            source_dir=args.source_dir,
            protocol=protocol,
            rows=rows,
            nodes=nodes,
            timings_path=timings_path,
            failures_path=failures_path,
        )
    payload = {
        "artifact_id": ARTIFACT_ID,
        "claim_boundary": protocol["claim_boundary"],
        "curve_manifest_sha256": sha256(args.output_dir / "curve_manifest.json"),
        "environment": environment,
        "failure_count": len(failures_path.read_text(encoding="utf-8").splitlines()),
        "finished_at_utc": utc_now(),
        "representation": REPRESENTATION,
        "results": results,
        "reverse_rate_audit": reverse,
        "schema_version": 1,
        "solver": args.solver,
        "task_ids": list(protocol["tasks"].values()),
        "timing": {
            "cpu_seconds": time.process_time() - cpu_started,
            "wall_seconds": time.perf_counter() - wall_started,
        },
    }
    payload["evidence_sha256"] = digest_json(payload)
    write_json(args.output_dir / "results.json", payload)
    print(
        json.dumps(
            {
                "evidence_sha256": payload["evidence_sha256"],
                "failure_count": payload["failure_count"],
                "output": str(args.output_dir),
                "solver": args.solver,
                "unique_nodes": len({row["node_id"] for row in results}),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
