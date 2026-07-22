# ADR-WHY-NOT-001: direct-solver necessity benchmark

Status: benchmark protocol frozen; W0-W3 standard runtime slices complete; full measurements pending

Date: 2026-07-22

Task: `P0-WHY-NOT-01`

## Decision question

Before developing a new emulator or SBI method, determine whether LINX,
PRyMordial, PRIMAT, or ABCMB+LINX can already execute the registered inference
program at acceptable cost and fidelity. “A neural network is faster” is not an
allowed justification.

This ADR freezes the measurements and stop rules before installing or timing
the competing solvers. Numeric result cells remain intentionally empty.

## Registered baselines

| ID | Frozen source | Role |
|---|---|---|
| `W0-LINX` | LINX `v0.1.2`, `ec2e9d2ca455e8204137e884da29f5dd13a638fa` | direct differentiable BBN, scalar rate nuisance, JAX/HMC baseline |
| `W1-PRYM` | PRyMordial `725d8a8db3ad5ea2630580d825c9d0d69ed76533` | explicit thermodynamics/rate-marginalization baseline |
| `W2-PRIMAT` | PRIMAT Python/C `v0.3.2`, `21ff8f39fa18e3937e9fdf386cfa982361bfdfce` | independent high-precision reference, not full production sampler by default |
| `W3-ABCMB` | ABCMB `v0.3.1`, `5eabbab4ed7e53f264e16024743d1ba517845c37`, with its bundled LINX tree | fully differentiable CMB+BBN and Fisher/HMC baseline |

PArthENoPE and AlterBBN remain solver-factor and legacy engineering baselines;
they do not replace the four mandatory answers in this ADR. SageNet predicts
SGWB spectra and does not replace a BBN abundance solver.

W3's bundled LINX is not assumed identical to W0. Its exact Git tree and the
incompatible JAX pins are recorded in
`manifests/software/why_not_baselines_v1.yaml` and must be compared explicitly.

## Common experiment contract

Every executable baseline must use the same registered parameter schema,
observation snapshot, neutron-lifetime scenario, floating-point mode, and
requested nuclear-rate perturbation. An adapter must return abundance values,
structured failure codes, runtime, peak resident memory, and source/config
hashes. Unsupported features are recorded as unsupported; they are not emulated
silently inside the competitor.

Measurements run in this order:

1. environment creation and cold-start import/compile;
2. standard-BBN central point;
3. 64-point standard-BBN batch;
4. scalar-rate `q=0,-1,+1` checks for registered reactions;
5. registered non-standard expansion point after the shared extension contract exists;
6. Jacobian/gradient stability where native differentiation is available;
7. matched direct posterior recovery;
8. end-to-end cost projection for robustness scans and 1,000 SBC replicates.

The first timing call is reported separately. Warm throughput excludes
environment setup and JIT compilation but includes data transformation and
solver failures. At least 30 warm repetitions are required per scalar timing;
the report must include median, interquartile range and p95, not only the best
run.

## Required quantitative answers

### Q1 — Why not direct LINX?

Measure FP64 cold/warm latency, 64-point throughput, scalar-rate marginalization,
Jacobian time, HMC/NUTS ESS/hour, gradient failures, and posterior recovery.
Audit whether the registered stiff/reheating extension and functional rate
modes are native, require a local extension, or are unsupported.

LINX is the default production choice if it passes fidelity and the full direct
workload gate below. Emulator development may continue only for a measured
cost, coverage, or missing-physics reason.

### Q2 — Why not direct PRyMordial?

Measure the same standard point and one matched extended point, including
explicit scalar-rate marginalization. Record cold/warm runtime, modification
surface, posterior recovery and total calls. A slower gradient path alone does
not disqualify PRyMordial if its total registered workload is feasible.

### Q3 — Why not direct PRIMAT?

PRIMAT is retained as an independent precision reference even if it is too slow
or difficult to extend for full inference. Measure standard fiducial latency,
100 posterior-region points and boundary/adversarial points. Its exclusion from
production requires a measured implementation or throughput limitation; it is
never excluded from final reference validation solely because another solver is
faster.

### Q4 — Why not ABCMB+LINX?

Measure Fisher construction, FP64 gradient stability, NUTS ESS/hour, posterior
recovery, memory and extension-development effort. The comparison must include
an identical CMB/BBN likelihood and cannot compare ABCMB+LINX joint inference
against an emulator that omits CMB cost.

## Frozen fidelity criteria

A direct or hybrid posterior passes only when, relative to the registered direct
reference:

