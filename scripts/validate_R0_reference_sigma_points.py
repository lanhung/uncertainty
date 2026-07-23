#!/usr/bin/env python3
"""Fail-closed validator for the two-path R0 reference sigma-point run."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from scripts.R0_reference_adapter import REACTIONS, digest_json, sha256, validate_protocol
from scripts.why_not_benchmark import load_yaml


OUTPUT_KEYS = ("Neff", "YPBBN", "DoH", "He3oH", "Li7oH")
REPRESENTATION = "R0_P0_ETR25_scalar_lognormal"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_evidence(path: Path, solver: str) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    stored = artifact.pop("evidence_sha256")
    require(digest_json(artifact) == stored, f"{solver} evidence digest drift")
    artifact["evidence_sha256"] = stored
    require(artifact.get("schema_version") == 1, f"{solver} schema drift")
    require(
        artifact.get("artifact_id") == "R0-REFERENCE-SIGMA-POINTS-v1",
        f"{solver} artifact identity drift",
    )
    require(artifact.get("solver") == solver, f"{solver} solver identity drift")
    require(
        artifact.get("representation") == REPRESENTATION,
        f"{solver} representation drift",
    )
    return artifact


def rows_by_node(artifact: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in artifact["results"]:
        require(row.get("status") == "ok", "non-ok terminal result")
        outputs = row.get("outputs")
        require(
            isinstance(outputs, dict) and set(outputs) == set(OUTPUT_KEYS), "output schema drift"
        )
        require(
            all(math.isfinite(float(outputs[key])) for key in OUTPUT_KEYS),
            "non-finite abundance output",
        )
        require(float(outputs["YPBBN"]) > 0.0, "non-positive YPBBN")
        require(float(outputs["DoH"]) > 0.0, "non-positive D/H")
        grouped.setdefault(str(row["node_id"]), []).append(row)
    return grouped


def primary_row(grouped: dict[str, list[dict[str, Any]]], node_id: str) -> dict[str, Any]:
    rows = sorted(grouped[node_id], key=lambda row: int(row["repetition"]))
    require(rows[0]["repetition"] == 0, f"missing primary row for {node_id}")
    return rows[0]


def response(
    grouped: dict[str, list[dict[str, Any]]],
    axis: str,
    output: str,
) -> float:
    minus = float(primary_row(grouped, f"{axis}_minus")["outputs"][output])
    plus = float(primary_row(grouped, f"{axis}_plus")["outputs"][output])
    return (plus - minus) / 2.0


def maximum_repeat_drift(grouped: dict[str, list[dict[str, Any]]]) -> float:
    maximum = 0.0
    for records in grouped.values():
        if len(records) < 2:
            continue
        ordered = sorted(records, key=lambda row: int(row["repetition"]))
        reference = ordered[0]["outputs"]
        for repeated in ordered[1:]:
            for key in OUTPUT_KEYS:
                left = float(reference[key])
                right = float(repeated["outputs"][key])
                maximum = max(maximum, abs(right - left) / max(abs(left), 1.0e-300))
    return maximum


def evaluate(
    protocol: dict[str, Any],
    linx: dict[str, Any],
    prymordial: dict[str, Any],
    curve_manifest: dict[str, Any],
) -> dict[str, Any]:
    expected_nodes = {str(node["id"]) for node in protocol["sigma_point_design"]["nodes"]}
    linx_rows = rows_by_node(linx)
    prym_rows = rows_by_node(prymordial)
    require(set(linx_rows) == expected_nodes, "LINX node grid incomplete")
    require(set(prym_rows) == expected_nodes, "PRyMordial node grid incomplete")
    require(linx["failure_count"] == 0, "LINX structured failures present")
    require(prymordial["failure_count"] == 0, "PRyMordial structured failures present")
    require(
        linx["claim_boundary"] == protocol["claim_boundary"]
        and prymordial["claim_boundary"] == protocol["claim_boundary"],
        "claim boundary drift",
    )

    checks: dict[str, bool] = {}
    center_curves = curve_manifest["center"]
    axis_by_reaction = {
        "dp_gamma_he3": "dp_gamma_he3",
        "dd_n_he3": "dd_n_he3",
        "dd_p_t": "dd_p_t",
    }
    for reaction_id, axis in axis_by_reaction.items():
        center = center_curves[reaction_id]["curve_sha256"]
        minus = curve_manifest[f"{axis}_minus"][reaction_id]["curve_sha256"]
        plus = curve_manifest[f"{axis}_plus"][reaction_id]["curve_sha256"]
        checks[f"{reaction_id}_curve_changes"] = center not in {minus, plus} and minus != plus

    tolerance = float(protocol["plusminus_acceptance"]["reverse_relative_tolerance"])
    for reaction in REACTIONS:
        linx_reverse = linx["reverse_rate_audit"][reaction.canonical_id]
        prym_reverse = prymordial["reverse_rate_audit"][reaction.canonical_id]
        checks[f"{reaction.canonical_id}_reverse_same_draw"] = (
            linx_reverse["same_perturbed_forward_used_by_reverse"] is True
            and int(linx_reverse["defined_rows"]) > 0
            and float(linx_reverse["maximum_relative_error"]) <= tolerance
            and prym_reverse["same_perturbed_forward_used_by_reverse"] is True
        )

    floor = float(protocol["plusminus_acceptance"]["non_negligible_DH_response_floor"])
    for reaction_id in axis_by_reaction:
        linx_response = response(linx_rows, reaction_id, "DoH")
        prym_response = response(prym_rows, reaction_id, "DoH")
        checks[f"{reaction_id}_DH_response_negative"] = (
            linx_response < -floor and prym_response < -floor
        )

    checks["tau_n_YPBBN_response_positive"] = (
        response(linx_rows, "tau_n", "YPBBN") > 0.0 and response(prym_rows, "tau_n", "YPBBN") > 0.0
    )
    contract = protocol["canonical_contract"]
    checks["canonical_units_and_output_mapping_valid"] = (
        contract["source_rate_unit"] == "cm3_mol-1_s-1"
        and contract["LINX_numeric_rate_unit"] == "cm3_s-1_g-1"
        and contract["numeric_conversion"] == "identity_under_molar_mass_constant_convention"
        and set(contract["raw_outputs"]) == set(OUTPUT_KEYS)
    )
    repeat = max(maximum_repeat_drift(linx_rows), maximum_repeat_drift(prym_rows))
    checks["zero_structured_failures_and_repeat_drift"] = linx["failure_count"] == prymordial[
        "failure_count"
    ] == 0 and repeat <= float(protocol["plusminus_acceptance"]["maximum_repeat_relative_drift"])

    expected_check_ids = protocol["plusminus_acceptance"]["check_ids"]
    require(set(checks) == set(expected_check_ids), "computed acceptance check set drift")
    accepted = all(checks.values())
    return {
        "accepted": accepted,
        "adapter_paths_ready": 2 if accepted else 0,
        "checks": checks,
        "maximum_repeat_relative_drift": repeat,
        "plusminus_checks_passed": sum(checks.values()),
        "sigma_nodes_ready": 9 if accepted else 0,
        "task_progress": {
            "UQ0-NUISANCE-ADAPTER": [2 if accepted else 0, 2],
            "UQ0-PLUSMINUS-REGRESSION": [sum(checks.values()), 12],
            "UQ1-SIGMA-POINT-9": [9 if accepted else 0, 9],
        },
    }


def validate(
    *,
    protocol_path: Path,
    linx_result_path: Path,
    prymordial_result_path: Path,
    linx_curve_path: Path,
    prymordial_curve_path: Path,
    repository_root: Path,
    yaml_python: Path | None = None,
) -> dict[str, Any]:
    protocol, _ = load_yaml(protocol_path, yaml_python)
    validate_protocol(protocol, repository_root)
    linx = load_evidence(linx_result_path, "LINX")
    prymordial = load_evidence(prymordial_result_path, "PRyMordial")
    require(
        sha256(linx_curve_path) == linx["curve_manifest_sha256"],
        "LINX curve manifest hash drift",
    )
    require(
        sha256(prymordial_curve_path) == prymordial["curve_manifest_sha256"],
        "PRyMordial curve manifest hash drift",
    )
    linx_curves = json.loads(linx_curve_path.read_text(encoding="utf-8"))
    prymordial_curves = json.loads(prymordial_curve_path.read_text(encoding="utf-8"))
    require(linx_curves == prymordial_curves, "solver curve manifests differ")
    return evaluate(protocol, linx, prymordial, linx_curves)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linx-dir", required=True, type=Path)
    parser.add_argument("--prymordial-dir", required=True, type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/benchmarks/R0_reference_fast_track_v1.yaml"),
    )
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--yaml-python", type=Path)
    args = parser.parse_args()
    result = validate(
        protocol_path=args.config,
        linx_result_path=args.linx_dir / "results.json",
        prymordial_result_path=args.prymordial_dir / "results.json",
        linx_curve_path=args.linx_dir / "curve_manifest.json",
        prymordial_curve_path=args.prymordial_dir / "curve_manifest.json",
        repository_root=args.repository_root.resolve(),
        yaml_python=args.yaml_python,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
