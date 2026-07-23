# Stage-R0 legacy solver-envelope mapping v1

Status: **legacy solver-envelope mapping frozen; ETR25 actual-PDF audit and
scientific sign-off pending; production use prohibited**

Date: 2026-07-23 UTC

Tasks: `UQ0-NATIVE-UQ-REPRO`, `UQ0-R0-RATE-PRIOR`

## Outcome

The three R0 deuterium reactions now have a deterministic LINX legacy-envelope
source package and exact canonical scalar coordinates for reproducing the
uncertainty interfaces distributed by LINX, PRyMordial and PRIMAT:

```text
r_i(T9_j, z_i) = rbar_i(T9_j) exp[z_i sigma_i(T9_j)]
```

The legacy calibration package contains the 150-knot central curves and
factor-uncertainty envelopes distributed in LINX `key_recommended` at exact
revision `ec2e9d2ca455e8204137e884da29f5dd13a638fa`. Its SHA256 is
`aacca2ad92c2132a67995801d091d9b642f3616cf7cf70b2a54a6e1d4348c745`.
The package is reproducible from the pinned public checkout with
`scripts/build_nuclear_stage0_R0_package.py`.

This closes a native-interface mapping artifact only. ADR-0007 makes ETR25 or
an approved original nuclear posterior the registered scientific-prior
candidate. `UQ0-ETR25-R0-INGEST` and `UQ0-RATE-PDF-AUDIT` therefore remain
upstream dependencies, `UQ0-R0-RATE-PRIOR` remains pending, and the common
production adapter is not unlocked. The central, `z=+1`, and `z=-1` abundance
regressions also remain a separate downstream gate. A03, A00, and A09 sign-offs
remain pending.

## Canonical coordinates

| Canonical reaction | Canonical parameter | LINX `key_recommended` mapping |
|---|---|---|
| `d(p,gamma)3He` | `z_dp_gamma_he3` | `nuclear_rates_q[1]`, `dpHe3g` |
| `d(d,n)3He` | `z_dd_n_he3` | `nuclear_rates_q[2]`, `ddHe3n` |
| `d(d,p)t` | `z_dd_p_t` | `nuclear_rates_q[3]`, `ddtp` |

One scalar is shared across the entire temperature curve of each reaction.
Forward and reverse rates use the same scalar. A reverse rate must never
receive a second draw.

The package uses the identity matrix only as an engineering covariance. No
physical cross-reaction covariance is distributed with these scalar tables;
missing covariance is not evidence that the reactions are independent. A
nonzero-correlation stress test and nuclear-data review are mandatory before
scientific production.

## Exact solver mappings and factorial boundary

All three public paths accept the same externally generated canonical `z`
coordinate:

| Path | Exact transform | Native rate-library relation |
|---|---|---|
| LINX S6 | assign the three `nuclear_rates_q` entries | exact LINX legacy calibration package |
| PRyMordial S4 | assign `p_dpHe3g`, `p_ddHe3n`, `p_ddtp` | native PRIMAT-like or NACREII-like alternative |
| PRIMAT S8 | assign `p_d_p__He3_g`, `p_d_d__He3_n`, `p_d_d__t_p`; all additive deltas zero | native PRIMAT or PArthENoPE-like alternative |

PRyMordial and PRIMAT implement the same scalar transform
`median * exp(z * log(exp_sigma))`, but their native tables are not
byte-identical to the LINX legacy package. Therefore the current paths are
registered as pipeline comparisons with native rate compilations, not
matched-physics engine comparisons. Engine-discrepancy claims remain
prohibited until identical forward tables, weak physics, and numerical
settings are injected and validated.

Native solver Monte Carlo is disabled on every path. The project draw manifest
must generate `z` and `tau_n`; all non-R0 nuclear parameters remain zero. This
prevents PRIMAT's full-network and neutron-lifetime sampling, or demo-level
PRyMordial sampling, from silently adding a second uncertainty source.

## PRIMAT effective-central caveat

PRIMAT defaults to nuclear QED corrections. For the radiative
`d(p,gamma)3He` reaction, the solver multiplies the raw table median by a
temperature-dependent QED factor before applying `z`. The adapter must freeze
that default and treat the post-QED internal curve as the effective central
curve. It must not report the raw table's second column as the default
effective PRIMAT central curve. The two `d+d` reactions are unaffected by this
particular transform.

## What is established

- exact public repository revisions, table bytes, grids, parsers and scalar
  transforms;
- a deterministic LINX-derived legacy-envelope package for three reactions;
- exact canonical-to-native parameter mappings for LINX, PRyMordial and
  PRIMAT;
- common forward/reverse nuisance handling;
- explicit interpolation and project-level out-of-grid rejection;
- explicit prohibition of native Monte Carlo and production use.

## What is not established

- A03 nuclear-data approval, A00 scientific approval or A09 independent
  validation;
- ETR25 source capture, actual-percentile products or posterior-derived
  coherent curve draws;
- the required actual-PDF versus log-normal adequacy audit;
- physical independence or a complete cross-reaction covariance;
- full posterior draws or function-valued rate modes;
- matched nuclear inputs across the three solver paths;
- central/plus/minus abundance regression;
- redistribution clearance for derived table arrays;
- a production `NUC-v1` prior.

The initial provenance-only audit remains historically correct: it selected no
scientific source and awarded no numerical-prior credit. This document is a
subsequent solver-interface calibration decision, not a scientific prior
selection or a retroactive alteration of that audit.

## Reproduction and validation

Build the package from a clean exact LINX checkout:

```bash
python scripts/build_nuclear_stage0_R0_package.py \
  --linx-source-root /path/to/linx-at-ec2e9d2 \
  --output \
  artifacts/priors/NUCLEAR-STAGE0-R0-LINX-KEY-RECOMMENDED-v1/package.json
```

Validate the repository contract:

```bash
python scripts/validate_nuclear_prior_R0_engineering_v1.py \
  --prior configs/physics/nuclear_prior_R0_engineering_v1.yaml \
  --stage configs/physics/nuclear_stage0_R0_v1.yaml \
  --repository-root .
```

Expected summary:

```text
{"canonical_parameters": 3, "mapped_solver_paths": 3, "pending_signoffs": 3, "production_enabled_reactions": 0, "registered_reactions": 3}
```
