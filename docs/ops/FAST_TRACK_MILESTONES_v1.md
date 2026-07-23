# Fast-track milestones v1 — important BBN-UQ conclusions before production scaling

> Status: **ACTIVE EXECUTION PATH**  
> Governing decision: `docs/decisions/ADR-0008-self-contained-fast-track.md`  
> Reference prior: `configs/physics/nuclear_prior_R0_reference_v1.yaml`  
> Scope: standard-BBN Stage R0 only; no JCAP/SGWB dependency

## 1. Objective

Obtain a scientifically interpretable result about nuclear-rate uncertainty and the fixed
post-hoc theoretical-covariance approximation with the smallest defensible number of direct
BBN solves.

The fast path is not a shortcut around physical validation. It is a reordering:

```text
low-dimensional deterministic designs
-> direct joint abundance distribution
-> five-point covariance drift
-> one-dimensional posterior comparison
-> conditional refinement only when the result demands it
```

The path does not wait for unpublished atlas/GP assets and does not require a neural network.

## 2. Milestone dashboard

| Milestone | Scientific question | Maximum initial solver design | Exit product | Scale trigger |
|---|---|---:|---|---|
| `FT-M0` | Is the public-information prior and solver interface fully specified? | 0 | frozen config and manifests | all fields validated |
| `FT-M1` | Are response signs, units and local linearity correct? | 9 | response table and failure audit | any sign/unit/failure issue |
| `FT-M2` | What joint abundance mean/covariance is induced at the fiducial point? | 81 | weighted distribution moments and comparator table | GH refinement discrepancy |
| `FT-M3` | Does the theory covariance drift over the relevant baryon-density range? | 5 x 81 | covariance/quantile/correlation drift map | drift >5% or nonlinearity |
| `FT-M4` | Does fixed `C_th` change the inferred `omega_b_h2` posterior? | same cached solves | `U-M0/U-M1/U-M2` posterior grid | shift >0.1 sigma or interval change >5% |
| `FT-M5` | Are tails/correlations robust? | 256–1,000 QMC draws | tail and correlation stress report | unresolved decision risk |
| `FT-M6` | Is broad production or ML justified? | 16/64-point formal gate | signed G0/G1/G2/G3 | formal decision |

The initial path through `FT-M4` uses at most 405 unique LINX parameter/nuisance nodes if
all five cosmological points use the 81-node design. Batched execution and cached nodes should
make this far cheaper than a blind 1,000-draw-per-point campaign.

## 3. FT-M0 — dependency breaker

### Inputs already available

- official ETR25 Tables 6–8 and checksums;
- ETR25 actual-percentile versus factor-uncertainty audit;
- coherent scalar and asymmetric comparator builders;
- accepted PRIMAT, PRyMordial and LINX native UQ evidence;
- validated LINX and PRyMordial reaction mappings;
- registered neutron-lifetime N0 scenario;
- correlation stress matrices.

### Required actions

1. validate `nuclear_prior_R0_reference_v1.yaml`;
2. freeze the five `omega_b_h2` values;
3. freeze standard-normal quadrature node conventions;
4. select LINX primary and PRyMordial spot-check nodes;
5. freeze raw-output units and abundance conversion rules;
6. create a run manifest and output schema;
7. mark the atlas/GP exact-rerun tasks as external, non-blocking audits.

### Exit rule

No scientific solve begins until every selected rate has a central curve, factor uncertainty,
reaction mapping, reverse-rate rule, and explicit missing-correlation treatment.

## 4. FT-M1 — nine-point response smoke

For the four standardized coordinates

```text
q_dp_gamma_he3
q_dd_n_he3
q_dd_p_t
q_tau_n
```

run the center and positive/negative axis points.

### Report

- canonical and native inputs;
- rate-curve hash for every reaction;
- abundance outputs;
- centered response per coordinate;
- expected physical sign;
- plus/minus asymmetry;
- wall time and structured failures;
- repeat drift for center and two sentinels.

### Stop immediately when

- a rate perturbation is silently ignored;
- the reverse rate does not follow the registered contract;
- output units differ across solvers;
- a deterministic repeat changes outside numerical tolerance;
- a response sign disagrees between LINX and the independent check at a non-negligible level.

## 5. FT-M2 — 81-node deterministic joint distribution

Use 3-node tensor Gauss–Hermite quadrature in four dimensions. The quadrature is a weighted
deterministic integration rule, not an empirical Monte Carlo sample.

### Compute

