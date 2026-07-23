# WHY-NOT existing solvers — final memo skeleton v1

Status: **fail-closed skeleton; fast-path workload now defined; final UQ economics undetermined**

Task: `P0-WHY-NOT-01` (`0/1`)

This file is the required final-memo container for the direct-first decision.
It records what is already measured and leaves every decision cell that needs
the reference-prior posterior grid, tail refinement, posterior recovery or SBC
explicitly open. Its existence does not complete the task.

Post-measurement status:
`configs/benchmarks/why_not_evidence_status_v1.yaml`. It is deliberately
separate from the hash-frozen measurement protocol.

The fail-closed source/revision audit for the two external native-UQ paper
reproductions is
`artifacts/benchmarks/NATIVE-UQ-EXTERNAL-BLOCKERS-v1/audit.json`.

The self-contained workload used to resolve the remaining decision is defined
by:

- `docs/decisions/ADR-0008-self-contained-fast-track.md`;
- `configs/physics/nuclear_prior_R0_reference_v1.yaml`;
- `docs/ops/FAST_TRACK_MILESTONES_v1.md`;
- `plan/plan.yaml` version 6.

## Evidence matrix

| Question | Current evidence | Status |
|---|---|---|
| Can the public solvers run reproducibly at one standard point? | Four integrity-validated W0–W3 runtime slices, each with 1,950 successful warm points and zero structured failures | measured, scope limited |
| Can native nuclear-rate UQ be reproduced? | PRIMAT and PRyMordial accepted at 1,000/1,000 draws; LINX v2 accepted under unchanged numerical gates | three mandatory core baselines accepted |
| Is the frozen LINX native candidate numerically accepted? | v1 failed at `0.001246448`; stricter pre-registered v2 passed at `0.000619368` versus unchanged `0.001` limit | yes, v2 C0 calibration only |
| Is the sensitivity-atlas R0 slice accepted? | Frozen central/sign checks failed; the pre-paper and registered public PRyMordial revisions are identical on the registered PRIMAT path | no; non-blocking external audit |
| Can the published GP abundance distribution be rerun? | Method structure captured; code, fitted hyperparameters, exact data, draws and seed are unavailable | externally blocked; non-blocking audit |
| Is a self-contained R0 reference-prior family defined? | ETR25 scalar, asymmetric-quantile, legacy-envelope and correlation-stress representations are frozen by ADR-0008 | yes for conditional exploratory direct calculations |
| Is the publication-grade experimental nuclear posterior reconstructed? | Pointwise ETR25 percentiles are public; coherent original draws and cross-reaction covariance are unavailable | no |
| Is the direct project workload measured? | The 9-point, GH81, five-point drift and one-dimensional posterior workload is frozen but not yet executed | pending |
| Are `U-M1` versus `U-M2` posterior consequences measured? | Direct one-dimensional posterior grid is defined | pending |
| Are prior/posterior SBC and OOD fallback measured? | Not required for the first direct fast gate; required before a learned-model claim | pending/conditional |
| Is the 672 worker-hour direct-first rule evaluable? | It becomes evaluable after the fast posterior grid and conditional refinement cost are measured | pending but no longer externally blocked |

## Solver dispositions

- `W0-LINX`: fiducial runtime measured; native scalar-envelope v1 failed its
  tolerance plateau, while the stricter pre-registered v2 passed without
  relaxing the gate. It is the primary batched solver for the reference-prior
  fast path. Gradient and HMC claims remain unavailable.
- `W1-PRyMordial`: fiducial runtime and one 1,000-draw native
  log-normal-marginalization calibration are accepted. It is the independent
  selected-node and distribution spot check; its native prior is not silently
  treated as the project prior.
- `W2-PRIMAT`: fiducial runtime and one 1,000-draw native MC calibration are
  accepted. It remains the precision/native reference. Project-owned ETR25
  curve injection is deferred until reverse-cap and injection regressions pass.
- `W3-ABCMB`: only the bundled-LINX BBN runtime slice and spectra-only audit
  component exist. Full CMB+BBN likelihood, Fisher, recovery, and HMC/NUTS are
  outside the active Stage-R0 fast path.

## Fast-path decision cells

```text
reference-prior direct distribution: defined, not yet run
five-point covariance drift: defined, not yet run
U-M0/U-M1/U-M2 posterior grid: defined, not yet run
direct solver sufficient: undetermined
emulator necessary for speed: undetermined
emulator necessary for distribution fidelity: undetermined
full UQ workload within 14 days / 672 worker-hours: now measurable after FT-M4
P0-WHY-NOT-01 progress: 0/1
```

The final decision may be filled only after the registered fast posterior grid
and any triggered refinement are measured. Standard-point linear extrapolation
alone cannot substitute for those measurements.

## Final sign-off block

- A02 numerical methods: pending direct fast-path workload
- A07 statistical inference: pending posterior-grid evidence
- A09 independent validation: pending publication-grade claims
- A00 scientific lead: pending publication-grade claims

Track B remains **NOT FROZEN**. Nature-tier Gate remains **CLOSED**. The
exploratory fast path may proceed without impersonating the missing human
signatures.
