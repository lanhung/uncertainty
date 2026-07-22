# BBN nuclear-rate uncertainty scope v1.1

> Status: **ACTIVE SCIENTIFIC SCOPE**  
> Effective date: 2026-07-23  
> Governing decisions: `ADR-0006-uncertainty-core-refocus.md`, `ADR-0007-frontier-literature-2026-07.md`  
> Frontier review: `docs/literature/FRONTIER_REVIEW_2026-07.md`

## 1. Project question

This repository is for one primary problem:

> How can nuclear-reaction-rate uncertainty be propagated through the coupled BBN ODE network into calibrated abundance distributions and cosmological posteriors, without relying on a fixed post-hoc theoretical-error approximation?

The current JCAP stiff-phase manuscript is not a dependency of this program. It may later provide a non-standard-cosmology case study, but manuscript release, lithium no-go reproduction, SGWB inference and paper submission are outside the active critical path.

## 2. Physical and statistical formulation

Let

- `theta` denote the low-dimensional cosmological parameters of interest;
- `z` denote scalar thermonuclear-rate nuisance variables;
- `u` denote original nuclear-data/posterior draws that generate coherent rate curves;
- `tau_n` and weak-rate quantities denote separately registered weak-physics nuisances;
- `s` denote the chosen numerical solver, rate compilation and network;
- `y` denote the primordial abundance vector.

The high-fidelity simulator is

```text
y = S(theta, r(T; u or z), tau_n; s).
```

The scalar approximation is

```text
log r_i(T) = log rbar_i(T) + z_i sigma_i(T),   z ~ N(0, C_z).
```

It is a baseline transport model, not an assumption that every evaluated rate density is exactly log-normal. Where an original nuclear posterior or Monte Carlo input model is available, a draw must produce a coherent rate curve over temperature.

The central scientific object is the induced conditional abundance distribution

```text
p(y | theta, s) = integral p(y | theta, u, z, tau_n, s)
                          p(u, z, tau_n | s) du dz d tau_n.
```

The target posterior is

```text
p(theta | d) proportional to p(theta)
    integral p(d | y) p(y | theta, s) dy.
```

The project must compare this distributional treatment against the common two-stage approximation

```text
C_like = C_obs + C_th,constant.
```

## 3. Frontier constraints and non-duplication rule

The July 2026 review establishes that direct BBN Monte Carlo, scalar log-normal rate nuisances, explicit PRyMordial marginalization, native PRIMAT Monte Carlo, LINX joint CMB+BBN rate marginalization, standard sensitivity rankings, GP treatment of the three deuterium reactions and generic nuisance-marginal SBI already exist.

Consequently:

- a fixed-point Monte Carlo band is a reproduction/calibration milestone, not a novelty claim;
- the three dominant deuterium reactions are a mechanics set, not a discovery;
- a normalizing flow, ratio estimator or Transformer is a baseline method family, not a contribution by name;
- a new emulator is justified only by measured end-to-end necessity;
- the first potentially new object is the joint, calibrated, parameter-dependent abundance distribution and its consequence for the validity of fixed `C_th`.

ETR25 is the primary candidate R0 experimental-rate source. Its low/median/high values are actual rate-density percentiles, while its factor uncertainty uses a log-normal approximation. The project must compare these representations rather than silently replacing the former by the latter.

## 4. What counts as progress

A result advances the project only if it establishes at least one of the following:

1. a validated solver interface that perturbs physical rate nuisances and returns structured failures;
2. a measured convergence result for Monte Carlo abundance bands;
3. a validated comparison between actual/posterior rate distributions and scalar log-normal approximations;
4. evidence that `C_rate(theta)` is non-constant, non-Gaussian or correlated across abundances;
5. a calibrated forward emulator `f(theta, z)` or marginalized model `p(y | theta)`;
6. a posterior comparison among central-rate, post-hoc-error, explicit-marginalization and learned-marginalization treatments;
7. a measured reduction in high-fidelity calls at matched posterior fidelity and coverage;
8. a physically important change in a cosmological conclusion after full marginalization.