- every core normalized median shift is below `0.1 sigma`;
- every core credible-interval ratio lies in `[0.95, 1.05]`;
- no registered posterior mode or decision-boundary topology is lost;
- numerical/adapter failure rate is below `1%` in-domain;
- 95% SBC coverage is compatible with nominal coverage under an exact binomial
  interval for 1,000 replicates;
- all out-of-domain or failed evaluations are explicit, never clipped silently.

These are acceptance criteria, not claims that the current system passes.

## Frozen cost and stop rules

The direct-workload projection includes 1,000 SBC replicates, the registered
solver/data/prior robustness matrix, and the flagship detector forecast. It is
computed from measured calls and measured concurrency, not ideal peak FLOPS.

1. **Direct-first stop rule.** If one registered direct stack passes fidelity
   and its projected workload fits on at most two current workers within 14
   calendar days and 672 worker-hours, speed is not a sufficient reason to
   develop a new emulator.
2. **Hybrid necessity rule.** A speed/cost claim requires at least a `10x`
   reduction in high-fidelity calls at matched posterior fidelity, or at least a
   `5x` measured end-to-end wall-time reduction when call counts are not
   comparable.
3. **Method stop rule.** If the hybrid method misses fidelity, coverage, or
   explicit-failure criteria, it is rejected regardless of speed.
4. **Physics-only continuation.** If direct tools are fast enough but cannot
   represent a registered functional-rate or extension contract, development
   may continue only to add that missing physics; it cannot claim generic speed
   necessity.
5. **PRIMAT retention rule.** No throughput result removes the required PRIMAT
   reference-point audit.

The 14-day/672-worker-hour ceiling is an engineering gate for the currently
authorized two-worker pool, not a universal scientific threshold. Changing it
after measurements requires a deviation entry and A00 approval.

## Measurement artifacts

The machine-readable specification is
`configs/benchmarks/why_not_existing_solvers_v1.yaml`. Each run must produce:

- `run_manifest.json` with code/config/environment hashes;
- `timings.jsonl` with cold and every warm observation;
- `failures.jsonl` with structured status;
- `posterior_metrics.json` where applicable;
- `resource_report.json` with core-hours, GPU-hours, memory and cost;
- a final `WHY_NOT_EXISTING_SOLVERS_v1.md` generated from measurements.

No result may be entered manually without a corresponding run manifest.
Every completed standard-fiducial runtime slice must also pass
`scripts/validate_why_not_runtime.py`. The validator recomputes source/config/
lock bindings, timing summaries, failure counts, successful-point counts and
cost arithmetic. Its report certifies artifact integrity only; it cannot grant
numerical, posterior or scientific acceptance.

## Current result

No baseline has yet completed the full registered measurement set. Standard-
fiducial runtime slices have completed for W2 PRIMAT, W0 LINX and W1
PRyMordial in locked worker environments. PRIMAT's 30 warm scalar and 30 sequential 64-point
workloads produced no structured failures, with a warm scalar median of
0.06387 seconds. LINX's warm scalar median was 0.21572 seconds and its native
64-point median was 0.85856 seconds, but identical-input scalar versus native-
batch abundances were not bitwise equal. A pre-registered eight-case follow-up
completed without runtime failures but did not reach either the tightened-
tolerance or weak-rate interpolation plateau. Numerical consistency is not
accepted, and an extended convergence scan is required. Raw runtime artifacts
are registered under `artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1/`; the
follow-up is under `artifacts/numerical/LINX-BATCH-TOLERANCE-v1/`.

An extended V2 scan retained the same plateau threshold. Five of its six cases,
including the proposed production candidate, reached LINX's default
`max_steps=4096`; both plateaus were therefore not evaluable. These are
structured numerical failures, not missing records. The artifacts are under
`artifacts/numerical/LINX-EXTENDED-CONVERGENCE-v2/`.

The V3 maximum-step diagnostic retained the V2 strict point and found exact
scalar and batch invariance between `max_steps=16384` and 32768; that narrow
diagnostic passed. The next tolerance/sampling convergence rerun is registered
to use 16384. V3 does not restore the rejected gradient or complete W0.

V4 completed that rerun with zero failures. Both unchanged plateau limits
passed, nominating `rtol=1e-8`, `atol=1e-11`, `sampling_nTOp=2400` and
`max_steps=16384` as the standard-point numerical candidate. This does not
accept the non-finite gradient, posterior recovery, extensions or W0 overall.

