from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests/models/ml4gw_upstreams_v1.yaml"
BBNET_CONFIG = ROOT / "configs/models/bbnet_ml4gw_v1.yaml"
SAGENET_VALIDATOR = ROOT / "scripts/validate_sagenet_checkpoints.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_ml4gw_bbnet_snapshot_matches_registered_tree() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    source = data["sources"]["bbnet"]
    root = ROOT / source["local_snapshot"]

    assert source["commit"] == "9bd5147095f25fd8c6ac7cad30d78c71bcd3ece7"
    assert source["snapshot_status"] == "exact_git_archive"

    expected_names = {record["path"] for record in source["files"]}
    observed_names = {path.name for path in root.iterdir() if path.is_file()}
    assert observed_names == expected_names

    for record in source["files"]:
        path = root / record["path"]
        assert path.stat().st_size == record["size_bytes"], path
        assert _sha256(path) == record["sha256"], path


def test_upstreams_are_not_misrepresented_as_validated() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    status = data["scientific_status"]
    assert status["approved_for_claims"] is False
    assert status["bbnet_reproduction_complete"] is False
    assert status["sagenet_forward_validation_complete"] is False
    assert status["sagenet_structural_validation_complete"] is True

    bbnet = data["sources"]["bbnet"]
    weight_record = next(item for item in bbnet["files"] if item["path"] == "weights")
    assert weight_record["size_bytes"] == 1
    assert "pretrained BBNet checkpoints" in bbnet["absent_from_all_reachable_history"]

    sagenet = data["sources"]["sagenet"]
    assert sagenet["checkpoint_safety"]["format"] == "pytorch_zip_with_pickle_metadata"
    assert sagenet["submodules"][0]["license"] == "GPL-3.0"
    inputs = next(
        artifact
        for artifact in sagenet["artifacts"]
        if artifact["path"].endswith("solve_plus.data_test_5400.json")
    )
    assert "log10OmegaGW" in inputs["missing_fields"]
    assert (
        "checkpoint prediction equivalence to the paper environment" in sagenet["not_established"]
    )


def test_bbnet_schema_mismatch_remains_an_explicit_gate() -> None:
    data = yaml.safe_load(BBNET_CONFIG.read_text(encoding="utf-8"))
    training = data["training_scripts"]
    evaluation = data["evaluation_scripts"]

    assert (
        training["parthenope"]["inputs"] != evaluation["file_named_parthenope"]["expected_inputs"]
    )
    assert training["alterbbn"]["inputs"] != evaluation["alterbbn_expert"]["expected_inputs"]
    assert data["use_policy"]["approved_for_scientific_inference"] is False


def test_sagenet_validator_never_enables_unrestricted_pickle_loading() -> None:
    source = SAGENET_VALIDATOR.read_text(encoding="utf-8")
    assert "weights_only=True" in source
    assert "weights_only=False" not in source
    assert "strict=True" in source

    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    validation = data["sources"]["sagenet"]["structural_validation"]
    assert validation["status"] == "passed"
    assert validation["scientific_output_equivalence"] is False
    assert set(validation["scaler_serialization_versions"].values()) == {"1.2.2", "1.6.1"}
