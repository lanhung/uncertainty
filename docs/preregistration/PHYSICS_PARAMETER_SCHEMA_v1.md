# Physics parameter schema v1

Status: standard-BBN benchmark subset frozen; extension semantics pending

Date: 2026-07-22

## Decision

`configs/physics/parameter_schema.yaml` is the canonical parameter-name and
adapter-alias registry. The standard-BBN direct-solver point is now fixed to
values inherited from already frozen project inputs:

| Coordinate | Value | Source |
|---|---:|---|
| `omega_b_h2` | 0.02237 | `CMB-v1` main-stage mean |
| `delta_neff` | 0 | standard-model null |
| `tau_n_seconds` | 878.3 s | `NEUTRON-v1` N0 mean |
| `kappa10` | 0 | standard-model null only |

This selection was made without using solver abundance or timing output. It
resolves the parameter-file prerequisite for standard-BBN WHY-NOT measurements
without freezing any extension prior.

## Unresolved extension contract

The supplied public BBNet source names `kappa10` and documents a legacy
training range, but does not define its physical normalization or the mapping
to the AlterBBN training columns `dd0` and `dd0_rad`. The same asset set does
not supply the authoritative `n_t`, `T_re`, tensor-amplitude, reheating or stiff
transition contract used by the old likelihood. These fields remain explicitly
unfrozen and cannot enter production or be interpreted through guessed aliases.

The schema distinguishes a training-domain statement from an inference prior.
Legacy ranges are recorded as provenance only; they are not promoted to Track B
priors.

## Gate consequence

Standard-BBN direct benchmarking may proceed. Non-standard benchmark points,
BBNet reproduction, Track A posterior work and extension Jacobians remain
blocked until the missing modified-solver and old-MCMC contracts are supplied
or independently reconstructed and scientifically approved.
