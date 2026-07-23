#!/usr/bin/env python3
"""Run the pre-registered strict LINX native-q convergence rerun."""

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import run_linx_native_q_reproduction as runner


runner.ARTIFACT_ID = "LINX-NATIVE-Q-REPRODUCTION-v2"
runner.EXPECTED_CONFIG_SHA256 = (
    "f8415100950cecaedecc7baed30a5d3f903833a1247922911c5de5c0748e93e3"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
