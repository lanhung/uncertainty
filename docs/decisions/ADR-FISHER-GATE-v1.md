# ADR-FISHER-GATE-v1: linear propagation gate before production data

Status: gate protocol prepared; point manifest and sign-off pending

Date: 2026-07-22

Task: `FISH-01` / `P2.5-jacobians` / `P2.5-gate-report`

## Decision

No Pilot-10k, large surrogate training campaign or additional long-lived cloud
capacity is authorized before a Fisher/linear-propagation screen. The screen
must determine whether scalar rates, functional rate shape, solver discrepancy
or observational covariance can plausibly change the registered physical
endpoints.

Pilot-1k may be used only for interface validation after the dependencies in
the project plan are satisfied. It is not permission to tune a discovery claim.

## Required response objects

At every accepted point `theta_j`, record in float64:

```text
J_theta(theta_j)
J_q(theta_j)
J_a(theta_j)
C_rate(theta_j)
C_shape(theta_j)
C_solver(theta_j)
```

The manifest records parameter units/transforms, abundance convention,
finite-difference step or autodiff path, solver/factor tuple, source/build
revisions, failed derivatives, truncation rank and condition diagnostics.

Autodiff is not accepted merely because the process exits zero. Non-finite
components, including the observed W0 LINX upstream gradient `NaN`, are failed
evidence until a physical-point repeat or finite-difference check resolves
them.

## Point-set contract

The minimum set is 64 distinct canonical `theta` points; 128 is preferred. The
final point file and checksum must be frozen before computing the gate result.
It must cover:

- standard BBN and the observationally relevant region;
- registered stiff/reheating or other extension regions;
- posterior high-density points when a reference posterior exists;
- physical and flagship decision boundaries;
- known/expected degeneracy directions;
- OOD and solver-failure critical regions.

Until the `kappa10`, `n_t`, `T_re` and stiff-transition definitions are frozen,
only the standard-BBN subset may run. Missing extension points cannot be
replaced by guessed conversions or counted toward 64.

## Derivative validation

For every derivative family:

1. evaluate at least two symmetric finite-difference step sizes;
2. require a visible local convergence interval or record nonlinearity;
3. compare native autodiff with finite differences wherever available;
4. record finite-component fraction and repeatability;
5. perturb each core scalar rate at `q_i = -2,-1,0,+1,+2` where supported;
6. perturb each accepted functional mode at `a_ik = -1,0,+1`;
7. never replace failed points with zeros, clipped values or emulator output.

## Approximate posterior outputs

The gate report must estimate, with approximation limitations shown:

- normalized posterior-center shift;
- credible-interval ratio/change;
- degeneracy rotation and conditioning;
- exclusion or decision-boundary topology risk;
- scalar-versus-functional rate difference;
- solver discrepancy floor;
- nuclear rate value-of-information for target parameters.

The observation, rate, shape and solver covariance contributions must be shown
separately before any total covariance is reported.

## Decision rule

The highest supported tier governs; uncertainty near a threshold is rounded to
the more conservative/higher tier and flagged for Pilot validation.

| Gate | Evidence | Consequence |
|---|---|---|
| `G0` | all core shifts `<0.1 sigma`, all interval changes `<5%`, and no topology change | close the Nature Astronomy discovery route for this effect; do not scale Pilot-10k |
| `G1` | any shift `0.1–0.3 sigma` or interval change `5–15%`, without G2/G3 evidence | authorize a targeted Pilot only |
| `G2` | any shift `>0.3 sigma`, interval change `>15%`, clear nonlinearity, rank inversion or topology change | authorize the full registered Track B progression, starting with Pilot-1k |
| `G3` | qualitative result changes across matched solvers or direct impact on real GW/BBN interpretation | highest priority plus independent external-style red team before production claims |

Thresholds are effect-size gates, not significance targets. A G0 result is a
valid stopping result and must not trigger broader post-hoc searches.

## Required artifact and sign-off

`artifacts/gates/FISHER_GATE_REPORT_v1.md` must contain hashes for the point
manifest, response arrays, covariance inputs, solver builds and analysis code.
The report remains `NOT EVALUATED` until all required sections are populated.

- A00 scientific lead: pending;
- A03 statistics validation: pending;
- A04 solver validation: pending;
- independent/red-team sign-off for G3: conditional and pending.
