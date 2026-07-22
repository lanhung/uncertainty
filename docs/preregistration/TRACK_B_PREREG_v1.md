# Track B preregistration index v1

Status: **DRAFT — NOT FROZEN; PRODUCTION AND UNBLINDING PROHIBITED**

Captured: 2026-07-22 UTC

Registry: `configs/preregistration/track_b_prereg_v1.yaml`

## Purpose

This index composes the existing observation, neutron, nuclear-rate, parameter,
endpoint, solver-factorial, Fisher, direct-solver and novelty contracts into one
machine-readable Track B gate. It does not upgrade a prepared protocol into
scientific evidence and does not sign any decision.

The standard-BBN subset, observation choice, neutron scenarios, numerical null
boundaries and direct-first cost rules are registered. The nuclear numerical
prior, extension semantics, several endpoint thresholds, matched solver matrix,
Fisher evidence and final direct-solver economics are not complete.

## Authorization state

| Action | Authorized? | Reason |
|---|---:|---|
| solver regression and direct runtime measurement | yes | allowed pre-unblinding diagnostics |
| synthetic recovery and label-hidden diagnostics | yes | allowed pre-unblinding diagnostics |
| Fisher/Laplace prescreen | yes | required before simulation expansion |
| Pilot-1k | no | Fisher and upstream contracts incomplete |
| Pilot-10k | no | Fisher gate report and sign-offs absent |
| Track B production inference | no | Track B is not frozen |
| flagship physical-effect selection | no | would constitute premature unblinding |
| Nature-tier claim | no | claim-evidence and independent validation gates are closed |

## Frozen boundaries already available

- normalized median-shift null boundary: `0.1 sigma`;
- credible-interval ratio null band: `[0.95, 1.05]`;
- topology null: unchanged;
- maximum in-domain failure fraction: `1%`;
- hybrid threshold: `10x` fewer high-fidelity calls or `5x` end-to-end wall time;
- direct-first ceiling: two workers, 14 days, 672 worker-hours.

These thresholds cannot be weakened after observing Track B results without a
registered deviation. Detector-volume, reaction-ranking and nuclear
value-of-information thresholds remain pending and cannot be invented from the
observed effect.

## Open freeze artifacts

The competitor matrix, novelty draft, observation decision, endpoint draft,
solver-factorial ADR and Fisher ADR exist, but their respective reviews or
measurements remain open. `NUC-v1` is explicitly non-production. The required
`artifacts/gates/FISHER_GATE_REPORT_v1.md` does not yet exist.

Until all entries in `required_freeze_artifacts` are complete and signed, the
machine-readable flags remain:

```text
production_authorized: false
unblinding_authorized: false
pilot_1k_authorized: false
pilot_10k_authorized: false
```

## Change and stopping policy

Before unblinding, the project may inspect regression, synthetic recovery,
Fisher prescreen, label-hidden diagnostics and direct-solver numerical/runtime
evidence. It may not choose a primary dataset, prior, endpoint, reaction set or
flagship effect based on a favorable result.

After unblinding, every change enters `DEVIATION_LOG.md` and is labeled
confirmatory or exploratory. A null or failed gate is retained as a valid
stopping result; it does not authorize expanding search freedom.

## Sign-off

Prepared by Codex as a gate index only.

- A00 scientific lead: **pending**;
- A03 nuclear data: **pending**;
- A04 observations and preregistration: **pending**;
- A09 independent validation: **pending**;
- A11 literature and competition: **pending**.

Operational authorization does not substitute for these scientific sign-offs.
