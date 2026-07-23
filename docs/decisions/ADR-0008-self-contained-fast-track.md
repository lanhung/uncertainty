# ADR-0008 — Self-contained fast path and external-reproduction decoupling

> Status: **ACCEPTED FOR EXECUTION**  
> Decision date: 2026-07-23  
> Scope: Stage-R0 BBN nuclear-rate uncertainty  
> Supersedes: the interpretation that exact reproduction of the 2026 sensitivity-atlas slice and the unpublished GP abundance run must block all project-owned R0 experiments  
> Does not supersede: claim, provenance, calibration, or independent-sign-off requirements for publication-grade results

## 1. Context

The repository has completed every currently executable task that does not require an
upstream release or an independent scientific signature. The native direct uncertainty
baselines have the following frozen status:

- PRIMAT native Monte Carlo: accepted;
- PRyMordial native rate marginalization: accepted;
- LINX native `nuclear_rates_q`: accepted under the stricter preregistered v2 protocol;
- 2026 sensitivity-atlas exact slice reproduction: not accepted because the public result
  tables do not include the generator code, exact solver revision, or complete configuration;
- 2026 GP deuterium abundance rerun: externally blocked because the analysis code, fitted
  hyperparameters, exact data bundle, posterior draws, and random seed are not public.

The two failed/blocked literature reproductions are useful external audits, but neither is a
source of the project prior and neither is logically required to test the repository's primary
question:

> how rate uncertainty propagates through a BBN solver into the joint abundance distribution,
> and when a fixed post-hoc theoretical covariance is or is not adequate.

Keeping those two exact reproductions on the production dependency chain would make the
project completion time depend on assets that the project cannot create honestly. It would
also prevent use of already captured ETR25 tables and the three accepted direct solvers.

## 2. Decision

### 2.1 Separate three evidence classes

The project now distinguishes:

1. **Core direct baselines** — PRIMAT, PRyMordial, and LINX. These are mandatory and already
   accepted for C0 calibration.
2. **External paper reproductions** — the sensitivity atlas and GP abundance result. These
   remain frozen external audits. Their exact reproduction is desirable but non-blocking.
3. **Project-owned reference-prior experiments** — self-contained calculations using only
   versioned public information already captured by this repository.

An external paper reproduction may never be relabeled as accepted by weakening its frozen
threshold after inspection. Instead, it is retained as negative or blocked evidence and removed
from dependencies that it cannot logically satisfy.

### 2.2 Freeze a public-information R0 reference-prior family

The first project-owned calculations may use the following explicitly labeled prior family:

- **R0-P0 — ETR25 scalar log-normal reference**: ETR25 median and factor uncertainty, with
  one standard-normal coordinate per reaction held coherent over temperature;
- **R0-P1 — asymmetric quantile-matched comparator**: the already registered rank-one
  transformation matching public p16/p50/p84 curves, explicitly not an actual posterior
  reconstruction;
- **R0-P2 — legacy solver-envelope comparator**: pinned LINX/PRyMordial/PRIMAT native
  representations for interface and lineage checks;
- **R0-C0… — correlation stress family**: identity as an engineering anchor plus the frozen
  positive/negative correlation stress matrices. Missing covariance is not interpreted as
  physical independence.

This family is sufficient for an internally reproducible sensitivity and approximation study.
It is not described as the unique nuclear-data posterior, and it does not close the later
publication-prior upgrade.

### 2.3 Use a solver path that does not require unresolved PRIMAT curve injection

The first reference-prior propagation uses LINX as the fast primary path and PRyMordial as an
independent direct check. PRIMAT native MC remains the precision/native reference. Project-owned
ETR25 curve injection into PRIMAT is not required before the first milestones because the
per-draw reverse-cap/injection regression remains unresolved.

This avoids turning a solver-specific reverse-rate implementation detail into a project-wide
blocker. PRIMAT injection is restored as a required matched-solver check only before a claim of
solver independence or publication-grade multi-solver factorization.

### 2.4 Replace brute-force-first execution with deterministic low-dimensional designs

Stage R0 has only three thermonuclear nuisance coordinates plus the separately registered
neutron-lifetime/weak nuisance. Before any 1,000- or 10,000-draw run, execute:

1. a `2d+1` sigma-point smoke (`d=4`, therefore 9 points);
2. a 3-node tensor Gauss–Hermite design (`3^4 = 81` points);
3. a 5-node design or sparse-grid refinement only when the 81-point result is not converged;
4. a scrambled Sobol/QMC tail check only when quantiles or non-Gaussianity require it.

The same standardized nodes and common random numbers are reused across cosmological points.
This makes covariance drift distinguishable from Monte Carlo noise.

### 2.5 Add a direct one-dimensional posterior milestone

For Stage R0, the active cosmological parameter is `omega_b_h2`. A full MCMC is unnecessary
for the first decision. Evaluate the marginalized abundance likelihood on a frozen one-dimensional
`omega_b_h2` grid using direct quadrature/QMC over the nuisance coordinates. Compare:

- `U-M0`: central rates;
- `U-M1`: constant post-hoc covariance;
- `U-M2`: direct nuisance marginalization.

This produces a decision-relevant posterior shift and credible-interval ratio before any neural
network is trained.

## 3. What can and cannot be solved internally

