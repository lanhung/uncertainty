import ast
import hashlib
from pathlib import Path

import pytest
import yaml

from scripts.bbnet_schema_adapter import (
    BBNetSchemaError,
    materialize_inputs,
    normalize_inputs,
    normalize_outputs,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "configs/models/bbnet_interface_schema_v1.yaml"


def _literal_assignment(path: Path, name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            values.append(ast.literal_eval(node.value))
    assert len(values) == 1, (path, name, values)
    return values[0]


def test_registry_is_bound_to_exact_public_source_schemas() -> None:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))

    assert registry["status"] == "structural_contract_only_scientific_inference_forbidden"
    for interface in registry["interfaces"].values():
        source = ROOT / interface["source"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == interface["source_sha256"]
        assert _literal_assignment(source, "input_cols") == interface["input_columns"]
        output_name = "output_cols" if source.name.startswith("train_") else "y_cols"
        assert _literal_assignment(source, output_name) == interface["output_columns"]
        assert interface["approved_for_scientific_inference"] is False


def test_parthenope_training_row_round_trips_structurally() -> None:
    source = {"OmegaBh^2": 0.02237, "dn_nu": 0.0, "kappa": 0.0, "tau": 878.3}

    normalized = normalize_inputs("parthenope_training", source)

    assert normalized.canonical == {
        "omega_b_h2": 0.02237,
        "delta_neff": 0.0,
        "kappa10": 0.0,
        "tau_n_seconds": 878.3,
    }
    assert normalized.unresolved == {}
    assert normalized.approved_for_scientific_inference is False
    assert materialize_inputs("parthenope_training", normalized.canonical) == list(source.values())


def test_alterbbn_training_preserves_unresolved_fields_and_cannot_materialize() -> None:
    source = {"dd0": 1.0, "dd0_rad": 2.0, "tau": 878.3, "omegabn": 0.02237}

    normalized = normalize_inputs("alterbbn_training", source)

    assert normalized.canonical == {"tau_n_seconds": 878.3, "omega_b_h2": 0.02237}
    assert normalized.unresolved == {"dd0": 1.0, "dd0_rad": 2.0}
    with pytest.raises(BBNetSchemaError, match="unresolved physical mappings"):
        materialize_inputs(
            "alterbbn_training",
            {
                "omega_b_h2": 0.02237,
                "delta_neff": 0.0,
                "kappa10": 0.0,
                "tau_n_seconds": 878.3,
            },
        )


def test_evaluator_alias_is_structural_only_and_outputs_are_canonicalized() -> None:
    canonical = {
        "omega_b_h2": 0.02237,
        "delta_neff": 0.0,
        "kappa10": 0.0,
        "tau_n_seconds": 878.3,
    }

    assert materialize_inputs("alterbbn_evaluator", canonical) == [
        0.0,
        0.0,
        878.3,
        0.02237,
    ]
    normalized = normalize_inputs(
        "alterbbn_evaluator",
        {"kappa10": 0.0, "DN_eff": 0.0, "tau": 878.3, "omegabn": 0.02237},
    )
    assert normalized.canonical == canonical
    assert normalized.approved_for_scientific_inference is False
    assert normalize_outputs("alterbbn_evaluator", {"H2/H": 2.5e-5, "Yp": 0.247}) == {
        "D_over_H": 2.5e-5,
        "Y_p": 0.247,
    }


def test_adapter_rejects_missing_unknown_nonfinite_and_boolean_values() -> None:
    valid = {"OmegaBh^2": 0.02237, "dn_nu": 0.0, "kappa": 0.0, "tau": 878.3}

    with pytest.raises(BBNetSchemaError, match="missing"):
        normalize_inputs(
            "parthenope_training", {key: value for key, value in valid.items() if key != "tau"}
        )
    with pytest.raises(BBNetSchemaError, match="unknown"):
        normalize_inputs("parthenope_training", {**valid, "silent_extra": 1.0})
    with pytest.raises(BBNetSchemaError, match="finite"):
        normalize_inputs("parthenope_training", {**valid, "tau": float("nan")})
    with pytest.raises(BBNetSchemaError, match="numeric scalar"):
        normalize_inputs("parthenope_training", {**valid, "kappa": False})
