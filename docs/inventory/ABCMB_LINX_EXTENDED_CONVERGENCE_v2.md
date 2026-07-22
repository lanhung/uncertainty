# ABCMB bundled-LINX extended convergence protocol v2

Status: **frozen before measurement; evidence pending**  
Task: `P0-WHY-NOT-01`  
Protocol: `configs/benchmarks/abcmb_linx_extended_convergence_v2.yaml`

## Why this run exists

The V1 consistency run completed all eight cases, but its tolerance and
weak-rate sampling plateaus failed the preregistered `0.001` observation-sigma
limit. Runtime completion is not numerical acceptance. V2 therefore extends
both axes without relaxing either the `0.01` scalar/native-batch budget or the
`0.001` plateau budget.

## Frozen design

The tolerance axis fixes `sampling_nTOp=2400` and compares `rtol` values
`1e-7`, `3e-8`, and `1e-8`. The sampling axis fixes `rtol=1e-8` and compares
`sampling_nTOp` values 300, 600, 1200, and 2400. Every abundance solve uses
`max_steps=16384`, the conservative value independently accepted by the W0
LINX max-steps diagnostic. The ABCMB background settings, source revision,
bundled LINX tree, network, batch size, repetitions, standard point, and
observation normalization remain frozen.

The production candidate is:

```text
rtol=1e-8
atol=1e-11
sampling_nTOp=2400
max_steps=16384
```

## Decision boundary

All required cases must succeed, every candidate scalar/native-batch
difference must remain at or below `0.01` observation sigma, both plateau pairs
must remain at or below `0.001` observation sigma, and repeated/within-batch
drift must be exactly zero. Thresholds cannot be increased after the run.

Even a full pass would accept only the bundled-LINX component at one frozen
standard-BBN point. It would not accept the full ABCMB pipeline, gradients,
Fisher matrices, HMC/NUTS, posterior recovery, non-standard cosmology, or
cross-solver fidelity.
