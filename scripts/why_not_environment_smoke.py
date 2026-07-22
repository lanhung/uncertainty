#!/usr/bin/env python3
"""Smoke exact WHY-NOT sources without treating the result as a benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


BASELINES = {
    "W0-LINX": ("LINX", "ec2e9d2ca455e8204137e884da29f5dd13a638fa"),
    "W1-PRYM": ("PRyMordial", "725d8a8db3ad5ea2630580d825c9d0d69ed76533"),
    "W2-PRIMAT": ("PRIMAT", "21ff8f39fa18e3937e9fdf386cfa982361bfdfce"),
    "W3-ABCMB": ("ABCMB", "5eabbab4ed7e53f264e16024743d1ba517845c37"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError as exc:
        raise RuntimeError(f"required distribution is missing: {name}") from exc


def fp64_result() -> dict[str, Any]:
    import numpy as np

    matrix = np.array([[4.0, 1.0], [1.0, 3.0]], dtype=np.float64)
    solution = np.linalg.solve(matrix, np.array([1.0, 2.0], dtype=np.float64))
    return {"dtype": str(solution.dtype), "solution": solution.tolist()}


def smoke_linx(source: Path) -> dict[str, Any]:
    os.environ.setdefault("JAX_PLATFORMS", "cpu")
    sys.path.insert(0, str(source))
    import jax
    from linx.nuclear import NuclearRates

    jax.config.update("jax_enable_x64", True)
    rates = NuclearRates(nuclear_net="key_PRIMAT_2023")
    return {
        "jax": package_version("jax"),
        "jax_x64": bool(jax.config.x64_enabled),
        "network": "key_PRIMAT_2023",
        "reaction_count": len(rates.reactions),
    }


def smoke_prymordial(source: Path) -> dict[str, Any]:
    previous = Path.cwd()
    os.chdir(source)
    sys.path.insert(0, str(source))
    try:
        import PRyM.PRyM_init as config
    finally:
        os.chdir(previous)
    return {
        "numpy": package_version("numpy"),
        "scipy": package_version("scipy"),
        "reaction_count": int(config.num_reactions),
        "tau_n_seconds": float(config.tau_n / config.second),
    }


def smoke_primat() -> dict[str, Any]:
    from primat.backend import run_bbn

    result = run_bbn({"Omegabh2": 0.02242, "network": "small"})
    yp = float(result["YPBBN"])
    deuterium = float(result["DoH"])
    if not (math.isfinite(yp) and 0.2 < yp < 0.3):
        raise RuntimeError(f"nonphysical PRIMAT helium smoke result: {yp}")
    if not (math.isfinite(deuterium) and 1e-5 < deuterium < 5e-5):
        raise RuntimeError(f"nonphysical PRIMAT deuterium smoke result: {deuterium}")
    return {"primat": package_version("primat"), "YPBBN": yp, "DoH": deuterium}


def smoke_abcmb() -> dict[str, Any]:
    import jax
    from abcmb.linx.nuclear import NuclearRates

    jax.config.update("jax_enable_x64", True)
    rates = NuclearRates(nuclear_net="key_PRIMAT_2023")
    return {
        "ABCMB": package_version("ABCMB"),
        "jax": package_version("jax"),
        "jax_x64": bool(jax.config.x64_enabled),
        "bundled_linx_network": "key_PRIMAT_2023",
        "reaction_count": len(rates.reactions),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", choices=tuple(BASELINES), required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if platform.python_version() != "3.11.15":
        raise RuntimeError(f"Python 3.11.15 is required, got {platform.python_version()}")
    if not args.lock.is_file():
        raise RuntimeError(f"lock file does not exist: {args.lock}")

    source_name, expected_revision = BASELINES[args.baseline]
    source = args.source_root / source_name
    actual_revision = git_head(source)
    if actual_revision != expected_revision:
        raise RuntimeError(
            f"source revision mismatch for {source_name}: {actual_revision} != {expected_revision}"
        )

    if args.baseline == "W0-LINX":
        source_result = smoke_linx(source)
    elif args.baseline == "W1-PRYM":
        source_result = smoke_prymordial(source)
    elif args.baseline == "W2-PRIMAT":
        source_result = smoke_primat()
    else:
        source_result = smoke_abcmb()

    manifest = {
        "schema_version": 1,
        "status": "source_smoke_passed",
        "scientific_use": "environment_acceptance_only_not_a_benchmark",
        "baseline": args.baseline,
        "python": platform.python_version(),
        "lock_sha256": sha256_file(args.lock),
        "source": {
            "name": source_name,
            "revision": actual_revision,
        },
        "fp64": fp64_result(),
        "source_result": source_result,
        "host": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