- weighted mean vector;
- weighted covariance and correlation matrix;
- third central moments as a nonlinearity diagnostic;
- R0-P0 versus R0-P1 versus R0-P2 differences;
- correlation-stress envelopes for selected matrices;
- weighted marginalized abundance likelihood at the fiducial cosmology;
- runtime and cost per representation.

### Required cross-checks

- compare mean/covariance with the 9-point sigma design;
- compare selected nodes with PRyMordial;
- compare the native PRIMAT MC scale without treating its different prior as a matched result;
- rerun 5-node Gauss–Hermite or 128/256 Sobol points only if convergence is insufficient.

## 6. FT-M3 — five-point covariance drift

Use common quadrature nodes at:

```text
omega_b_h2 = 0.02207, 0.02222, 0.02237, 0.02252, 0.02267
```

### Primary outputs

- `C_rate(theta)` for each point;
- relative Frobenius and eigenvalue drift from the fiducial covariance;
- D/H and `Y_p` quantile drift;
- correlation drift;
- R0-P0 versus R0-P1 drift;
- correlation-stress envelope;
- local polynomial fit and leave-one-point-out residual.

### Fast interpretation

- `<5%` stable covariance and stable correlations: fixed `C_th` remains plausible in the
  registered standard-BBN window;
- `5–15%` drift: targeted 16-point design is warranted;
- `>15%`, sign change, strong skewness, or mode-relevant behavior: move directly to the
  formal gate and prioritize distributional treatment.

## 7. FT-M4 — direct posterior grid

The first inference target is one-dimensional `omega_b_h2`; use a deterministic grid rather
than MCMC.

### Likelihoods

- `U-M0`: central solver prediction and observational covariance;
- `U-M1`: central prediction plus fixed fiducial `C_th`;
- `U-M2`: weighted direct marginal likelihood over the quadrature/QMC nuisance design.

Use stable log-sum-exp evaluation and the same observation/prior registry for all three.
Interpolate only after direct grid convergence is checked.

### Report

- posterior median/mean/mode;
- 68% and 95% intervals;
- normalized shifts relative to `U-M2`;
- interval ratios;
- posterior predictive distribution;
- data/theory covariance decomposition;
- complete solver calls and cost.

This is the earliest milestone capable of answering the central project question with a direct
posterior consequence.

## 8. FT-M5 — conditional tail and robustness refinement

Activate only for one of these reasons:

- 81- versus 625-node quadrature disagreement;
- visible skewness/tail probability relevant to the likelihood;
- sensitivity to correlation stress;
- `U-M1/U-M2` shift near or above the frozen threshold;
- publication-grade direct-MC validation.

Use scrambled Sobol sequences with cumulative sizes 128/256/512/1024 and common random
numbers across cosmological points. Randomize with at least four independent scrambles when
estimating integration error.

Do not run 10,000 or 100,000 draws unless a measured convergence failure requires them.

## 9. FT-M6 — formal scale decision

### G0

- posterior shift `<0.1 sigma`;
- interval change `<5%`;
- no topology change;
- direct workload affordable.

Action: publish or record the validity domain/null result; no new ML production.

### G1

Modest covariance/PDF/correlation effect or repeated-workload benefit.

Action: targeted 16-point design and simple conditional Gaussian/MLP baselines.

### G2

Important drift, tail, posterior effect, or repeated direct cost.

Action: 64-point design, broader reaction set, calibrated learned distribution or ratio method.

### G3

Qualitative inference change or matched solver disagreement.

Action: independent red team, publication-prior upgrade, and high-impact application review.

## 10. Parallel non-blocking lane

The following proceed in parallel and do not block `FT-M0` through `FT-M4`:

- request upstream atlas generator/configuration;
- request GP analysis package, data and posterior draws;
- implement a clean-room GP only if the scalar/asymmetric comparison shows a decision-relevant
  need for function-valued uncertainty;
- obtain A00/A03/A09 signatures before publication-grade claims;
- repair PRIMAT project-owned ETR25 curve injection before a matched multi-solver claim.

## 11. Definition of fast-track success

Within the first four milestones the project must produce one of two outcomes:

1. a quantitative demonstration that fixed `C_th` is adequate over the registered R0 domain,
   with a measured validity bound; or
2. a quantitative demonstration that rate-PDF shape, covariance drift, abundance correlation,
   or direct marginalization changes the posterior enough to justify the next stage.

Either outcome is scientifically useful. Reaching neither outcome means the execution path is
still focused on infrastructure rather than the research question.
