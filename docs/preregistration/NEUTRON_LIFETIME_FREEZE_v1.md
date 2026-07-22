# NEUTRON-v1 lifetime freeze

Status: **decision frozen; Track B gate closed pending sign-off**
Decision date: 2026-07-21 UTC
Task: `P0-NEUTRON-01` / scientific blocker `NUC-01`

## Frozen scenarios

| ID | Role | Distribution |
|---|---|---|
| `N0` | main baseline | PDG 2026 UCN average, Normal(`878.3`, `0.4`) s |
| `N1` | bottle-only robustness | latest UCNtau split normal around `877.82` s |
| `N2` | proton-beam robustness | Yue 2013 Normal(`887.7`, `2.2472`) s |
| `N3` | method-discrepancy robustness | equal-weight finite mixture of `N1` and `N2` |

The exact directional widths and source IDs are frozen in
`configs/physics/neutron_lifetime_v1.yaml`. Published statistical and systematic
components are combined in quadrature; asymmetric systematic components remain
asymmetric.

`N0` is selected because the 2026 PDG UCN average provides a reviewed aggregate
with its scale-factor inflation retained. The choice was made before Track B
production inference and cannot be swapped in response to a more favorable
`Y_p`, new-physics significance, or detector-overlap result.

## J-PARC and beam/bottle tension

The J-PARC electron-detection beam result is registered as a separate stress
test: `877.2 ± 1.7 (stat) +4.0/-3.6 (sys) s`. It is not merged into `N2`, whose
proton-counting systematics are distinct. `N3` is a sensitivity model for an
unresolved method discrepancy, not a posterior claim about which technique is
correct.

## No double counting

Neutron lifetime, weak-rate radiative/thermal corrections, neutrino decoupling,
and weak normalization are separate model factors. A solver adapter must document
how `tau_n` enters before it can use these priors. The same lifetime uncertainty
must not re-enter through an additional weak-rate scale nuisance.

## Version integrity and sign-off

The PDG listing and all three experiment documents have immutable URLs and
SHA256 checksums in `manifests/data/OBS-v1-sources.yaml`.

Prepared by: Codex acting in the A04 observations/preregistration role.
A00 scientific lead sign-off: **pending**.
Independent weak-physics review: **pending**.
Track B status: **NOT FROZEN**.
