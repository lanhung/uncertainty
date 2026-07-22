#!/usr/bin/env python3
"""Perform a structural, safe-load audit of the pinned SageNet checkpoints.

This is not an accuracy benchmark. It verifies provenance, refuses unrestricted
pickle loading, requires an exact state-dict match, and checks only that a zero
input produces a finite tensor of the registered shape.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import re
import subprocess
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.preprocessing import StandardScaler


SAGENET_COMMIT = "ab7face439b5ad47a8551d61e1a3fbdfd2d0ac55"
CHECKPOINTS = {
    "CosmicNet2": {
        "filename": "best_gw_model_CosmicNet2.pth",
        "sha256": "d3f3ca4320229a6e4dcb2ebd0a84f1ef6920e21357c6a93200d1b2e4adfd016c",
        "serialized_sklearn": "1.2.2",
        "class_name": "CosmicNet2",
    },
    "LSTM": {
        "filename": "best_gw_model_LSTM.pth",
        "sha256": "6c1066ba4b74d283f6d451346aa40a23062ad81feeec0bcbbbace1548a3ab343",
        "serialized_sklearn": "1.6.1",
        "class_name": "LSTM",
    },
    "RNN": {
        "filename": "best_gw_model_RNN.pth",
        "sha256": "19f4812cec55f60eca32df73b4a98a4b7477a0b401aadd86bf37e84ad38e6a3b",
        "serialized_sklearn": "1.2.2",
        "class_name": "RNN",
    },
    "Transformer": {
        "filename": "best_gw_model_Transformer.pth",
        "sha256": "95d87b483472fd4a73f6de5ba85213358ed138bf75a2d26d8bd1ce4181a6d485",
        "serialized_sklearn": "1.6.1",
        "class_name": "Former",
    },
}
EXPECTED_UNSAFE_GLOBALS = {
    "numpy.ndarray",
    "numpy.dtype",
    "numpy.core.multiarray.scalar",
    "numpy.core.multiarray._reconstruct",
    "numpy._core.multiarray.scalar",
    "numpy._core.multiarray._reconstruct",
    "sklearn.preprocessing._data.StandardScaler",
}
VERSION_PATTERN = re.compile(r"from version ([^ ]+) when using version")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _safe_globals() -> list[Any]:
    try:
        multiarray = importlib.import_module("numpy._core.multiarray")
    except ModuleNotFoundError:  # NumPy 1.x
        multiarray = importlib.import_module("numpy.core.multiarray")

    reconstruct = multiarray._reconstruct
    scalar = multiarray.scalar
    return [
        np.ndarray,
        np.dtype,
        type(np.dtype(np.float64)),
        type(np.dtype(np.int64)),
        reconstruct,
        (reconstruct, "numpy.core.multiarray._reconstruct"),
        (reconstruct, "numpy._core.multiarray._reconstruct"),
        scalar,
        (scalar, "numpy.core.multiarray.scalar"),
        (scalar, "numpy._core.multiarray.scalar"),
        StandardScaler,
    ]


def _load_models_module(root: Path) -> Any:
    source = root / "sagenetgw" / "models.py"
    spec = importlib.util.spec_from_file_location("pinned_sagenet_models", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import model source: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(root: Path) -> dict[str, Any]:
    head = _git_head(root)
    if head != SAGENET_COMMIT:
        raise RuntimeError(f"SageNet commit mismatch: expected {SAGENET_COMMIT}, got {head}")

    models_module = _load_models_module(root)
    model_dir = root / "sagenetgw" / "models"
    results: dict[str, Any] = {}

    for name, record in CHECKPOINTS.items():
        path = model_dir / record["filename"]
        observed_hash = _sha256(path)
        if observed_hash != record["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch for {path}")

        unsafe = set(torch.serialization.get_unsafe_globals_in_checkpoint(path))
        unexpected = sorted(unsafe - EXPECTED_UNSAFE_GLOBALS)
        if unexpected:
            raise RuntimeError(f"unexpected pickle globals in {path}: {unexpected}")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", InconsistentVersionWarning)
            with torch.serialization.safe_globals(_safe_globals()):
                checkpoint = torch.load(path, map_location="cpu", weights_only=True)

        warning_versions = sorted(
            {
                match.group(1)
                for item in caught
                if isinstance(item.message, InconsistentVersionWarning)
                if (match := VERSION_PATTERN.search(str(item.message))) is not None
            }
        )
        if warning_versions and warning_versions != [record["serialized_sklearn"]]:
            raise RuntimeError(
                f"unexpected serialized scikit-learn version for {name}: {warning_versions}"
            )

        if sorted(checkpoint) != ["model_state", "param_scaler", "x_scaler", "y_scaler"]:
            raise RuntimeError(f"unexpected checkpoint keys for {name}: {sorted(checkpoint)}")
        for scaler_name, expected_features in (
            ("x_scaler", 1),
            ("y_scaler", 1),
            ("param_scaler", 9),
        ):
            scaler = checkpoint[scaler_name]
            if type(scaler) is not StandardScaler or scaler.n_features_in_ != expected_features:
                raise RuntimeError(f"invalid {scaler_name} in {name}")

        model_class = getattr(models_module, record["class_name"])
        model = model_class()
        model.load_state_dict(checkpoint["model_state"], strict=True)
        model.eval()
        with torch.inference_mode():
            output = model(torch.zeros((1, 9), dtype=torch.float32))
        if tuple(output.shape) != (1, 256, 2) or not bool(torch.isfinite(output).all()):
            raise RuntimeError(f"invalid structural forward output for {name}")

        results[name] = {
            "sha256": observed_hash,
            "safe_weights_only_load": True,
            "state_dict_strict_match": True,
            "output_shape": list(output.shape),
            "output_finite": True,
            "serialized_sklearn": record["serialized_sklearn"],
            "version_warning_observed": bool(warning_versions),
        }

    return {
        "schema_version": 1,
        "validation_kind": "structural_only_not_accuracy",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sagenet_commit": head,
        "environment": {
            "python": __import__("sys").version.split()[0],
            "torch": torch.__version__,
            "numpy": np.__version__,
            "scikit_learn": __import__("sklearn").__version__,
        },
        "models": results,
        "scientific_output_equivalence_validated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sagenet_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate(args.sagenet_root.resolve())
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
