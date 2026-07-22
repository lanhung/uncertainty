# WHY-NOT baseline source audit v1

Status: exact sources acquired; direct forward smokes executed on westb

Captured: 2026-07-22

Task: `P0-WHY-NOT-01` / `P0-env-lock`

## Result

The four mandatory sources were cloned into a fresh temporary directory by
`scripts/fetch_why_not_baselines.sh`. Every checkout resolved to the commit
frozen in `configs/benchmarks/why_not_existing_solvers_v1.yaml`; submodules were
initialized recursively. Environment smokes were followed by direct upstream
forward executions for LINX and PRyMordial; these single-run observations are
not the registered repeated benchmark.

| Baseline | Exact source | License | Environment finding |
|---|---|---|---|
| LINX | `ec2e9d2ca455e8204137e884da29f5dd13a638fa` | MIT | `requirements-fast.txt` pins JAX/JAXlib 0.4.28, Diffrax 0.6.0 and Equinox 0.11.10; interpax 0.3.1 must be installed without dependency resolution according to upstream |
| PRyMordial | `725d8a8db3ad5ea2630580d825c9d0d69ed76533` | GPL-3.0 | no package metadata or lock; README declares NumPy/SciPy mandatory and Numba/Numdifftools/Vegas recommended |
| PRIMAT | `21ff8f39fa18e3937e9fdf386cfa982361bfdfce` | GPL-3.0-or-later | v0.3.2 declares Python >=3.10 with a lean NumPy/SciPy core; exact source install must be tested rather than silently substituting an unverified wheel |
| ABCMB | `5eabbab4ed7e53f264e16024743d1ba517845c37` | MIT | setup pins JAX 0.8.1, Equinox 0.13.2 and Optimistix 0.0.11; repository vendors a LINX tree rather than depending on the W0 checkout |

Exact license and dependency-file hashes are recorded in
`manifests/software/why_not_baselines_v1.yaml`.

## Environment consequence

The current general `environments/solver-cpu` lock uses JAX 0.7.2. It is useful
for project adapter development, but it is not an exact reproduction
environment for either LINX's fast pin (0.4.28) or ABCMB's pin (0.8.1).
Installing all competitors into one environment would therefore measure an
unregistered hybrid dependency state.

Before timing, create separate immutable environments for:

1. exact LINX v0.1.2 fast dependencies;
2. ABCMB v0.3.1 and its bundled LINX;
3. PRyMordial/PRIMAT CPU baselines, initially from the existing solver lock but
   installed from the frozen source commits and accepted only after smoke tests.

The first two dedicated resolver locks are now checked in:

- `environments/linx-v0.1.2/uv.lock` freezes the upstream fast dependency set;
  `interpax==0.3.1` remains a required hash-verified `--no-deps` sidecar because
  upstream simultaneously pins NumPy 2.4.6 while interpax metadata requires
  NumPy below 2.0;
- `environments/abcmb-v0.3.1/uv.lock` freezes ABCMB at its Git commit with JAX
  0.8.1, Optimistix 0.0.11, resolved Diffrax 0.7.1 and Interpax 0.3.14.

Both locks resolve locally, are included in `make lock-check`, and passed FP64
source-level smoke tests on `autodl-westb-01`. PRyMordial loaded its 63-reaction
source tables, and PRIMAT built its C backend from the exact frozen checkout and
returned finite physical abundances in a small-network smoke run. The raw
manifests are under `artifacts/environments/`.

The ABCMB bundled LINX tree has Git tree
`59b3ab7b3ada7d7ff6484920e0e29291cf4a084e`. It must be compared against
W0-LINX; shared naming does not establish source or numerical equivalence.

## Direct execution consequence

LINX's upstream standard-BBN forward script completed and agreed with its
embedded PRIMAT references below the script's 0.3% threshold. Its gradient
check, however, produced one `NaN` component and is rejected even though the
upstream process returned exit code zero. PRyMordial's small and large Python
network paths both completed with finite abundances. Exact values, timings and
raw logs are recorded in `docs/inventory/DIRECT_SOLVER_EXECUTION_v1.md` and
`artifacts/solver-build/DIRECT_SOLVER_SMOKE_v1.json`.

The first registered common-harness slice has since completed for W2 PRIMAT at
the frozen standard-BBN point. It contains every observation for 30 scalar and
30 sequential 64-point timing repetitions with zero structured failures. See
`docs/inventory/WHY_NOT_PRIMAT_RUNTIME_v1.md`. This is a runtime slice, not a
completed baseline or posterior-fidelity result.

W0 LINX has also completed the common standard-fiducial runtime slice. Its
native `jit(vmap)` path is substantially faster per point than its scalar path,
but identical inputs produced a small scalar/batch abundance discrepancy. The
result is registered as open pending a tolerance scan rather than promoted to a
fidelity pass. See `docs/inventory/WHY_NOT_LINX_RUNTIME_v1.md`.

## Scientific boundary

Source acquisition, dependency inspection and one-off upstream runs do not
answer the WHY-NOT questions. `P0-WHY-NOT-01` remains incomplete until the
registered repeated timings, accepted gradient checks, posterior recovery and
workload projections exist.
