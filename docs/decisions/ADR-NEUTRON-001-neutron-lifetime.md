# ADR-NEUTRON-001: neutron-lifetime scenarios

Status: accepted for preregistration; scientific sign-off pending
Date: 2026-07-21
Task: `P0-NEUTRON-01`

## Problem

The beam/bottle discrepancy is large enough that a single convenient Gaussian
can hide a material model choice in `Y_p` and extended-cosmology inference.

## Options considered

1. Use only the newest individual measurement.
2. Use one global average and ignore method discrepancy.
3. Register a reviewed UCN baseline, method-specific alternatives, and an
   explicit mixture stress model.

## Decision

Adopt option 3 with `N0`–`N3` exactly as specified in
`configs/physics/neutron_lifetime_v1.yaml`. Register the J-PARC electron-beam
measurement as an additional, systematics-distinct stress test.

## Rationale

This preserves a stable primary baseline while making the beam/bottle choice
visible in every flagship endpoint. It also prevents selecting the lifetime
model after seeing the final result.

## Objections

An equal-weight `N3` mixture is not derived from a full experiment-level
hierarchical analysis. It is therefore used only for robustness and is not
interpreted as a model probability. A later pre-unblinding hierarchical model
may supersede it through a new ADR.

## Consequences

All flagship inference must report `N0`–`N3`; solver adapters must expose and
audit lifetime handling; weak-rate uncertainties cannot double count `tau_n`.

## Review triggers

- a new peer-reviewed beam or bottle measurement;
- a revised PDG aggregate;
- an experiment-level covariance enabling a defensible hierarchical model;
- evidence that a solver maps `tau_n` inconsistently with the registered prior.

## Signatories

- A04 observations/preregistration: Codex, prepared 2026-07-21;
- A00 scientific lead: pending;
- independent weak-physics reviewer: pending.