W1 completed 30 warm scalar solves and 30 sequential 64-point workloads with
1,950 successful warm points and no structured failures. Its warm scalar median
was 5.90683 seconds and its sequential 64-point median was 375.05736 seconds,
or 5.86027 seconds per point. Repeated outputs had zero recorded drift, and the
run consumed 3.17975 worker-hours at an estimated CNY 9.15767. This is only the
standard-fiducial runtime slice: explicit rate marginalization, the registered
extension point, matched posterior recovery and the full workload projection
remain pending.

W3's ABCMB-bundled LINX component also completed 30 warm scalar solves and 30
native 64-point workloads with 1,950 successful warm points and no structured
failures. Its scalar median was 0.31112 seconds and its native batch median was
0.89676 seconds, or 0.01401 seconds per point. The scalar and batch abundance
outputs were not numerically identical: the maximum difference was
`1.5777656725834976e-6`, dominated by `Y_p`. The discrepancy remains open, as
do the full CMB pipeline, Fisher matrix, gradient stability, HMC/NUTS,
posterior recovery and extension-development measurements. The runtime slice
therefore cannot answer Q4 by itself.

The preregistered eight-case W3 scalar/native-batch follow-up subsequently
completed without failures. All three candidate cases passed the frozen
`0.01` observation-sigma scalar/batch budget, but the tolerance plateau was
`0.0047691 sigma` and the weak-rate sampling plateau was `0.0274556 sigma`,
both above the frozen `0.001 sigma` threshold. W3 numerical consistency is not
accepted. An extended convergence protocol is required; the threshold may not
be relaxed after this result.

That extended protocol was frozen before measurement as
`ABCMB-LINX-EXTENDED-CONVERGENCE-v2`. It separates tolerance at
`sampling_nTOp=2400` from weak-rate sampling at `rtol=1e-8`, uses
`max_steps=16384`, and preserves the V1 `0.01 sigma` scalar/batch and
`0.001 sigma` plateau limits. The subsequent six-case run completed without
failures: the tolerance plateau was `0.000387133 sigma`, the weak-rate sampling
plateau was `0.000771123 sigma`, and both zero-drift checks passed. This accepts
only the standard-point bundled-LINX numerical candidate. It supplies no
full-ABCMB, gradient, Fisher, HMC/NUTS, posterior, extension, cross-solver or
WHY-NOT completion credit.

The registered LINX neighborhood diagnostic then completed all 45 expected
path/point records. Every record failed structurally, with no silently accepted
non-finite values, so the three-coordinate gradient candidate is rejected. The
separate ABCMB spectra-first audit accepted all five frozen spectra cases with
zero repeat drift, completing only one of four components; gradient,
toy-Fisher, synthetic recovery and HMC/NUTS were not run. Exact evidence and
scope boundaries are in `docs/inventory/LINX_GRADIENT_STABILITY_v1.md` and
`docs/inventory/ABCMB_FULL_COMPONENT_AUDIT_v1.md`.

Posterior-region, adversarial, extension and matched-posterior measurements
remain pending. LINX's previously observed non-finite gradient also remains
rejected. The answer to all four “why not” questions is therefore still
**undetermined**. This ADR closes protocol discretion, not `P0-WHY-NOT-01`.

ADR-0006 pauses further generic ABCMB/LINX auditing while retaining this
evidence. `P0-WHY-NOT-01` remains active only for the direct-solver necessity
and emulator-economics memo tied to the nuclear-rate UQ workload.

Before any registered W1 timing, the PRyMordial adapter contract was frozen in
`configs/benchmarks/prymordial_runtime_adapter_v1.yaml`. It selects the Python
small 12-reaction network, PRIMAT-like rate tables, recomputation of background
and bulk weak rates, no recomputation of stored thermal weak corrections, and
sequential calls because the upstream path has no native batch API. Its input
and abundance-unit mappings are explicit. The standard-fiducial runtime slice
is now registered; this does not authorize or imply the remaining W1 labels.

The W3 pre-execution component contract is frozen separately in
`configs/benchmarks/abcmb_linx_runtime_adapter_v1.yaml`. It binds the installed
ABCMB VCS provenance, the repository's bundled LINX tree, FP64 CPU execution,
the `key_PRIMAT_2023` network, upstream background/abundance numerics, and
native `jax.jit(jax.vmap)` batching. This first slice measures only ABCMB's
bundled BBN component and must be compared with W0. It does not answer the full
ABCMB+LINX question: CMB spectra, Fisher/gradient stability, HMC/NUTS,
posterior recovery, and extension effort remain pending.

## Sign-off

- benchmark protocol prepared by Codex, 2026-07-22;
- A00 scientific lead: pending;
- A03 statistics validation: pending;
- A07 compute validation: pending.
