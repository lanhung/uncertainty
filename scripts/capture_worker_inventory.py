#!/usr/bin/env python3
"""Capture a machine-readable worker inventory without requiring project deps."""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def cpu_limits() -> dict[str, Any]:
    host_count = os.cpu_count()
    try:
        affinity_count = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        affinity_count = host_count

    quota_cpus: float | None = None
    cpu_max = read_text("/sys/fs/cgroup/cpu.max")
    if cpu_max:
        quota, _, period = cpu_max.partition(" ")
        if quota != "max" and period:
            try:
                quota_cpus = int(quota) / int(period)
            except (ValueError, ZeroDivisionError):
                pass
    else:
        quota = read_text("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
        period = read_text("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
        try:
            if quota is not None and period is not None and int(quota) > 0:
                quota_cpus = int(quota) / int(period)
        except (ValueError, ZeroDivisionError):
            pass

    candidates = [count for count in (host_count, affinity_count) if count]
    if quota_cpus is not None:
        candidates.append(max(1, math.ceil(quota_cpus)))
    effective_count = min(candidates) if candidates else None
    return {
        "host_logical_cpu_count": host_count,
        "affinity_cpu_count": affinity_count,
        "quota_cpu_count": quota_cpus,
        "effective_logical_cpu_count": effective_count,
    }


def memory_limit_bytes() -> int | None:
    value = read_text("/sys/fs/cgroup/memory.max")
    if value is None:
        value = read_text("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if value in (None, "max"):
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    # cgroup v1 uses a value close to 2**63 when no limit is configured.
    return None if parsed >= 2**60 else parsed


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

    limits = cpu_limits()
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
        # Keep this scheduling-facing field constrained to the container quota.
        "logical_cpu_count": limits["effective_logical_cpu_count"],
        "cpu_limits": limits,
        "memory_limit_bytes": memory_limit_bytes(),
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
