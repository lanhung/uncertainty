# ADR-0008: reproduce native UQ before freezing the project prior

Status: **accepted**

Date: 2026-07-23

Supersedes: the dependency direction between `UQ0-NATIVE-UQ-REPRO` and
`UQ0-R0-RATE-PRIOR` in plan version 4.

## Context

The July 2026 frontier audit makes native PRIMAT Monte Carlo, PRyMordial rate
marginalization and LINX `nuclear_rates_q` mandatory calibration baselines.
Those upstream paths carry their own native rate representations. Reproducing
them is needed to understand draw semantics, units, reverse-rate behavior,
failure modes and abundance-level reference outputs before a project-owned
coherent ETR25 prior and production adapter are frozen.

Plan version 4 accidentally made `UQ0-NATIVE-UQ-REPRO` depend on
`UQ0-R0-RATE-PRIOR`. That inverted the v0.4.1 critical path and prevented
public native baselines from running while the actual/original ETR25 posterior
and scientific sign-offs were unavailable.

## Decision

Plan version 5 uses:

```text
UQ0-PUBLIC-SOLVER-BASELINES + UQ0-RATE-PDF-AUDIT
    -> UQ0-NATIVE-UQ-REPRO
    -> UQ0-R0-RATE-PRIOR
    -> UQ0-NUISANCE-ADAPTER
```

Native-UQ reproduction must use the frozen upstream source and its native
uncertainty interface. It may not inject the candidate ETR25 surrogate, select
a project scientific prior, or unlock production.

`UQ0-R0-RATE-PRIOR` remains the gate that accepts coherent rate curves,
cross-reaction covariance policy, solver mappings and the production draw
contract. Existing rate-level mapping/reverse regressions are retained as C0
evidence but do not count as abundance-level native-UQ reproduction.

## Acceptance boundary

Each native baseline receives progress only when its registered
abundance-level reproduction artifact:

- pins source, environment, network, rate representation and seed;
- records central and perturbed/drawn abundance outputs;
- reports failures, runtime and numerical reproducibility;
- validates against the upstream API or published reference object;
- states explicitly that it is a calibration reproduction, not a novelty or
  project-prior acceptance claim.

The atlas slice and GP-prior-structure baselines remain separate units. No
task is marked complete from source inspection or rate-only mapping evidence.

## Consequences

- PRIMAT, PRyMordial and LINX native-UQ work can proceed without private legacy
  assets or A03/A00/A09 sign-off.
- The missing actual/original ETR25 posterior still blocks the project-owned
  coherent scientific prior and every downstream production run.
- The Nature-tier gate remains closed.
