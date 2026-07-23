#!/usr/bin/env python3
"""Validate the strict LINX native-q convergence rerun fail-closed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import validate_linx_native_q_reproduction as validator


validator.ARTIFACT_ID = "LINX-NATIVE-Q-REPRODUCTION-v2"
validator.EXPECTED_CONFIG_SHA256 = (
    "f8415100950cecaedecc7baed30a5d3f903833a1247922911c5de5c0748e93e3"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/benchmarks/linx_native_q_reproduction_v2.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(validator.validate(args.artifact, args.config), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
