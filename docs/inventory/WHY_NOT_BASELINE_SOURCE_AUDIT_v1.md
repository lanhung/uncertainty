# WHY-NOT baseline source audit v1

Status: exact sources acquired; executable environments pending

Captured: 2026-07-22

Task: `P0-WHY-NOT-01` / `P0-env-lock`

## Result

The four mandatory sources were cloned into a fresh temporary directory by
`scripts/fetch_why_not_baselines.sh`. Every checkout resolved to the commit
frozen in `configs/benchmarks/why_not_existing_solvers_v1.yaml`; submodules were
initialized recursively. No scientific runtime measurement was performed.

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

Both locks resolve locally and are included in `make lock-check`; neither is
accepted for timing until it installs and passes an FP64 source-level smoke test
on an available worker.

The ABCMB bundled LINX tree has Git tree
`59b3ab7b3ada7d7ff6484920e0e29291cf4a084e`. It must be compared against
W0-LINX; shared naming does not establish source or numerical equivalence.

## Scientific boundary

Source acquisition and dependency inspection do not answer the WHY-NOT
questions. `P0-WHY-NOT-01` remains incomplete until the registered timings,
gradient checks, posterior recovery and workload projections exist.
