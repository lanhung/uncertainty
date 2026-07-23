#!/usr/bin/env python3
"""Reproduce the published PRyMordial R0 sensitivity-atlas slice."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


EXPECTED_PRYM_REVISION = "725d8a8db3ad5ea2630580d825c9d0d69ed76533"
EXPECTED_ATLAS_REVISION = "d3ea1838d9450673698f07b7c6b8971efb87d0fd"
EXPECTED_PRYM_FILES = {
    "PRyM/PRyM_init.py": "7b52cdd4cf7a7c39082d6cdf4a2e4f3b67458dc20d6ff9f07c2b488ef1819e2f",
    "PRyM/PRyM_main.py": "98f0724f27ace2927d38c3eec615def05bfbfd9c1c9cc09cfa91470417b3451f",
    "PRyM/PRyM_nuclear_net63.py": "dfc634de131e740810f3e2992649f82747173495b2c8e6e0f849a69b1f6da577",
}
EXPECTED_ATLAS_TABLE = "Sensitivity_Summary_Tables/Tau_n_Weak_Norm_Sensitivity_Summary_Table.pdf"
EXPECTED_ATLAS_TABLE_SHA256 = "bf7bd5bcb1753a7e805837e18460b85d3af06fa4fdaf0d5f96b4eee7bff0f035"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--atlas-root", required=True, type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/benchmarks/sensitivity_atlas_R0_slice_v1.yaml"),
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_solver(source_root: Path) -> tuple[Any, Any]:
    if git_revision(source_root) != EXPECTED_PRYM_REVISION:
        raise RuntimeError("PRyMordial revision drift")
    for relative, expected in EXPECTED_PRYM_FILES.items():
        if sha256(source_root / relative) != expected:
            raise RuntimeError(f"PRyMordial source-byte drift: {relative}")

    old_cwd = Path.cwd()
    sys.path.insert(0, str(source_root))
    try:
        os.chdir(source_root)
        import PRyM.PRyM_init as config  # type: ignore[import-not-found]
        import PRyM.PRyM_main as main  # type: ignore[import-not-found]
    finally:
        os.chdir(old_cwd)
    return config, main.PRyMclass


def configure(config: Any, protocol: dict[str, Any]) -> None:
    solver = protocol["solver"]
    config.Omegabh2 = float(solver["omega_b_h2"])
    config.eta0b = config.Omegabh2_to_eta0b * config.Omegabh2
    config.DeltaNeff = float(solver["delta_neff"])
    config.tau_n = float(solver["tau_n_seconds"]) * config.second
    config.aTid_flag = True
    config.compute_bckg_flag = True
    config.compute_nTOp_flag = True
    config.compute_nTOp_thermal_flag = False
    config.save_bckg_flag = False
    config.save_nTOp_flag = False
    config.save_nTOp_thermal_flag = False
    config.smallnet_flag = False
    config.nacreii_flag = False
    config.ReloadKeyRates()
    config.julia_flag = False
    config.verbose_flag = False
    config.NP_nuclear_flag = False
    for name in (
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
    ):
        setattr(config, name, 0.0)


def solve(config: Any, solver_class: Any, reaction: str | None, q: float) -> dict[str, float]:
    for native in ("dpHe3g", "ddHe3n", "ddtp"):
        setattr(config, f"p_{native}", q if native == reaction else 0.0)
    started = time.perf_counter()
    raw = solver_class().PRyMresults().tolist()
    elapsed = time.perf_counter() - started
    outputs = {
        "Yp": float(raw[4]),
        "DH": float(raw[5]),
        "Li7H": float(raw[7]),
    }
    if not all(math.isfinite(value) and value > 0 for value in outputs.values()):
        raise FloatingPointError(f"invalid abundance outputs: {outputs}")
    return {"elapsed_seconds": elapsed, "abundances": outputs}  # type: ignore[return-value]


def main() -> int:
    args = parse_args()
    protocol = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if git_revision(args.atlas_root) != EXPECTED_ATLAS_REVISION:
        raise RuntimeError("atlas revision drift")
    table_path = args.atlas_root / EXPECTED_ATLAS_TABLE
    if sha256(table_path) != EXPECTED_ATLAS_TABLE_SHA256:
        raise RuntimeError("atlas reference table byte drift")

    config, solver_class = load_solver(args.source_root)
    configure(config, protocol)
    attempts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for reaction in ("dpHe3g", "ddHe3n", "ddtp"):
        for q in (-1.0, 0.0, 1.0):
            try:
                attempts.append(
                    {"reaction": reaction, "q": q, **solve(config, solver_class, reaction, q)}
                )
            except Exception as exc:  # explicit complete failure accounting
                failures.append(
                    {
                        "reaction": reaction,
                        "q": q,
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                )
    try:
        repeat = solve(config, solver_class, None, 0.0)
        attempts.append({"reaction": "central_repeat", "q": 0.0, **repeat})
    except Exception as exc:
        failures.append(
            {
                "reaction": "central_repeat",
                "q": 0.0,
                "type": type(exc).__name__,
                "message": str(exc),
            }
        )

    by_key = {(row["reaction"], row["q"]): row for row in attempts}
    comparisons: dict[str, Any] = {}
    for reaction in ("dpHe3g", "ddHe3n", "ddtp"):
        if not all((reaction, q) in by_key for q in (-1.0, 0.0, 1.0)):
            continue
        minus = by_key[(reaction, -1.0)]["abundances"]
        central = by_key[(reaction, 0.0)]["abundances"]
        plus = by_key[(reaction, 1.0)]["abundances"]
        reference = protocol["published_reference"]["rows"][reaction]
        comparisons[reaction] = {
            "central": central,
            "minus_one_sigma": minus,
            "plus_one_sigma": plus,
            "centered_derivative_per_q": {
                name: (plus[name] - minus[name]) / 2.0 for name in central
            },
            "published_central": reference["central"],
            "published_derivative_per_q": reference["derivative_per_q"],
            "published_R2": reference["R2"],
        }

    repeat_drift = None
    if ("dpHe3g", 0.0) in by_key and ("central_repeat", 0.0) in by_key:
        first = by_key[("dpHe3g", 0.0)]["abundances"]
        second = by_key[("central_repeat", 0.0)]["abundances"]
        repeat_drift = max(abs(second[name] / first[name] - 1.0) for name in first)

    acceptance_failures: list[str] = []
    contract = protocol["acceptance"]
    if failures:
        acceptance_failures.append("structured_solver_failures_present")
    if len(attempts) + len(failures) != 10:
        acceptance_failures.append("incomplete_solve_accounting")
    if repeat_drift is None or repeat_drift > float(contract["maximum_repeat_relative_drift"]):
        acceptance_failures.append("central_repeat_drift_exceeds_contract")
    for reaction, result in comparisons.items():
        for abundance in ("Yp", "DH", "Li7H"):
            central = float(result["central"][abundance])
            reference_central = float(result["published_central"][abundance])
            derivative = float(result["centered_derivative_per_q"][abundance])
            reference_derivative = float(result["published_derivative_per_q"][abundance])
            if abs(central - reference_central) > float(
                contract["maximum_central_absolute_difference"][abundance]
            ):
                acceptance_failures.append(f"central_reference_mismatch:{reaction}:{abundance}")
            absolute_difference = abs(derivative - reference_derivative)
            relative_difference = absolute_difference / max(abs(reference_derivative), 1.0e-300)
            if absolute_difference > float(
                contract["derivative_absolute_floor"][abundance]
            ) and relative_difference > float(
                contract["maximum_derivative_relative_difference"][abundance]
            ):
                acceptance_failures.append(f"derivative_reference_mismatch:{reaction}:{abundance}")
            if (
                contract["require_expected_derivative_sign"]
                and derivative * reference_derivative <= 0
            ):
                acceptance_failures.append(f"derivative_sign_mismatch:{reaction}:{abundance}")
    if set(comparisons) != {"dpHe3g", "ddHe3n", "ddtp"}:
        acceptance_failures.append("incomplete_R0_comparison_set")
    acceptance_passes = not acceptance_failures

    payload: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": "SENSITIVITY-ATLAS-R0-SLICE-v1",
        "task_id": "UQ0-NATIVE-UQ-REPRO",
        "status": (
            "accepted_independent_public_calibration_reproduction"
            if acceptance_passes
            else "failed_independent_public_calibration_reproduction"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_scope": protocol["scientific_boundary"],
        "source": {
            "atlas_repository": protocol["published_object"]["repository"],
            "atlas_revision": EXPECTED_ATLAS_REVISION,
            "atlas_table_path": EXPECTED_ATLAS_TABLE,
            "atlas_table_sha256": EXPECTED_ATLAS_TABLE_SHA256,
            "atlas_generator_revision_available": False,
            "prymordial_repository": protocol["solver"]["repository"],
            "prymordial_revision": EXPECTED_PRYM_REVISION,
            "prymordial_source_sha256": EXPECTED_PRYM_FILES,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
            "platform": platform.platform(),
        },
        "configuration": protocol["solver"],
        "attempted_solve_count": len(attempts) + len(failures),
        "successful_solve_count": len(attempts),
        "failure_count": len(failures),
        "failures": failures,
        "attempts": attempts,
        "comparisons": comparisons,
        "maximum_repeat_relative_drift": repeat_drift,
        "runtime_seconds_total": sum(float(row["elapsed_seconds"]) for row in attempts),
        "acceptance_contract": protocol["acceptance"],
        "acceptance_passes": acceptance_passes,
        "acceptance_failures": sorted(set(acceptance_failures)),
        "native_UQ_task_progress_eligible": acceptance_passes,
        "limitations": [
            "The atlas publishes result PDFs but not its generating scripts.",
            "The atlas paper does not pin the PRyMordial source revision.",
            "This artifact compares an independent frozen-public-code rerun with the published table.",
            "It neither accepts a project prior nor authorizes production.",
        ],
    }
    payload["evidence_sha256"] = digest_json(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "evidence_sha256": payload["evidence_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
