# UQ0 public solver baselines v1

Status: three public forward paths accepted for UQ0; production acceptance is not implied

Captured: 2026-07-23

Task: `UQ0-PUBLIC-SOLVER-BASELINES`

## Decision

Three previously executed, exact-source public paths meet the deliberately
narrow UQ0 baseline contract in `SCIENCE_CRITICAL_PATH_v3.md`. Each has a full
source revision, license, environment lock, float64 standard-point output for
`Y_p` and `D/H`, structured failure ledger, measured runtime, and source/config
hashes.

| UQ0 path | Exact public source | Accepted forward configuration | `Y_p` | `D/H` | Warm scalar |
|---|---|---|---:|---:|---:|
| `UQ0-S6-LINX-key-PRIMAT-2023-v1` | LINX `ec2e9d2ca455e8204137e884da29f5dd13a638fa` | `key_PRIMAT_2023`, FP64, `rtol=1e-8`, `atol=1e-11`, `sampling_nTOp=2400`, `max_steps=16384` | 0.2466565317 | `2.4417232841e-5` | 2.34755 s/point |
| `UQ0-S4-PRyMordial-small-PRIMAT-like-v1` | PRyMordial `725d8a8db3ad5ea2630580d825c9d0d69ed76533` | Python small 12-reaction network, PRIMAT-like rates, FP64 | 0.2468834991 | `2.4441162056e-5` | 5.90683 s/point |
| `UQ0-S8-PRIMAT-small-C-v1` | PRIMAT `21ff8f39fa18e3937e9fdf386cfa982361bfdfce` | exact-checkout compiled C backend, small network, FP64 | 0.2469551308 | `2.4447361728e-5` | 0.06387 s/point |

The input point is bound to the preserved historical schema snapshot with
SHA-256 `61dc9c3ec1fdc9eb455f9ed64ad604a49d801e2b7de361db8db74a883b8c3c9e`:
`Omega_b h^2=0.02237`, `Delta N_eff=0`, `tau_n=878.3 s`. The current UQ-only
schema is not retroactively substituted into these runs.

Machine-readable records are:

- `configs/solvers/public_bbn_baselines_UQ0_v1.yaml`;
- `configs/solvers/cards/UQ0-S6-LINX-key-PRIMAT-2023-v1.yaml`;
- `configs/solvers/cards/UQ0-S4-PRyMordial-small-PRIMAT-like-v1.yaml`;
- `configs/solvers/cards/UQ0-S8-PRIMAT-small-C-v1.yaml`.

Validate all hashes and minimum fields with:

```bash
python scripts/validate_uq0_solver_baselines.py
```

## Why the three paths qualify

The LINX runtime slice originally exposed a scalar/native-batch discrepancy.
It is not used as the acceptance evidence. The later frozen V4 convergence
rerun established a local numerical plateau and supplies the strict accepted
standard-point values and timings. This is forward-only evidence; the separate
gradient audit remained a structured negative result.

PRyMordial and PRIMAT each completed 30 scalar and 30 sequential 64-point
timing repetitions with zero observed structured failures and zero output
drift. Their empty `failures.jsonl` files are hash-bound evidence of zero
observed failures; the harness rejects non-finite results and serializes
exceptions rather than treating a zero process exit as sufficient.

## Acceptance boundary and remaining work

This closes only the evidence gap for three executable public **forward
baseline paths**. It does not establish a UQ result and must not be counted as
the paused W0-W3 challenge or a production Gate.

The next mandatory steps remain:

1. register numerical R0 priors and exact per-solver mappings for
   `d(p,gamma)3He`, `d(d,n)3He`, and `d(d,p)t`;
2. register weak/neutron handling without double counting;
3. implement the common `simulate(theta,z,tau_n,solver,network,precision)`
   adapter for all three paths;
4. execute central and symmetric `z=+/-1` regressions, including deliberately
   invalid-input structured-failure tests;
5. only later test parameter-region accuracy, matched-physics cross-solver
   fidelity and posterior recovery.

In particular, LINX gradients/HMC remain prohibited, PRyMordial's rate
marginalization has not been exercised through the common adapter, and PRIMAT
has not yet covered the posterior/adversarial point requirements. None of
those limitations invalidate the narrow UQ0 forward-path baseline, and none
may be silently dropped from later production acceptance.
