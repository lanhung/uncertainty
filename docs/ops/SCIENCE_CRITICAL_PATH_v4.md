# Science critical path v4 — self-contained BBN-UQ milestone path

> Effective date: 2026-07-23  
> Governing decisions: `ADR-0006`, `ADR-0007`, `ADR-0008`  
> Scientific scope: `docs/science/UNCERTAINTY_SCOPE_v1.md`  
> Milestone details: `docs/ops/FAST_TRACK_MILESTONES_v1.md`  
> Desired state: `plan/plan.yaml` version 6

## 1. Active deliverable

Produce a direct, reproducible answer to this question:

> Under a versioned public-information nuclear-rate prior family, how does the joint BBN abundance distribution vary with `omega_b_h2`, and when does a fixed post-hoc theoretical covariance reproduce or bias direct nuisance marginalization?

The separate JCAP/SGWB work is not a dependency. Exact reproduction of unpublished atlas or GP assets is not a dependency. No learned model is active before the direct fast gate.

## 2. Evidence classes

### Mandatory core

- ETR25 Tables 6–8 and the rate-PDF approximation audit;
- accepted PRIMAT native Monte Carlo;
- accepted PRyMordial native marginalization;
- accepted LINX v2 rate-perturbation calibration;
- versioned reaction mappings, units, weak treatment, failures and costs.

### Non-blocking external audits

- exact 2026 sensitivity-atlas reproduction;
- exact 2026 GP abundance-distribution reproduction.

These remain visible as negative or blocked evidence. They cannot be converted into passes by relaxing frozen thresholds, but they also do not define the project prior.

### Publication upgrade

- original or reproducible nuclear posterior when available, or explicit conditional prior-family scope;
- nuclear-data and scientific review;
- independent validation;
- matched second-solver evidence for any solver-independent claim.

Publication upgrade does not block exploratory direct milestones.

## 3. Phase UQ0 — reference prior and direct adapter

Freeze `configs/physics/nuclear_prior_R0_reference_v1.yaml` with the ETR25 scalar log-normal reference, asymmetric quantile-matched comparator, legacy solver-envelope comparator, correlation stress family, neutron-lifetime N0 nuisance, and an explicit statement that this is not the unique experimental posterior.

Implement the fast path on LINX as the primary batched solver and PRyMordial as the independent selected-node check. PRIMAT native Monte Carlo remains a precision reference. Project-owned ETR25 injection into PRIMAT is deferred until its reverse-cap and injection regressions pass.

Validate central, plus/minus, coherent-curve, units, reverse mapping, repeatability and structured failures before any weighted design.

## 4. Phase UQ1 — first conclusions with hundreds of calls

### FT-M1 — nine-point response smoke

Run the center and positive/negative axis points for three rates and neutron lifetime. Produce response signs, local curvature, failures and cross-solver spot checks.

### FT-M2 — 81-node direct distribution

Run 3-node tensor Gauss–Hermite quadrature in four nuisance dimensions. Compute weighted abundance means, joint covariance, correlations, third moments, marginalized likelihood values, and differences among the registered prior representations. Refine only when the 81-node result does not converge.

### FT-M3 — five-point covariance drift

Reuse identical standardized nodes at five frozen `omega_b_h2` values. Measure covariance, quantile, correlation and representation drift. Common nodes are mandatory to suppress integration-noise differences.

### FT-M4 — direct posterior grid

On a deterministic `omega_b_h2` grid compare:

```text
U-M0 central rate
U-M1 fixed fiducial C_th
U-M2 direct quadrature or QMC marginalization
```

Report posterior shifts, interval ratios, posterior predictive behavior and total cost. This is the earliest decision-level scientific milestone.

### Fast gate

Choose one: stop with a registered R0 validity domain; run targeted quadrature or QMC tail refinement; or authorize the formal 16/64-point path. A 1,000-draw run is a conditional cross-check, not an automatic prerequisite.

## 5. Phase UQ2 — conditional publication-grade expansion

Run only when the fast gate identifies a decision-relevant effect or unresolved numerical risk:

1. 16-point covariance, PDF and tail smoke;
2. frozen 64-point response set;
3. direct workload economics including repeated posteriors and SBC;
4. method baseline manifest;
5. publication-prior and sign-off upgrade;
6. G0/G1/G2/G3 report.

## 6. Low-cost algorithms

Use in this order:

1. sigma points for response diagnostics;
2. Gauss–Hermite quadrature for the four-dimensional Gaussian reference;
3. sparse-grid or scrambled Sobol QMC for asymmetric, tail and correlation refinement;
4. low-order polynomial response fits with held-out residual checks;
5. direct one-dimensional posterior grids;
6. only then conditional emulators, ratio estimators or learned distributions.

All nodes, weights and transforms must be written to immutable manifests. Weighted quadrature output is not mislabeled as an empirical sample.

## 7. Immediate milestone events

1. **Reference-prior freeze** — validate the new config and select primary and secondary solver paths.
2. **Nine-point smoke** — stop on any mapping, unit, reverse-rate or repeatability failure.
3. **81-node fiducial distribution** — produce the first direct joint abundance covariance and representation comparison.
4. **Five-point drift map** — determine whether fixed covariance is plausibly stable.
5. **Direct posterior grid** — obtain the first answer to the central project question.
6. **Scale decision** — only measured effect size and cost can authorize 1,000 draws, 16/64 points, broader rates or machine learning.

## 8. Stop and scale thresholds

- fast posterior shift below `0.05 sigma`: no immediate refinement unless tails are unresolved;
- null boundary: below `0.1 sigma`, interval ratio in `[0.95,1.05]`, no topology change;
- covariance drift below 5%: fixed `C_th` plausible in the registered R0 domain;
- covariance drift from 5% to 15%: targeted 16-point follow-up;
- covariance drift above 15%, significant tails, or posterior decision change: formal 64-point gate;
- direct workload affordable: close the speed-only learned-model claim;
- prior-representation sensitivity dominant: prioritize nuclear PDF and correlation modeling, not a larger network.

## 9. Definition of progress

Scientific progress is a validated reference-prior solve, a completed weighted direct distribution, a measured covariance or quantile drift, a direct `U-M1/U-M2` posterior comparison, a tail or correlation stress result, or a signed scale decision.

Waiting for an upstream archive, adding governance documents, or running unrelated solver audits is not progress on the active critical path.
