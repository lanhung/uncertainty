# WHY-NOT existing solvers — final memo skeleton v1

Status: **fail-closed skeleton; final UQ economics undetermined**

Task: `P0-WHY-NOT-01` (`0/1`)

This file is the required final-memo container for the direct-first decision.
It records what is already measured and leaves every decision cell that needs
the accepted R0 production workload, posterior recovery, or SBC explicitly
open. Its existence does not complete the task.

Post-measurement status:
`configs/benchmarks/why_not_evidence_status_v1.yaml`. It is deliberately
separate from the hash-frozen measurement protocol.

The fail-closed source/revision audit for the two remaining native-UQ
baselines is
`artifacts/benchmarks/NATIVE-UQ-EXTERNAL-BLOCKERS-v1/audit.json`.

## Evidence matrix

| Question | Current evidence | Status |
|---|---|---|
| Can the public solvers run reproducibly at one standard point? | Four integrity-validated W0–W3 runtime slices, each with 1,950 successful warm points and zero structured failures | measured, scope limited |
| Can native nuclear-rate UQ be reproduced? | PRIMAT and PRyMordial accepted at 1,000/1,000 draws; LINX v2 accepted under unchanged numerical gates | 3/5 accepted |
| Is the frozen LINX native candidate numerically accepted? | v1 failed at `0.001246448`; stricter pre-registered v2 passed at `0.000619368` versus unchanged `0.001` limit | yes, v2 C0 calibration only |
| Is the sensitivity-atlas R0 slice accepted? | Frozen central/sign checks failed; the pre-paper and registered public PRyMordial revisions are identical on the registered PRIMAT path | no |
| Can the published GP abundance distribution be rerun? | Method structure captured; code, fitted hyperparameters, exact data, draws and seed are unavailable | blocked |
| Is the project R0 prior frozen for production? | Engineering candidate and provenance exist; scientific prior and signatures do not | no |
| Is the direct 1,000-draw project workload measured? | No accepted production-prior run | pending |
| Are posterior recovery and `U-M1` versus `U-M2` measured? | No registered posterior reference | pending |
| Are prior/posterior SBC and OOD fallback measured? | No registered workload | pending |
| Is the 672 worker-hour direct-first rule evaluable? | Fiducial linear arithmetic exists, but not a UQ cost projection | no |

## Solver dispositions

- `W0-LINX`: fiducial runtime measured; native scalar-envelope v1 failed its
  tolerance plateau, while the stricter pre-registered v2 passed without
  relaxing the gate. Gradient and posterior claims remain unavailable.
- `W1-PRyMordial`: fiducial runtime and one 1,000-draw native
  log-normal-marginalization calibration are accepted. Posterior recovery and
  the project-selected prior remain unmeasured.
- `W2-PRIMAT`: fiducial runtime and one 1,000-draw native MC calibration are
  accepted. It remains the precision reference regardless of throughput.
- `W3-ABCMB`: only the bundled-LINX BBN runtime slice and spectra-only audit
  component exist. Full CMB+BBN likelihood, Fisher, recovery, and HMC/NUTS are
  not measured and are outside the active UQ-only path.

## Frozen decision cells

```text
direct solver sufficient: undetermined
emulator necessary for speed: undetermined
emulator necessary for distribution fidelity: undetermined
full UQ workload within 14 days / 672 worker-hours: not yet evaluable
P0-WHY-NOT-01 progress: 0/1
```

The decision may be filled only after the accepted R0 prior drives the direct
fiducial MC and the registered posterior/SBC cost model. Standard-point linear
extrapolation cannot substitute for those measurements.

## Final sign-off block

- A02 numerical methods: pending final workload
- A07 statistical inference: pending posterior/SBC evidence
- A09 independent validation: pending
- A00 scientific lead: pending

Track B remains **NOT FROZEN**. Nature-tier Gate remains **CLOSED**.