Documentation, dashboards, manuscript release work and generic architecture experiments do not count as scientific progress unless they directly enable one of these items.

## 5. Staged reaction sets

The eventual nuisance space may contain dozens to approximately one hundred rates. The project must not begin with an undifferentiated full-network model.

### Stage R0 — mechanics, nuclear-PDF audit and calibration

Use the three dominant deuterium-burning reactions:

```text
d(p,gamma)3He
d(d,n)3He
d(d,p)t
```

Treat neutron lifetime and weak-rate normalization separately. This stage establishes:

- ETR25 or equivalent source ingestion and exact provenance;
- actual/posterior rate-density versus scalar log-normal comparison;
- coherent temperature-dependent rate draws;
- solver rate-ID mappings;
- abundance covariance and Monte Carlo convergence;
- the point-to-distribution map for `Y_p` and `D/H`.

### Stage R1 — four-abundance core

After R0 passes, add the leading `3He/7Be/7Li` production and destruction channels needed for calibrated `3He/H` and `Li7/H` uncertainty. The precise set is selected from published sensitivity and original rate-posterior registries before execution; no lithium-specific claim is preselected.

### Stage R2 — core network

Expand to a preregistered set of roughly 10–20 reactions only when R0/R1 show missing variance, coverage failure or posterior sensitivity.

### Stage R3 — full-network stress

Use the full solver network only as a stress test, coverage audit or production requirement justified by earlier gates.

## 6. Fixed inference ladder

All implementations and papers use the following labels.

- `U-M0`: central-rate deterministic solver.
- `U-M1`: constant post-hoc theoretical covariance.
- `U-M2`: direct Monte Carlo or explicit joint marginalization over rate nuisances.
- `U-M3`: conditional forward emulator `f(theta, z)` or `f(theta, u)`.
- `U-M4`: learned marginalized abundance distribution `p(y | theta)`.
- `U-M5`: multi-solver/rate-library hierarchical treatment.
- `U-M6`: hybrid emulator with explicit direct-solver fallback.

No model is accepted solely because its pointwise MSE is small. Acceptance requires abundance-distribution calibration and posterior recovery.

## 7. Mandatory direct baselines before learned models

The project must reproduce or explicitly document a blocker for:

1. PRIMAT native `run_mc()` / `mc_uncertainty()` at the frozen point;
2. PRyMordial explicit rate marginalization;
3. LINX central and `nuclear_rates_q` perturbations;
4. one R0 slice from the 2026 sensitivity atlas;
5. the prior/thermal-propagation structure of the 2026 GP deuterium analysis.

These baselines prevent reimplementation of existing functionality and define the direct cost floor.

## 8. Immediate experiments

### E0 — rate-PDF and native-MC audit

Before a custom production driver:

1. ingest and hash ETR25 R0 source products;
2. validate units and temperature semantics;
3. compare actual/posterior percentiles with the log-normal approximation in the BBN window;
4. reproduce PRIMAT native Monte Carlo and one PRyMordial/LINX uncertainty path;
5. validate coherent rate-curve sampling and structured failures.

### E1 — fixed-cosmology Monte Carlo benchmark

At a frozen standard-BBN point:

1. generate 1,000 nuisance draws;
2. compare cumulative results at `N=100,300,1000`;
3. extend to 3,000 or 10,000 only when convergence requires it;
4. record empirical mean, covariance, skewness, tails and abundance correlations;
5. compare actual/posterior and scalar-lognormal rate models;
6. measure CPU time, failures and effective sample size;
7. reproduce theoretical bands on Schramm-style abundance curves.

### E2 — constant-error audit

At 16 cosmological points, test whether a covariance estimated at one fiducial point remains valid elsewhere. Report relative covariance drift, quantile drift, joint-correlation drift, non-Gaussian diagnostics and rate-PDF-model dependence.

