from pathlib import Path

import yaml

from scripts.why_not_environment_smoke import BASELINES


ROOT = Path(__file__).resolve().parents[2]


def test_smoke_revisions_match_registered_manifest() -> None:
    manifest = yaml.safe_load(
        (ROOT / "manifests/software/why_not_baselines_v1.yaml").read_text(encoding="utf-8")
    )
    for baseline, (source_name, revision) in BASELINES.items():
        assert source_name
        assert revision == manifest["baselines"][baseline]["revision"]


def test_bootstrap_requires_exact_source_validation() -> None:
    script = (ROOT / "scripts/bootstrap_why_not_env.sh").read_text(encoding="utf-8")
    assert 'git -C "${SOURCE_ROOT}/${source_name}" rev-parse HEAD' in script
    assert "--require-hashes" in script
    assert "--no-deps" in script
    assert "environment_acceptance_only_not_a_benchmark" in (
        ROOT / "scripts/why_not_environment_smoke.py"
    ).read_text(encoding="utf-8")
