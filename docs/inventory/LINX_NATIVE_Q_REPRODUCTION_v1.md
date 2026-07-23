# LINX native `nuclear_rates_q` abundance reproduction v1

Status: **executed; frozen acceptance failed**

The registered worker run completed all 42 scalar rows and 28 heterogeneous
batch rows with zero structured failures and zero repeat drift. Scalar/batch
agreement passed at `0.00036123` observation sigma, the weak-rate-sampling
plateau passed at `0.00076602` sigma, and all three R0 D/H responses were
nonzero and straddled the central prediction. The tolerance plateau reached
`0.00124645` observation sigma, exceeding the frozen `0.001` threshold, so the
baseline is not accepted and grants no task progress. Thresholds were not
relaxed after observing the result. The immutable evidence digest is
`4ddc1ce6cc75ac618a1c23c5b03a31ed9fc2d5cefa3c08ee95c95e788119ae5f`.

This baseline exercises LINX v0.1.2 at revision
`ec2e9d2ca455e8204137e884da29f5dd13a638fa` with the `key_recommended`
network and JAX FP64 CPU execution. It is deliberately an abundance-level
calibration of LINX's native scalar rate-envelope coordinates, not a project
nuclear-prior selection.

## Registered experiment

At the frozen standard-BBN point, the runner evaluates seven 12-component
`nuclear_rates_q` vectors:

- the all-zero central vector;
- `q=-1,+1` for `d(p,gamma)3He` at native index 1;
- `q=-1,+1` for `d(d,n)3He` at native index 2;
- `q=-1,+1` for `d(d,p)t` at native index 3.

Every non-R0 coordinate remains zero. The same background solution is reused
across all q vectors. Three preregistered numerical cases each run the seven
vectors twice, yielding 42 scalar rows. The candidate case also runs a
14-member heterogeneous `jax.jit(jax.vmap(...))` batch twice, yielding 28
stored batch rows. A cold compile batch is timed but is not counted as
measurement evidence.

The accepted artifact must independently establish:

1. complete, duplicate-free scalar and heterogeneous-batch grids;
2. finite abundances and a positive proton denominator for every row;
3. exactly zero scalar-repeat and batch-repeat drift;
4. candidate scalar/batch agreement within `0.01` frozen observation sigma;
5. tolerance and weak-rate-sampling plateaus within `0.001` observation sigma;
6. nonzero D/H responses for each R0 rate, with the central value between its
   registered `-1` and `+1` results;
7. zero structured solver failures and complete timing/resource provenance.

The validator recomputes all decisions from raw rows and checks the hashes of
the run manifest, results, resource report, timing ledger, and empty failure
ledger. It does not accept a stored `passed` flag as evidence.

## Execution interface

The long run belongs under the host-level `cpu-heavy` resource lease and the
project heartbeat/checkpoint wrapper. The runner itself is:

```bash
python scripts/run_linx_native_q_reproduction.py \
  --config configs/benchmarks/linx_native_q_reproduction_v1.yaml \
  --parameter-schema configs/physics/parameter_schema.yaml \
  --observation-config configs/data/abundance_OBS-v1.yaml \
  --mapping-artifact artifacts/priors/LINX-R0-MAPPING-REGRESSION-v1/regression.json \
  --source-dir /path/to/frozen/LINX \
  --inventory /path/to/worker-inventory.json \
  --environment-lock environments/linx-v0.1.2/uv.lock \
  --output-dir /new/artifact/directory \
  --hourly-price-cny PRICE
```

After copying the immutable result into the repository, validation is:

```bash
python scripts/validate_linx_native_q_reproduction.py \
  artifacts/benchmarks/LINX-NATIVE-Q-REPRODUCTION-v1/reproduction.json
```

## Claim boundary

A full pass grants one `UQ0-NATIVE-UQ-REPRO` calibration unit at claim level
`C0`. It does **not**:

- reconstruct the ETR25 actual/posterior rate PDF;
- choose `NUC-v1` or authorize the production nuisance adapter;
- validate gradients, Fisher information, HMC, or posterior marginalization;
- establish cross-solver engine discrepancy;
- provide A00/A03/A09 scientific or independent-validation signatures;
- support novelty or priority claims.

Any missing row, source or environment drift, companion hash mismatch,
structured failure, numerical threshold failure, or scope overclaim leaves the
baseline unaccepted.
