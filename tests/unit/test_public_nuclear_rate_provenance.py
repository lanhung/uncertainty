from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/capture_public_nuclear_rate_provenance.py"
CONFIG = ROOT / "configs/physics/public_nuclear_rate_provenance_v1.yaml"
ARTIFACT = (
    ROOT
    / "artifacts/provenance/PUBLIC-NUCLEAR-RATE-PROVENANCE-v1"
    / "capture-20260722T200435Z.json"
)
VALIDATOR = ROOT / "scripts/validate_public_nuclear_rate_provenance.py"


def load_module():
    spec = importlib.util.spec_from_file_location("public_rate_provenance", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_public_rate_provenance", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_protocol_covers_four_repositories_and_three_reactions() -> None:
    module = load_module()
    protocol = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    module.validate_protocol(protocol)
    assert set(protocol["repositories"]) == {"LINX", "PRyMordial", "PRIMAT", "ABCMB"}
    assert set(protocol["reaction_path_tokens"]) == {
        "dp_gamma_he3",
        "dd_n_he3",
        "dd_p_t",
    }


def test_capture_binds_git_blob_and_file_hash(tmp_path: Path) -> None:
    module = load_module()
    repo = tmp_path / "TEST"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "rate.txt").write_text("1 2 3\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "rate.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    revision = module.git(repo, "rev-parse", "HEAD")
    captured = module.capture_repository(
        tmp_path,
        "TEST",
        {"revision": revision, "license": "test-only", "collections": {"c": ["rate.txt"]}},
    )
    item = captured["collections"]["c"][0]
    assert item["sha256"] == module.sha256(repo / "rate.txt")
    assert item["git_blob"] == module.git(repo, "rev-parse", "HEAD:rate.txt")
    assert item["line_count"] == 1


def test_capture_rejects_dirty_tracked_source(tmp_path: Path) -> None:
    module = load_module()
    repo = tmp_path / "TEST"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "rate.txt").write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "rate.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    revision = module.git(repo, "rev-parse", "HEAD")
    (repo / "rate.txt").write_text("modified\n", encoding="utf-8")
    try:
        module.capture_repository(
            tmp_path,
            "TEST",
            {
                "revision": revision,
                "license": "test-only",
                "collections": {"c": ["rate.txt"]},
            },
        )
    except ValueError as exc:
        assert "dirty" in str(exc)
    else:
        raise AssertionError("dirty tracked checkout was accepted")


def test_committed_capture_passes_standalone_validator() -> None:
    result = load_validator().validate(CONFIG, ARTIFACT)

    assert result == {
        "accepted": True,
        "artifact_id": "PUBLIC-NUCLEAR-RATE-PROVENANCE-v1",
        "duplicate_content_groups": 3,
        "file_count": 21,
        "nuc_v1_frozen": False,
        "repositories": 4,
        "status": "captured_inventory_only_not_nuc_freeze",
    }


def test_validator_rejects_tampered_file_or_duplicate_group(
    tmp_path: Path,
) -> None:
    validator = load_validator()
    original = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    for mutation in ("file", "duplicates"):
        payload = copy.deepcopy(original)
        if mutation == "file":
            payload["repositories"]["LINX"]["collections"]["key_recommended"][0][
                "sha256"
            ] = "0" * 64
        else:
            payload["duplicate_content_groups"] = []
        path = tmp_path / f"{mutation}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            validator.validate(CONFIG, path)
        except ValueError as exc:
            assert "capture hash drift" in str(exc)
        else:
            raise AssertionError(f"tampered {mutation} capture was accepted")