### 3.1 Internally solvable now

Using current repository contents, the project can:

- freeze the reference-prior family above;
- complete LINX and PRyMordial rate mappings and structured-failure checks;
- generate 9-, 81-, 256-, or 1,000-point direct designs;
- measure abundance covariance, correlation, skewness, tails, and convergence;
- map covariance drift over a small `omega_b_h2` design;
- compare `U-M1` and `U-M2` on a one-dimensional posterior grid;
- estimate the actual cost of direct inference;
- decide whether a learned model is necessary.

### 3.2 Not internally recoverable without inventing evidence

The project cannot reconstruct uniquely:

- the unpublished sensitivity-atlas generator configuration;
- the unpublished GP fit hyperparameters, posterior draws, exact data bundle, or seed;
- the true cross-temperature and cross-reaction copula from pointwise p16/p50/p84 tables alone;
- independent A00/A03/A09 human scientific signatures.

These are recorded as limitations rather than silently synthesized. Clean-room alternatives are
allowed, but they must carry new project identifiers and may not be called exact reproductions.

## 4. Milestone events

### M0 — dependency break and reference-prior freeze

**Target duration:** less than one working day.  
**Exit evidence:** a validated reference-prior configuration, selected primary/secondary solver
paths, frozen nodes, units, reverse-rate policy, and explicit claim boundary.

### M1 — nine-point response smoke

**Target duration:** hours.  
**Design:** center plus positive/negative sigma points for the three rates and weak nuisance.  
**Exit evidence:** correct response signs, local linearity/nonlinearity indicator, no structured
failures, and a first variance estimate.

### M2 — 81-point deterministic distribution

**Target duration:** hours on LINX; same-day independent spot checks.  
**Exit evidence:** mean, covariance, correlation, skewness proxy, convergence against the
nine-point result, and direct comparison of R0-P0/R0-P1/R0-P2.

### M3 — five-point cosmological drift scan

**Target duration:** less than one day.  
**Design:** frozen `omega_b_h2` points at the prior mean and symmetric offsets covering the
observationally relevant interval.  
**Exit evidence:** drift of `C_rate(theta)`, quantiles, correlations, and the first fixed-`C_th`
validity estimate.

### M4 — direct posterior grid

**Target duration:** less than one day after M3.  
**Exit evidence:** normalized posterior shift, credible-interval ratio, posterior-predictive
comparison, and complete direct cost for `U-M0/U-M1/U-M2`.

### M5 — tail and robustness refinement, conditional

Run 256/512 scrambled Sobol points, 1,000 direct draws, additional correlation models, or a
second full solver only when M2–M4 show unresolved tail, nonlinearity, or decision risk.

### M6 — formal 16/64-point and learned-model gate, conditional

The existing 16-point smoke and 64-point formal gate remain publication-grade expansion steps.
They are not prerequisites for obtaining the first important conclusion.

## 5. Fast stop/scale rules

- If the 9- and 81-point moments agree within 2% of the theoretical standard deviation and
  the direct posterior shift is below `0.05 sigma`, do not run 1,000 draws solely for volume.
- If the five-point covariance drift is below 5%, correlations are stable, and `U-M1` versus
  `U-M2` stays below `0.1 sigma` with interval ratios in `[0.95, 1.05]`, record an R0 validity
  domain and stop ML scaling.
- If R0-P0 versus R0-P1 changes the direct posterior by more than `0.1 sigma`, prioritize
  nuclear-PDF modeling before enlarging the reaction set.
- If correlation stress models dominate the result, report an identified nuclear-data
  information gap rather than selecting the most favorable covariance.
- If direct LINX/PRyMordial completes M1–M4 cheaply, close the speed-only emulator claim.
- If M3/M4 reveal a meaningful failure of fixed `C_th`, authorize the 16/64-point gate and
  only then consider `U-M3/U-M4`.

## 6. Scientific claim boundary

Results produced under the reference-prior family are conditional on that explicitly registered
family. They may support claims about:

- the validity or failure of a public log-normal approximation;
- parameter dependence of the induced joint abundance covariance;
- sensitivity to missing cross-reaction correlation assumptions;
- direct-versus-post-hoc inference under public information;
- direct solver economics.

They may not support claims that the complete experimental nuclear posterior has been
reconstructed or that all nuclear-data systematics have been marginalized.

## 7. Consequences

### Positive

- The active project no longer waits indefinitely for unpublished upstream assets.
- The first posterior-level result requires hundreds, not millions, of solver calls.
- Native direct tools are used before new ML development.
- External negative/blocked reproductions remain visible and honest.
- Human sign-off is moved to publication claims rather than exploratory computation.

### Costs and risks

- The first prior is a documented reference family rather than a unique nuclear posterior.
- A later publication-prior upgrade may change quantitative bands.
- Tensor Gauss–Hermite designs become inefficient after substantial reaction-set expansion;
  sparse grids/QMC or learned methods will then be needed.
- Conditional conclusions must not be overgeneralized.

## 8. Required repository changes

- update `plan/plan.yaml` to separate external reproduction audits from the active dependency
  chain;
- add a reference-prior configuration;
- add a milestone runbook;
- retain the existing blocker artifacts unchanged;
- keep publication-grade sign-off and the Nature-tier gate closed until the formal evidence
  exists.
