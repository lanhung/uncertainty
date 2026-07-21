#!/usr/bin/env python3
"""Capture a machine-readable worker inventory without requiring project deps."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "error": str(exc)}
    return {
        "available": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def torch_inventory() -> dict[str, Any]:
    try:
        import torch  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"available": False, "error": repr(exc)}

    devices: list[dict[str, Any]] = []
    for index in range(torch.cuda.device_count()):
        properties = torch.cuda.get_device_properties(index)
        devices.append(
            {
                "index": index,
                "name": properties.name,
                "total_memory_bytes": properties.total_memory,
                "compute_capability": [properties.major, properties.minor],
                "multi_processor_count": properties.multi_processor_count,
            }
        )
    return {
        "available": True,
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "cudnn_version": torch.backends.cudnn.version(),
        "devices": devices,
    }


def disk_inventory(path: str) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.exists():
        return {"exists": False}
    usage = shutil.disk_usage(candidate)
    return {
        "exists": True,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--node-name", default=os.environ.get("AUTODL_NODE_NAME"))
    parser.add_argument("--region", default=os.environ.get("AUTODL_REGION"))
    args = parser.parse_args()

    payload: dict[str, Any] = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "node_name": args.node_name or socket.gethostname(),
        "region": args.region or "unknown",
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "platform": platform.platform(),
        "kernel": platform.release(),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
        },
        "logical_cpu_count": os.cpu_count(),
        "lscpu": run(["lscpu"]),
        "memory": run(["free", "-b"]),
        "nvidia_smi": run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,uuid,memory.total,driver_version,compute_cap",
                "--format=csv,noheader,nounits",
            ]
        ),
        "torch": torch_inventory(),
        "storage": {
            "/": disk_inventory("/"),
            "/root/autodl-tmp": disk_inventory("/root/autodl-tmp"),
            "/root/autodl-fs": disk_inventory("/root/autodl-fs"),
        },
        "environment_hints": {
            key: os.environ.get(key)
            for key in (
                "CUDA_VISIBLE_DEVICES",
                "OMP_NUM_THREADS",
                "MKL_NUM_THREADS",
                "RESEARCH_OPS_PROJECT",
                "RESEARCH_OPS_OWNER",
            )
            if os.environ.get(key) is not None
        },
    }

    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(args.output)
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
