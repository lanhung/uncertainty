#!/usr/bin/env python3
"""Build the deterministic Stage-R0 scalar-rate package from pinned LINX tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


EXPECTED_REVISION = "ec2e9d2ca455e8204137e884da29f5dd13a638fa"
EXPECTED_TABLES = {
    "dp_gamma_he3": {
        "linx_id": "dpHe3g",
        "path": "linx/data/nuclear_rates/key_recommended/dpHe3g.txt",
        "git_blob": "ac7d26e7032d8b58c1ea494bbb1db0ec6a761e50",
        "q_index": 1,
        "in_states": [1, 2],
        "out_states": [4],
        "forward_symmetry_factor": 1.0,
        "backward_symmetry_factor": 1.0,
        "sha256": "b5c410b91daaef1d4fe4b3c349f615fa9fa0a7a013a98b28b2e295574c0b4906",
        "alpha": 1.6335102e10,
        "beta": 1.5,
        "gamma": -63.749132,
    },
    "dd_n_he3": {
        "linx_id": "ddHe3n",
        "path": "linx/data/nuclear_rates/key_recommended/ddHe3n.txt",
        "git_blob": "50fa383ea2ae0c510c7f2513dff271d7e0d4f64d",
        "q_index": 2,
        "in_states": [2, 2],
        "out_states": [0, 4],
        "forward_symmetry_factor": 0.5,
        "backward_symmetry_factor": 1.0,
        "sha256": "3c7aed50f298501e60279782ae638e6799c4247d265e43075a2ad2fd46225d7d",
        "alpha": 1.7318296,
        "beta": 0.0,
        "gamma": -37.934112,
    },
    "dd_p_t": {
        "linx_id": "ddtp",
        "path": "linx/data/nuclear_rates/key_recommended/ddtp.txt",
        "git_blob": "b4e5303bc3a29e42e6c4d77a4e15fccf51d94a40",
        "q_index": 3,
        "in_states": [2, 2],
        "out_states": [1, 3],
        "forward_symmetry_factor": 0.5,
        "backward_symmetry_factor": 1.0,
        "sha256": "bd9acc42dcccb9de167cc78b19e8d91c51b0f8ee5bbc2c0e155d2bd69344cc45",
        "alpha": 1.7349209,
        "beta": 0.0,
        "gamma": -46.797116,
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def parse_table(path: Path) -> dict[str, Any]:
    header: list[str] = []
    rows: list[tuple[float, float, float]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            header.append(line[1:].strip())
            continue
        fields = line.split()
        if len(fields) != 3:
            raise ValueError(f"{path}:{line_number}: expected exactly three columns")
        row = tuple(float(value) for value in fields)
        if not all(math.isfinite(value) and value > 0 for value in row):
            raise ValueError(f"{path}:{line_number}: all values must be finite and positive")
        rows.append(row)

    if len(rows) != 150:
        raise ValueError(f"{path}: expected 150 data rows, found {len(rows)}")
    t9 = [row[0] for row in rows]
    if any(right <= left for left, right in zip(t9, t9[1:])):
        raise ValueError(f"{path}: T9 grid must be strictly increasing")
    expsigma = [row[2] for row in rows]
    if any(value < 1 for value in expsigma):
        raise ValueError(f"{path}: exp(sigma) must be at least one")
    return {
        "header": header,
        "T9": t9,
        "central_rate": [row[1] for row in rows],
        "exp_sigma": expsigma,
        "log_sigma": [math.log(value) for value in expsigma],
    }


def build(source_root: Path) -> dict[str, Any]:
    revision = git_value(source_root, "rev-parse", "HEAD")
    if revision != EXPECTED_REVISION:
        raise ValueError(f"LINX revision mismatch: {revision} != {EXPECTED_REVISION}")
    if git_value(source_root, "status", "--short"):
        raise ValueError("LINX source checkout must be clean")

    reactions: dict[str, Any] = {}
    common_grid: list[float] | None = None
    for reaction_id, specification in EXPECTED_TABLES.items():
        table_path = source_root / specification["path"]
        actual_blob = git_value(
            source_root,
            "rev-parse",
            f"HEAD:{specification['path']}",
        )
        if actual_blob != specification["git_blob"]:
            raise ValueError(
                f"{reaction_id} Git blob mismatch: {actual_blob} != {specification['git_blob']}"
            )
        actual_sha256 = sha256(table_path)
        if actual_sha256 != specification["sha256"]:
            raise ValueError(
                f"{reaction_id} table hash mismatch: {actual_sha256} != {specification['sha256']}"
            )
        parsed = parse_table(table_path)
        if common_grid is None:
            common_grid = parsed["T9"]
        elif parsed["T9"] != common_grid:
            raise ValueError(f"{reaction_id} does not use the common R0 T9 grid")
        reactions[reaction_id] = {
            "linx_id": specification["linx_id"],
            "linx_q_index": specification["q_index"],
            "in_states": specification["in_states"],
            "out_states": specification["out_states"],
            "forward_symmetry_factor": specification["forward_symmetry_factor"],
            "backward_symmetry_factor": specification["backward_symmetry_factor"],
            "source_path": specification["path"],
            "source_git_blob": actual_blob,
            "source_sha256": actual_sha256,
            "source_header": parsed["header"],
            "central_rate": parsed["central_rate"],
            "exp_sigma": parsed["exp_sigma"],
            "log_sigma": parsed["log_sigma"],
            "scalar_transform_at_table_knots": (
                "rate(T9_j,z)=central_rate(T9_j)*exp(z*log_sigma(T9_j))"
            ),
            "reverse_rate": {
                "formula": "reverse=alpha*T9**beta*exp(gamma/T9)*forward",
                "alpha": specification["alpha"],
                "beta": specification["beta"],
                "gamma": specification["gamma"],
                "same_scalar_z_as_forward": True,
            },
        }

    assert common_grid is not None
    return {
        "schema_version": 1,
        "package_id": "NUCLEAR-STAGE0-R0-LINX-KEY-RECOMMENDED-v1",
        "status": "engineering_scalar_prior_scientific_signoff_pending",
        "source": {
            "repository": "https://github.com/cgiovanetti/LINX",
            "revision": revision,
            "tree": git_value(source_root, "rev-parse", "HEAD^{tree}"),
            "software_distribution_license": "MIT",
            "derived_table_redistribution_review": "pending",
            "collection": "key_recommended",
            "compilation_label": "LINX_key_recommended_2026_GP_derived_scalar_envelope",
            "primary_citation": "arXiv:2604.16600",
            "source_evidence": {
                "parser": {
                    "path": "linx/reactions.py",
                    "git_blob": "125915f1706575093606418aa6aee6502c328cdc",
                    "sha256": "5ebdb9c86978c19213d72adb3371e649ce1adffc3c8fa395dd39d0410ccbc0ee",
                },
                "network_mapping": {
                    "path": "linx/nuclear.py",
                    "git_blob": "f311f5a069ebedf1dfe00e424cb4058d699dacd5",
                    "sha256": "b969043f545cfeddf41d4c3c9c376f9dfb12a52ba67cd2472f0f324f2ee126b8",
                },
            },
        },
        "coordinate": {
            "name": "T9",
            "definition": "T / 1e9 K",
            "grid": common_grid,
        },
        "rate_units": "cm^3 s^-1 g^-1",
        "central_curve_semantics": "p_equals_zero_curve_mean_vs_median_unresolved",
        "interpolation": {
            "registered_for_R0": "linear_in_perturbed_rate_over_T9",
            "operation_order": "perturb_table_knots_then_interpolate",
            "log_symmetric_transform_exact_only_at_table_knots": True,
            "out_of_grid_policy": "reject_before_solver_call",
        },
        "within_reaction_covariance": {
            "rank": 1,
            "definition_at_table_knots": ("Cov[log r(Ta),log r(Tb)]=log_sigma(Ta)*log_sigma(Tb)"),
            "single_scalar_z_shared_over_temperature": True,
        },
        "cross_reaction_covariance": {
            "baseline_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "order": ["dp_gamma_he3", "dd_n_he3", "dd_p_t"],
            "status": "missing_not_evidence_of_independence",
            "use": "engineering_baseline_only_with_preregistered_correlation_stress",
        },
        "functional_posterior_boundary": {
            "included": False,
            "reason": "three-column tables expose a one-scalar-per-reaction envelope, not full GP draws",
        },
        "reactions": reactions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linx-source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(build(args.linx_source_root), indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
