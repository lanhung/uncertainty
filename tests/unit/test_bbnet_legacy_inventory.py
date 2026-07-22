from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests/models/bbnet_legacy_upstream_v1.yaml"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_imported_legacy_text_matches_manifest() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    groups = data["imports"]
    records = groups["package_snapshot"]["files"]

    for record in records:
        path = ROOT / record["path"]
        assert path.is_file(), path
        assert _sha256(path) == record["local_sha256"], path


def test_legacy_import_is_not_misrepresented_as_runnable() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    status = data["scientific_status"]
    assert status["runnable"] is False
    assert status["reproduction_complete"] is False
    assert status["approved_for_inference"] is False

    binaries = {item["name"]: item for item in data["binary_artifacts_not_imported"]}
    assert binaries["model_pe.pth"]["status"].startswith("absent")
    assert binaries["model_al.pth"]["status"].startswith("rejected_truncated")

    recovered = data["imports"]["recovered_training_scripts"]
    assert recovered["imported"] is False
