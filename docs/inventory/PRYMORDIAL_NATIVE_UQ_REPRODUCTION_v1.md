# PRyMordial native abundance-UQ reproduction v1

Status: **executed; accepted as one C0 native-UQ calibration baseline**

The corrected registered worker run completed 1,000/1,000 draws with zero
failures and zero sentinel replay drift. Relative to the frozen public table,
the reproduced standard deviations have ratios `1.0136627679` for `Yp_BBN`
and `1.0173054838` for `D/H`; all preregistered bootstrap, central, median,
failure-fraction and finite-output checks passed. The accepted summary SHA256
is `5b538f1df900b00a33eaba7521d6946d570964bb6a08556185b7f8e44fb40b37`.

## Scope

This protocol reproduces one public PRyMordial abundance Monte Carlo
statistically. It is an upstream `C0` calibration baseline for
`UQ0-NATIVE-UQ-REPRO`; it is not the project's R0 prior, an ETR25 posterior
reconstruction, a cosmological-posterior reproduction, or production truth.

The frozen source is `vallima/PRyMordial` revision
`725d8a8db3ad5ea2630580d825c9d0d69ed76533`. The registered public row is
conditioned on

```text
Omega_b h^2 = 0.0222
Delta N_eff = 0
```

and reports

```text
Yp_BBN = 0.24677515532524957
sigma(Yp_BBN) = 1.3508787327181341e-4
D/H = 2.5390204658712323e-5
sigma(D/H) = 9.993016856744879e-7
```

The public table does not publish its Monte Carlo seed, draw manifest, or
joint covariance. Exact draw-wise reproduction is therefore impossible. The
registered comparison is deliberately statistical.

## Frozen native model

The run uses the upstream 63-reaction network, NACRE-II key rates, and
PRyMordial's native independent standard-normal `p_*` parameters for all 63
rates. It independently samples

```text
tau_n ~ Normal(878.4 s, 0.5^2 s^2)
```

while holding the baryon density and `Delta N_eff` fixed. Every process
explicitly resets all 63 `p_*` values, all 63 `NP_delta_*` values, weak and
nuclear new-physics flags, network selection, cosmology, and neutron lifetime
before constructing a fresh `PRyMclass`. Key rates are reloaded only after
`nacreii_flag=True` has been assigned.

PRyMordial stores these inputs in module globals. Threads are therefore
prohibited. The runner uses a spawn-based `ProcessPoolExecutor` with one
BLAS/OpenMP/Numba thread per process. Reused processes are safe only because
the complete mutable input contract is reassigned for every draw; three
registered draws are also replayed as deterministic sentinels.

## Deterministic draw and failure contract

Before any solver call, the runner writes all 1,000 latent draws to
`draw_manifest.jsonl`. Draw `i` is generated from child `i` of NumPy
`SeedSequence(240701)` with `PCG64DXSM`; the neutron lifetime is drawn first,
followed by the ordered 63-vector. Each JSONL record has a canonical SHA-256
digest.

There is no failure replacement. Every registered draw has exactly one
terminal record in either `results.jsonl` or `failures.jsonl`. Both files are
append-only and fsynced. After every terminal draw, `run_state.json` is
atomically replaced and the runner emits absolute `PROGRESS i/1000`.

Resume is fail-closed:

- the config digest, source revision and bytes, clean source worktree,
  environment, immutable draw manifest, and run ID must still match;
- partial JSONL records, altered record digests, duplicate terminal outcomes,
  unknown draw IDs, or changed latent ordering abort the resume;
- terminal JSONL records are authoritative if a crash occurred after a record
  fsync but before the next atomic state replacement.

## Registered execution

The first run on the leased worker is:

```bash
scripts/with_resource_lease.sh \
  --resource cpu-heavy \
  --project uncertainty \
  --task UQ0-NATIVE-UQ-REPRO \
  -- \
  python worker/run_with_heartbeat.py \
    --task UQ0-NATIVE-UQ-REPRO \
    --total 5 \
    --unit baselines \
    --progress-regex 'BASELINE_PROGRESS\s+([0-9]+)/([0-9]+)' \
    --success-event progress \
    --success-current <ACCEPTED_BASELINE_COUNT> \
    --resume \
    -- \
    python scripts/run_prymordial_native_uq_reproduction.py \
      --source-root /path/to/frozen/PRyMordial \
      --output-dir /persistent/path/PRYMORDIAL-NATIVE-UQ-REPRODUCTION-v1 \
      --workers 20
```

The nonterminal success event records the absolute accepted-baseline count
without marking the parent five-baseline science task done. Draw-level
progress remains in the persistent runner state and log; it is deliberately
not confused with the parent task's scientific acceptance count.

After an interrupted attempt, use the identical command and add `--resume` to
the final runner invocation. The runner refuses a nonempty output directory
without a valid run manifest and refuses an existing valid run unless resume
was explicitly requested.

Validate the completed directory independently:

```bash
python scripts/validate_prymordial_native_uq_reproduction.py \
  /persistent/path/PRYMORDIAL-NATIVE-UQ-REPRODUCTION-v1
```

The six required files are:

```text
run_manifest.json
draw_manifest.jsonl
results.jsonl
failures.jsonl
run_state.json
summary.json
```

## Frozen acceptance

Acceptance requires:

- exactly 1,000 attempted draws and at least 990 successful draws;
- failure fraction at most 1%;
- complete, unique terminal accounting and positive finite `Yp_BBN` and
  `D/H`;
- central and Monte Carlo median offsets no more than `0.25` public sigma;
- each reproduced standard deviation between `0.90` and `1.10` of the public
  value;
- each public standard deviation inside the deterministic 99% bootstrap
  interval from 20,000 resamples;
- relative drift at most `1e-12` for repeated draws 0, 499, and 999.

The validator regenerates all latent draws from the frozen seed, recomputes
the raw-result statistics, covariance, correlation, bootstrap intervals,
central offsets, repeat checks, terminal accounting, source/environment
provenance, and every acceptance boolean. Re-digesting a modified summary
cannot make an overclaim pass.

Passing grants one PRyMordial native-abundance-UQ baseline unit only. It does
not authorize the coherent project prior, nuisance adapter, direct UQ1
production, cross-solver discrepancy claims, or any novelty statement.
