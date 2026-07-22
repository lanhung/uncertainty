# NUC-v1 nuclear-rate prior freeze contract

Status: **DRAFT — NOT FROZEN; PRODUCTION USE PROHIBITED**

Contract date: 2026-07-22 UTC

Task: `NUC-01` / `P2-rate-registry` / `P2-functional-rate-basis`

## Scope

`configs/physics/nuclear_prior_NUC-v1.yaml` now defines the fields and gates that
an approved nuclear-rate prior must satisfy. It is a schema and review contract,
not a numerical prior. It must not be used for Track B training labels, Fisher
inputs, production inference, or scientific claims.

The first three functional-rate candidates are registered by stable IDs:

- `dp_gamma_he3`: `d(p,gamma)3He`;
- `dd_n_he3`: `d(d,n)3He`;
- `dd_p_t`: `d(d,p)t`.

Their source versions, central curves, scalar envelopes, covariance structures,
functional bases, detailed-balance mappings, and checksums remain deliberately
`pending`. No numerical value has been inferred from a placeholder.

## Mandatory provenance for every reaction

Before a reaction is enabled, its entry must contain:

1. a unique reaction ID, physical equation, and solver aliases;
2. immutable nuclear-data and rate-compilation versions;
3. central rate, units, temperature grid, and scalar `sigma_i(T)`;
4. functional energy grid, posterior mean, basis vectors, eigenvalues, cumulative
   variance, and thermal-integration method when functional modes are used;
5. shared normalization and cross-reaction correlation treatment;
6. forward/reverse detailed-balance mapping;
7. solver-specific rate-ID mappings;
8. licenses and source checksums;
9. membership in the core, extended, and full stress sets.

The target core registry has 12 reactions. Only three candidate contracts are
present, so the other reaction selections and all numerical priors remain open.

## Correlations are not independence

`NUC-v1` explicitly sets `independence_assumed: false`. If an authoritative
source does not publish a correlation matrix, the missing correlation must be
recorded as unmodeled and a preregistered sensitivity stress test must be run.
It is prohibited to convert missing covariance information into an independence
assumption silently.

## Scalar and functional models

The scalar contract follows the registered baseline interface
`log r_i(T) = log rbar_i(T) + q_i sigma_i(T)`, with `q_i` standard normal. This
does not freeze `rbar_i(T)` or `sigma_i(T)`.

For the three head deuterium reactions, the functional contract requires a
posterior-derived and cross-validated basis. The number of modes must be selected
using cross-validation and cumulative posterior variance; an arbitrary mode
count is not allowed. Scalar and functional representations must originate from
the same nuclear data so normalization uncertainty is not counted twice.

## Neutron lifetime boundary

Neutron lifetime is modeled separately in
`configs/physics/neutron_lifetime_v1.yaml`. It is not an ordinary thermonuclear
rate, and its uncertainty must not be reintroduced through a weak-rate scale
nuisance. The existing neutron decision still has its own pending scientific and
weak-physics review.

## Freeze blockers

- authoritative nuclear-data versions and immutable checksums;
- the remaining core reaction selection;
- central curves, grids, units, scalar envelopes, and covariance structures;
- functional posterior construction and mode-selection validation;
- shared experimental-systematic and cross-reaction correlation review;
- detailed-balance and solver mapping validation;
- A03 nuclear-data review;
- A00 scientific-lead sign-off;
- A09 independent validation.

Until every blocker is closed and the machine-readable status changes through a
reviewed commit, Track B remains **NOT FROZEN** and production use remains
prohibited.

## Sign-off

Contract prepared by Codex as an auditable schema only; this is not a scientific
approval.

- A03 nuclear-data review: **pending**;
- A00 scientific lead: **pending**;
- A09 independent validation: **pending**.