### E3 — formal 64-point response and novelty gate

Freeze 64 standard/posterior/boundary points and compute finite-difference or validated autodiff responses to `theta`, rate nuisances and weak nuisances. This gate decides whether production-scale data generation and a new learned model are scientifically warranted.

### E4 — emulator and SBI comparison

Only after `G1+`, compare in order:

1. deterministic conditional MLP for `f(theta,z)`;
2. heteroscedastic multivariate Gaussian and deep ensemble;
3. mixture or calibrated quantile model;
4. TMNRE/AMNRE-style marginal ratio estimation;
5. neural likelihood or flow only if direct distribution diagnostics require it;
6. calibrated multi-fidelity or function-valued models only when the relevant need is measured.

GAN, diffusion, normalizing flow or Transformer architectures are not predetermined.

### E5 — inference comparison

Using the same data, priors and solver physics, compare `U-M0` through authorized learned models on posterior location, interval width, topology, posterior predictive calibration and end-to-end cost.

## 9. Self-contained implementation policy

The project may be implemented from scratch using public and pinned solvers, rate tables and nuclear-data products. This is the default if private legacy assets are absent.

Permitted sources include audited public versions of LINX, PRyMordial, PRIMAT, PArthENoPE and AlterBBN, plus ETR25 and original nuclear posterior products, subject to licences and exact revision capture. Newly generated training labels must be produced by an approved numerical solver. AI-generated, interpolated or augmented values that were not validated by a solver cannot be treated as physical truth.

The minimum clean-room path is

```text
frontier and nuclear-source audit
-> coherent rate-prior ingestion
-> native direct-baseline reproduction
-> common nuisance interface
-> fixed-point Monte Carlo bands
-> 16-point covariance-drift smoke
-> 64-point formal gate
-> conditional emulator/SBI baselines
-> posterior recovery
-> optional non-standard cosmology application.
```

## 10. Validation thresholds

Before a learned model enters cosmological inference:

- every core posterior median shift relative to direct inference must be below `0.1 sigma`;
- every core credible-interval ratio must lie in `[0.95, 1.05]`;
- no posterior mode or decision-boundary topology may be lost;
- in-domain structured failure rate must be below `1%`;
- nominal 68% and 95% predictive/parameter coverage must pass preregistered tests;
- both prior SBC and posterior-focused SBC are required;
- multiple training seeds and model/ensemble uncertainty must be reported;
- OOD and solver failures must be explicit, never silently clipped;
- direct-solver challenge points must include tails and rate-prior boundaries.

## 11. Stop and scale rules

- If 1,000 draws already converge for the required bands, do not run 100,000 merely to create a larger dataset.
- If actual/posterior and scalar-lognormal rate treatments differ below all frozen null thresholds, retain the scalar baseline and report the bound.
- If `C_rate(theta)` is effectively constant and posterior differences remain below the null thresholds, close the distributional-physics claim and report the validity domain honestly.
- If direct solvers finish the registered inference and calibration workload within the existing worker budget, speed alone does not justify a new emulator.
- If the 16-point smoke reveals substantial covariance drift, non-Gaussian tails, rate-PDF-shape effects or posterior-risk warnings, proceed to the formal 64-point gate.
- Pilot-1k/Pilot-10k, broader reaction sets, function-valued modes and Nature-tier campaigns require a signed gate decision.

## 12. Non-goals of the active plan

The following are not current critical-path tasks:

- submission or reproduction of the separate JCAP manuscript;
- proving or revisiting a stiff-phase lithium no-go;
- SGWB/SageNet integration;
- recovery of private legacy checkpoints as a prerequisite;
- debugging every feature of ABCMB or LINX;
- starting from all approximately one hundred rates;
- reimplementing native PRIMAT/PRyMordial Monte Carlo without first reproducing it;
- choosing a fashionable generative architecture before the distribution is measured;
- claiming a Nature-tier result before the physical effect and method necessity are established.
