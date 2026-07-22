#!/usr/bin/env python3
"""Emit a deterministic, auditable smoke manifest for a locked environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


SOLVER_PACKAGES = (
    "diffrax",
    "equinox",
    "interpax",
    "jax",
    "jaxlib",
    "numba",
    "numdifftools",
    "numpy",
    "primat",
    "PyYAML",
    "scipy",
    "vegas",
)
TRAIN_PACKAGES = (
    "arviz",
    "emcee",
    "h5py",
    "joblib",
    "matplotlib",
    "numpy",
    "pandas",
    "PyYAML",
    "scikit-learn",
    "scipy",
    "torch",
)


def package_versions(names: tuple[str, ...]) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in names:
        try:
            found[name] = version(name)
        except PackageNotFoundError as exc:
            raise RuntimeError(f"required distribution is missing: {name}") from exc
    return found


def command_line(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unavailable"
    return result.stdout.splitlines()[0].strip() if result.stdout else "unknown"


def rounded(values: Any) -> Any:
    """Normalize floats before cross-host comparison across BLAS implementations."""
    if isinstance(values, float):
        return round(values, 12)
    if isinstance(values, list):
        return [rounded(value) for value in values]
    if isinstance(values, dict):
        return {key: rounded(value) for key, value in values.items()}
    return values


def solver_result() -> dict[str, Any]:
    os.environ.setdefault("JAX_PLATFORMS", "cpu")
    import jax
    import jax.numpy as jnp
    import numpy as np
    import scipy.linalg

    jax.config.update("jax_enable_x64", True)
    matrix = np.array([[4.0, 1.0, 0.5], [1.0, 3.0, -0.25], [0.5, -0.25, 2.0]])
    vector = np.array([1.0, -2.0, 0.25])
    scipy_solution = scipy.linalg.solve(matrix, vector, assume_a="sym")
    jax_solution = jnp.linalg.solve(jnp.asarray(matrix), jnp.asarray(vector))
    return rounded(
        {
            "scipy_solution": scipy_solution.tolist(),
            "jax_solution": jax_solution.tolist(),
            "max_abs_difference": float(np.max(np.abs(scipy_solution - jax_solution))),
            "jax_x64": bool(jax.config.x64_enabled),
            "jax_backend": jax.default_backend(),
        }
    )


def train_result(allow_no_gpu: bool) -> dict[str, Any]:
    import torch

    cuda_available = torch.cuda.is_available()
    if not cuda_available and not allow_no_gpu:
        raise RuntimeError("CUDA is unavailable in the GPU training environment")
    device = torch.device("cuda" if cuda_available else "cpu")
    matrix = torch.tensor(
        [[4.0, 1.0, 0.5], [1.0, 3.0, -0.25], [0.5, -0.25, 2.0]],
        dtype=torch.float64,
        device=device,
    )
    vector = torch.tensor([1.0, -2.0, 0.25], dtype=torch.float64, device=device)
    solution = torch.linalg.solve(matrix, vector)
    if device.type == "cuda":
        torch.cuda.synchronize()
    props = torch.cuda.get_device_properties(0) if cuda_available else None
    return rounded(
        {
            "solution": solution.detach().cpu().tolist(),
            "dtype": str(solution.dtype),
            "device": str(device),
            "cuda_available": cuda_available,
            "torch_cuda": torch.version.cuda,
            "gpu_name": props.name if props else None,
            "gpu_memory_bytes": props.total_memory if props else None,
            "compute_capability": [props.major, props.minor] if props else None,
        }
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("solver-cpu", "train-gpu"), required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-no-gpu", action="store_true")
    args = parser.parse_args()

    if platform.python_version() != "3.11.15":
        raise RuntimeError(f"Python 3.11.15 is required, got {platform.python_version()}")
    if not args.lock.is_file():
        raise RuntimeError(f"lock file does not exist: {args.lock}")

    packages = SOLVER_PACKAGES if args.kind == "solver-cpu" else TRAIN_PACKAGES
    fixed_point = solver_result() if args.kind == "solver-cpu" else train_result(args.allow_no_gpu)
    comparison_payload = {
        "kind": args.kind,
        "python": platform.python_version(),
        "packages": package_versions(packages),
        "lock_sha256": sha256_file(args.lock),
        "fixed_point": fixed_point,
    }
    comparison_sha256 = hashlib.sha256(
        json.dumps(comparison_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    manifest = {
        "schema_version": 1,
        "status": "smoke_passed",
        "comparison_sha256": comparison_sha256,
        **comparison_payload,
        "host": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "gcc": command_line(["gcc", "--version"]),
            "gfortran": command_line(["gfortran", "--version"]),
        },
    }
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
