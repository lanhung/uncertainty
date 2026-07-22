# Independent pre-asset audit protocols v1

Status: heartbeat complete; LINX negative result and ABCMB spectra retained;
generic challenge and remaining components paused by ADR-0006

These protocols cover work that does not require the missing modified solvers,
legacy BBNet checkpoint/scaler/data/MCMC assets, or independent scientific
signatures.

## Registered workstreams

1. `ABCMB-FULL-COMPONENT-AUDIT-v1` covers exact-source spectra integrity,
   selected full-model gradients, a toy Fisher interface and one-dimensional
   Asimov recovery. Formal Fisher, real posterior and HMC/NUTS claims remain
   unavailable because the exact environment has no registered likelihood,
   covariance or sampler.
2. `LINX-GRADIENT-STABILITY-v1` tests the accepted W0 numerical candidate at
   the standard point and a frozen small neighborhood using AD-mode and
   five-point finite-difference comparisons. The historical NaN at the extreme
   `2*ones(15)` challenge is retained as a diagnostic-only ablation.
3. `WHY-NOT-STANDARD-CHALLENGE-GRID-v1` runs seven frozen standard-BBN points
   across W0-W3. Cross-baseline differences remain descriptive pipeline
   discrepancies because rate libraries, weak physics and networks are not
   matched.
4. `OFFLINE-HEARTBEAT-E2E-v1` validates durable buffering, checkpointing,
   controlled replay and prompt lease release without touching science-gate
   state.

Every workstream has a separate `EXEC` task. Reaching 100% execution does not
complete `P0-WHY-NOT-01` or any blocked solver/rate/Fisher task.

## Post-measurement disposition

- the offline heartbeat regression passed 8/8 and was replayed to the ledger;
- the LINX neighborhood gradient candidate completed 4/4 execution groups but
  failed all 45 frozen acceptance records without silent non-finite values;
- all five ABCMB spectra cases passed, completing only the spectra component
  (1/4); gradient, toy-Fisher and synthetic recovery were not run;
- ADR-0006 then removed the generic LINX/ABCMB follow-up and W0-W3 challenge
  grid from active desired state. Their task records are cancelled, not
  scientifically completed, and their artifacts remain available for a future
  signed reactivation.

## Resource policy

The three scientific/numerical workloads share the westb `cpu-heavy` lease and
therefore execute serially unless a single registered harness safely controls
internal parallelism. The lightweight heartbeat regression uses the separate
`ops-e2e` lease and may run concurrently. Exact locks are CPU-only; the visible
GPU is not treated as usable by silently changing JAX builds.
