#!/usr/bin/env python3
"""Run the four frozen WHY-NOT challenge baselines in registered order.

The per-baseline harness deliberately reports case progress as ``PROGRESS i/7``.
This suite emits the distinct ``BASELINE_PROGRESS i/4`` signal so the external
ledger records baseline completion without confusing cases with baselines.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BASELINE_ORDER = ("W0-LINX", "W1-PRYM", "W2-PRIMAT", "W3-ABCMB")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_mapping(values: list[str], option: str) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for value in values:
        baseline, separator, raw_path = value.partition("=")
        if not separator or not baseline or not raw_path:
            raise ValueError(f"{option} entries must use BASELINE=PATH")
        if baseline in mapping:
            raise ValueError(f"duplicate {option} entry for {baseline}")
        mapping[baseline] = Path(raw_path).resolve()
    if set(mapping) != set(BASELINE_ORDER):
        missing = sorted(set(BASELINE_ORDER) - set(mapping))
        extra = sorted(set(mapping) - set(BASELINE_ORDER))
        raise ValueError(f"{option} baseline mismatch: missing={missing}, extra={extra}")
    return mapping


def load_protocol(path: Path) -> dict[str, Any]:
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    if protocol.get("status") != "protocol_frozen_measurements_pending":
        raise ValueError("challenge protocol is not frozen")
    if tuple(protocol.get("baselines", {})) != BASELINE_ORDER:
        raise ValueError("challenge baseline order differs from the frozen suite")
    return protocol


def build_command(
    *,
    baseline: str,
    python: Path,
    source_dir: Path,
    environment_lock: Path,
    output_dir: Path,
    args: argparse.Namespace,
) -> list[str]:
    return [
        str(python),
        str(REPOSITORY_ROOT / "scripts/why_not_standard_challenge_grid.py"),
        "--baseline",
        baseline,
        "--config",
        str(args.config),
        "--cmb-config",
        str(args.cmb_config),
        "--neutron-config",
        str(args.neutron_config),
        "--parameter-schema",
        str(args.parameter_schema),
        "--observation-config",
        str(args.observation_config),
        "--source-dir",
        str(source_dir),
        "--inventory",
        str(args.inventory),
        "--environment-lock",
        str(environment_lock),
        "--output-dir",
        str(output_dir),
        "--hourly-price-cny",
        str(args.hourly_price_cny),
        "--yaml-python",
        str(args.yaml_python),
    ]


def run_command(command: list[str], log: TextIO) -> int:
    process = subprocess.Popen(
        command,
        cwd=REPOSITORY_ROOT,
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        log.write(line)
        log.flush()
    return process.wait()


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cmb-config", type=Path, required=True)
    parser.add_argument("--neutron-config", type=Path, required=True)
    parser.add_argument("--parameter-schema", type=Path, required=True)
    parser.add_argument("--observation-config", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--yaml-python", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hourly-price-cny", type=float, required=True)
    parser.add_argument("--baseline-python", action="append", default=[])
    parser.add_argument("--source-dir", action="append", default=[])
    parser.add_argument("--environment-lock", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.config = args.config.resolve()
    args.cmb_config = args.cmb_config.resolve()
    args.neutron_config = args.neutron_config.resolve()
    args.parameter_schema = args.parameter_schema.resolve()
    args.observation_config = args.observation_config.resolve()
    args.inventory = args.inventory.resolve()
    args.yaml_python = args.yaml_python.resolve()
    args.output_dir = args.output_dir.resolve()
    load_protocol(args.config)
    interpreters = parse_mapping(args.baseline_python, "--baseline-python")
    sources = parse_mapping(args.source_dir, "--source-dir")
    locks = parse_mapping(args.environment_lock, "--environment-lock")
    for mapping in (interpreters, sources, locks):
        for path in mapping.values():
            if not path.exists():
                raise FileNotFoundError(path)
    for path in (
        args.cmb_config,
        args.neutron_config,
        args.parameter_schema,
        args.observation_config,
        args.inventory,
        args.yaml_python,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "suite_id": "WHY-NOT-STANDARD-CHALLENGE-GRID-v1",
        "started_at_utc": utc_now(),
        "status": "in_progress",
        "baseline_order": list(BASELINE_ORDER),
        "baselines": {},
    }
    manifest_path = args.output_dir / "suite_manifest.json"
    write_manifest(manifest_path, manifest)

    for index, baseline in enumerate(BASELINE_ORDER, start=1):
        output_dir = args.output_dir / baseline
        command = build_command(
            baseline=baseline,
            python=interpreters[baseline],
            source_dir=sources[baseline],
            environment_lock=locks[baseline],
            output_dir=output_dir,
            args=args,
        )
        log_path = args.output_dir / f"{baseline}.log"
        started_at = utc_now()
        with log_path.open("w", encoding="utf-8") as log:
            return_code = run_command(command, log)
        manifest["baselines"][baseline] = {
            "command": command,
            "finished_at_utc": utc_now(),
            "log": log_path.name,
            "return_code": return_code,
            "started_at_utc": started_at,
        }
        write_manifest(manifest_path, manifest)
        if return_code != 0:
            manifest["status"] = "failed"
            manifest["failed_baseline"] = baseline
            manifest["finished_at_utc"] = utc_now()
            write_manifest(manifest_path, manifest)
            return return_code
        print(f"BASELINE_PROGRESS {index}/{len(BASELINE_ORDER)}", flush=True)

    manifest["status"] = "complete"
    manifest["finished_at_utc"] = utc_now()
    write_manifest(manifest_path, manifest)
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
