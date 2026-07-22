# Reproducible environments

This repository intentionally separates the always-on control environment from
the scientific environments used on elastic workers:

- the root `uv.lock` contains the control service and development checks;
- `solver-cpu/uv.lock` contains NumPy/SciPy, the FP64 JAX stack, PRIMAT and
  PRyMordial's Python-side dependencies;
- `train-gpu/uv.lock` contains the CUDA 13.0 PyTorch training stack.

All three environments require CPython 3.11.15. A lock records Python packages,
not native BBN solver source or compiler state. Each native solver must also
produce a `solver_card.yaml` with its source revision, compiler, flags, BLAS and
fixed-point regression results before production use.

On an AutoDL worker, run:

```bash
bash scripts/bootstrap_science_env.sh --kind solver-cpu
bash scripts/bootstrap_science_env.sh --kind train-gpu
```

The script installs the exact `uv` release into project-scoped persistent
storage, keeps package caches and virtual environments on the local data disk,
uses the checked-in lock with `--locked`, and writes a JSON smoke manifest into
project artifact storage. It never modifies a shared global Conda environment.

The train environment is intentionally NVIDIA/Linux-specific. CUDA
availability is mandatory for its worker smoke test. The solver environment
forces JAX CPU execution and enables 64-bit mode.
