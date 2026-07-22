# AutoDL elastic worker inventory

Status date: 2026-07-22 UTC
Scope: public-safe scheduling and evidence inventory; no endpoint or credential data

The node names below identify physical allocations, not permanent scientific roles.
`solver`, `train`, and `verify` remain task-time labels assigned only after a resource
lease and a workload-specific benchmark.

| Stable node | Region | Lifecycle | Uncertainty acceptance | Current scheduling state |
|---|---|---|---|---|
| `autodl-westb-01` | westb | elastic, shared, may be powered off | CPU environment and source inventory accepted; GPU FP64 smoke passed; workload-specific GPU performance remains unmeasured | eligible only through the shared host-level lease; an exclusive `cpu-heavy` W1 lease was active at this status date |
| `autodl-bjb1-01` | bjb1 | elastic, shared, may be powered off | pending uncertainty hardware and environment capture | not eligible while external workloads are active; uncertainty started no process or lease |
| `autodl-bjb1-02-spare` | bjb1 | optional elastic spare, shared, may be powered off | pending uncertainty hardware and environment capture | not eligible while external services are active; uncertainty started no process or lease |

## Accepted westb capture

The host capture was written on the worker at
`/root/autodl-fs/projects/uncertainty/artifacts/worker-inventory.json`. Its raw
SHA-256 is
`8af7676442b166e552e102f5520e2a08f6642c29af295e0a0c08e816ed849cd8`.
The raw file is intentionally not published because it includes ephemeral hostname
and GPU UUID fields. The public-safe fields are:

| Field | Captured value |
|---|---|
| capture time | `2026-07-21T18:13:28.708546+00:00` |
| platform | Linux 5.15.0-78, x86-64, glibc 2.35 |
| effective CPU allocation | 25 logical CPUs; cgroup quota 25 on a 208-logical-CPU host |
| memory limit | 98,784,247,808 bytes (92 GiB) |
| root filesystem | 32,212,254,720 bytes (30 GiB) total |
| `/root/autodl-tmp` | 53,687,091,200 bytes (50 GiB) total; rebuildable project scratch only |
| `/root/autodl-fs` | 214,748,364,800 bytes (200 GiB) total; regional persistent project state |
| host-visible GPU label | `NVIDIA GeForce RTX 4090` |
| host-visible GPU memory | 49,140 MiB reported by `nvidia-smi`; 50,864,390,144 bytes reported by PyTorch |
| driver / compute capability | driver 580.105.08; compute capability 8.9 |

The 49,140 MiB allocation is a platform-visible vGPU configuration. The label must
not be interpreted as proof of the memory capacity or FP64 throughput of a retail
physical RTX 4090. Scheduling decisions use measured workload benchmarks.

The project-locked GPU environment separately passed a CUDA FP64 fixed-point smoke
with PyTorch `2.12.1+cu130`. That evidence is committed at
`artifacts/environments/environment-train-gpu-autodl-westb-01.json`. It proves only
that the locked environment can execute a finite FP64 CUDA calculation; it is not a
throughput, numerical-convergence, or production-training acceptance result.

## Storage and regional boundaries

- System root is not an artifact store.
- `/root/autodl-tmp/projects/uncertainty` holds repositories, environments, scratch,
  and other reproducible data.
- `/root/autodl-fs/projects/uncertainty` holds checkpoints, manifests, run state,
  logs, and artifacts that must survive instance recycling.
- westb and bjb1 persistent stores are independent regional domains. No shared-path
  assumption is permitted.
- Large cross-region transfers require an object-store manifest and checksums;
  neither the control host nor worker-to-worker SSH is the default data bus.

## Acceptance boundaries

This inventory does not make either bjb1 node available and does not grant a
production role to westb. Before a pending node becomes eligible, capture its raw
inventory, validate the project environment, verify storage mounts, inspect active
external workloads, and acquire the appropriate host-level lease. Production solver
or training cost claims additionally require cold/warm throughput, failure accounting,
precision checks, and a source-backed entry in `docs/compute/solver_throughput.csv`.
