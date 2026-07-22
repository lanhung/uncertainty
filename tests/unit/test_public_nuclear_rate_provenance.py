from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/capture_public_nuclear_rate_provenance.py"
CONFIG = ROOT / "configs/physics/public_nuclear_rate_provenance_v1.yaml"


def load_module():
    spec = importlib.util.spec_from_file_location("public_rate_provenance", SCRIPT)
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
