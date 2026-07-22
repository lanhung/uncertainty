from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from scripts import run_why_not_standard_challenge_suite as suite


def test_parse_mapping_requires_all_frozen_baselines(tmp_path: Path) -> None:
    values = [f"{baseline}={tmp_path / baseline}" for baseline in suite.BASELINE_ORDER]
    mapping = suite.parse_mapping(values, "--source-dir")
    assert tuple(mapping) == suite.BASELINE_ORDER
    with pytest.raises(ValueError, match="baseline mismatch"):
        suite.parse_mapping(values[:-1], "--source-dir")


def test_load_protocol_rejects_reordered_baselines(tmp_path: Path) -> None:
    path = tmp_path / "protocol.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "status": "protocol_frozen_measurements_pending",
                "baselines": {baseline: {} for baseline in reversed(suite.BASELINE_ORDER)},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="baseline order"):
        suite.load_protocol(path)


def test_main_reports_only_completed_baselines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol = tmp_path / "protocol.yaml"
    protocol.write_text(
        yaml.safe_dump(
            {
                "status": "protocol_frozen_measurements_pending",
                "baselines": {baseline: {} for baseline in suite.BASELINE_ORDER},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    common = tmp_path / "input"
    common.write_text("x\n", encoding="utf-8")
    sources: list[str] = []
    interpreters: list[str] = []
    locks: list[str] = []
    for baseline in suite.BASELINE_ORDER:
        source = tmp_path / f"source-{baseline}"
        source.mkdir()
        lock = tmp_path / f"lock-{baseline}"
        lock.write_text("lock\n", encoding="utf-8")
        sources.extend(["--source-dir", f"{baseline}={source}"])
        interpreters.extend(["--baseline-python", f"{baseline}={sys.executable}"])
        locks.extend(["--environment-lock", f"{baseline}={lock}"])

    calls: list[list[str]] = []

    def fake_run(command: list[str], log: object) -> int:
        calls.append(command)
        return 0

    monkeypatch.setattr(suite, "run_command", fake_run)
    output = tmp_path / "output"
    result = suite.main(
        [
            "--config",
            str(protocol),
            "--cmb-config",
            str(common),
            "--neutron-config",
            str(common),
            "--parameter-schema",
            str(common),
            "--observation-config",
            str(common),
            "--inventory",
            str(common),
            "--yaml-python",
            sys.executable,
            "--output-dir",
            str(output),
            "--hourly-price-cny",
            "2.88",
            *interpreters,
            *sources,
            *locks,
        ]
    )
    assert result == 0
    assert len(calls) == 4
    assert capsys.readouterr().out.count("BASELINE_PROGRESS") == 4
    manifest = json.loads((output / "suite_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert list(manifest["baselines"]) == list(suite.BASELINE_ORDER)
