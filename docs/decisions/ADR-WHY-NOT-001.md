# ADR-WHY-NOT-001: direct-solver necessity benchmark

Status: benchmark protocol frozen; measurements pending

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

## Current result

No baseline has yet been measured in the locked worker environment. The current
answer to all four “why not” questions is therefore **undetermined**. This ADR
closes protocol discretion, not `P0-WHY-NOT-01`.

## Sign-off

- benchmark protocol prepared by Codex, 2026-07-22;
- A00 scientific lead: pending;
- A03 statistics validation: pending;
- A07 compute validation: pending.
