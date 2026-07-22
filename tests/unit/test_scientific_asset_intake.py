import hashlib
import zipfile
from pathlib import Path

import pytest
import yaml

from scripts.register_scientific_asset import AssetIntakeError, register_asset


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "configs/inventory/scientific_asset_intake_v1.yaml"


def test_checkpoint_registration_hashes_without_deserializing(tmp_path: Path) -> None:
    checkpoint = tmp_path / "candidate.pth"
    checkpoint.write_bytes(b"untrusted pickle-like bytes")
    expected = hashlib.sha256(checkpoint.read_bytes()).hexdigest()

    manifest = register_asset(
        checkpoint,
        "bbnet_checkpoint",
        "operator handoff",
        "unknown_pending_review",
        "candidate paper checkpoint",
        expected,
    )

    assert manifest["sha256"] == expected
    assert manifest["status"] == "quarantined_unreviewed"
    assert manifest["approved_for_scientific_inference"] is False
    assert manifest["approved_for_production"] is False
    assert manifest["security"] == {
        "deserialization_performed": False,
        "execution_performed": False,
        "extraction_performed": False,
    }
    assert manifest["archive_inspection"]["format"] == "not_an_archive"


def test_directory_tree_hash_is_deterministic_and_rejects_symlinks(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "b.py").write_text("b = 2\n", encoding="utf-8")
    (source / "a.py").write_text("a = 1\n", encoding="utf-8")

    first = register_asset(
        source,
        "data_generation_script",
        "operator handoff",
        "MIT",
        "candidate label generator",
    )
    second = register_asset(
        source,
        "data_generation_script",
        "operator handoff",
        "MIT",
        "candidate label generator",
    )

    assert first["sha256"] == second["sha256"]
    assert first["files"] == second["files"]
    assert [item["relative_path"] for item in first["files"]] == ["a.py", "b.py"]

    (source / "link.py").symlink_to(source / "a.py")
    with pytest.raises(AssetIntakeError, match="contains symlink"):
        register_asset(
            source,
            "data_generation_script",
            "operator handoff",
            "MIT",
            "candidate label generator",
        )


def test_archive_traversal_and_checksum_mismatch_fail_closed(tmp_path: Path) -> None:
    archive = tmp_path / "solver.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("../escape.py", "bad = True\n")

    with pytest.raises(AssetIntakeError, match="unsafe zip metadata"):
        register_asset(
            archive,
            "modified_parthenope_source",
            "operator handoff",
            "unknown_pending_review",
            "candidate modified solver",
        )

    checkpoint = tmp_path / "candidate.pt"
    checkpoint.write_bytes(b"bytes")
    with pytest.raises(AssetIntakeError, match="checksum mismatch"):
        register_asset(
            checkpoint,
            "bbnet_checkpoint",
            "operator handoff",
            "unknown_pending_review",
            "candidate checkpoint",
            "0" * 64,
        )


def test_wrong_types_empty_provenance_and_top_level_symlink_are_rejected(
    tmp_path: Path,
) -> None:
    wrong = tmp_path / "checkpoint.txt"
    wrong.write_text("not allowed", encoding="utf-8")
    with pytest.raises(AssetIntakeError, match="allowed suffixes"):
        register_asset(
            wrong,
            "bbnet_checkpoint",
            "operator handoff",
            "unknown",
            "candidate checkpoint",
        )

    checkpoint = tmp_path / "checkpoint.pth"
    checkpoint.write_bytes(b"bytes")
    with pytest.raises(AssetIntakeError, match="must be non-empty"):
        register_asset(checkpoint, "bbnet_checkpoint", "", "unknown", "candidate")

    link = tmp_path / "link.pth"
    link.symlink_to(checkpoint)
    with pytest.raises(AssetIntakeError, match="symlinks are forbidden"):
        register_asset(link, "bbnet_checkpoint", "origin", "unknown", "candidate")


def test_policy_covers_every_declared_missing_asset_family() -> None:
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))

    assert set(policy["categories"]) == {
        "modified_parthenope_source",
        "modified_alterbbn_source",
        "bbnet_checkpoint",
        "bbnet_scaler",
        "training_or_validation_data",
        "data_generation_script",
        "mcmc_or_likelihood_asset",
    }
    assert policy["approved_for_scientific_inference"] is False
    assert policy["default_status"] == "quarantined_unreviewed"
