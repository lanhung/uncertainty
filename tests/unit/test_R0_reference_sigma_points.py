from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_R0_reference_sigma_points.py"
PROTOCOL = ROOT / "configs/benchmarks/R0_reference_fast_track_v1.yaml"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_R0_reference_sigma_points", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fixtures():
    protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    nodes = protocol["sigma_point_design"]["nodes"]
    outputs = {
        node["id"]: {
            "Neff": 3.044,
            "YPBBN": 0.247,
            "DoH": 2.5e-5,
            "He3oH": 1.0e-5,
            "Li7oH": 5.0e-10,
        }
        for node in nodes
    }
    for axis in ("dp_gamma_he3", "dd_n_he3", "dd_p_t"):
        outputs[f"{axis}_minus"]["DoH"] += 1.0e-7
        outputs[f"{axis}_plus"]["DoH"] -= 1.0e-7
    outputs["tau_n_minus"]["YPBBN"] -= 1.0e-3
    outputs["tau_n_plus"]["YPBBN"] += 1.0e-3

    def artifact(solver: str):
        rows = []
        for node in nodes:
            repetitions = 2
            for repetition in range(repetitions):
                rows.append(
                    {
                        "node_id": node["id"],
                        "outputs": outputs[node["id"]].copy(),
                        "q": node["q"],
                        "repetition": repetition,
                        "status": "ok",
                    }
                )
        reverse = {
            reaction: {
                "same_perturbed_forward_used_by_reverse": True,
                **(
                    {"defined_rows": 10, "maximum_relative_error": 1.0e-14}
                    if solver == "LINX"
                    else {}
                ),
            }
            for reaction in ("dp_gamma_he3", "dd_n_he3", "dd_p_t")
        }
        return {
            "claim_boundary": protocol["claim_boundary"],
            "failure_count": 0,
            "results": rows,
            "reverse_rate_audit": reverse,
        }

    curves = {}
    for node in nodes:
        curves[node["id"]] = {}
        for reaction in ("dp_gamma_he3", "dd_n_he3", "dd_p_t"):
            changed = node["id"] in {f"{reaction}_minus", f"{reaction}_plus"}
            curves[node["id"]][reaction] = {
                "curve_sha256": f"{reaction}:{node['id'] if changed else 'center'}"
            }
    return protocol, artifact("LINX"), artifact("PRyMordial"), curves


def test_evaluator_accepts_complete_two_path_sigma_grid() -> None:
    module = load_module()
    protocol, linx, prymordial, curves = fixtures()
    result = module.evaluate(protocol, linx, prymordial, curves)

    assert result["accepted"] is True
    assert result["adapter_paths_ready"] == 2
    assert result["plusminus_checks_passed"] == 12
    assert result["sigma_nodes_ready"] == 9


def test_evaluator_rejects_wrong_physical_response_sign() -> None:
    module = load_module()
    protocol, linx, prymordial, curves = fixtures()
    for artifact in (linx, prymordial):
        by_node = {row["node_id"]: row for row in artifact["results"] if row["repetition"] == 0}
        by_node["dp_gamma_he3_plus"]["outputs"]["DoH"] = 2.6e-5
        by_node["dp_gamma_he3_minus"]["outputs"]["DoH"] = 2.4e-5

    result = module.evaluate(protocol, linx, prymordial, curves)
    assert result["accepted"] is False
    assert result["checks"]["dp_gamma_he3_DH_response_negative"] is False
    assert result["sigma_nodes_ready"] == 0
