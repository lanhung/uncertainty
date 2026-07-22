# BBN nuclear-rate uncertainty scope v1

> Status: **ACTIVE SCIENTIFIC SCOPE**  
> Effective date: 2026-07-23  
> Governing decision: `docs/decisions/ADR-0006-uncertainty-core-refocus.md`

## 1. Project question

This repository is for one primary problem:

> How can nuclear-reaction-rate uncertainty be propagated through the coupled BBN ODE network into calibrated abundance distributions and cosmological posteriors, without relying on a fixed post-hoc theoretical-error approximation?

The current JCAP stiff-phase manuscript is not a dependency of this program. It may later provide a non-standard-cosmology case study, but manuscript release, lithium no-go reproduction, SGWB inference and paper submission are outside the active critical path.

## 2. Physical and statistical formulation

Let

- `theta` denote the low-dimensional cosmological parameters of interest;
- `z` denote thermonuclear-rate nuisance variables;
- `tau_n` and weak-rate quantities denote separately registered weak-physics nuisances;
- `s` denote the chosen numerical solver, rate compilation and network;
- `y` denote the primordial abundance vector.

The high-fidelity simulator is

```text
y = S(theta, z, tau_n; s)
```

with a scalar rate baseline

```text
log r_i(T) = log rbar_i(T) + z_i sigma_i(T),   z ~ N(0, C_z).
```

The central scientific object is the induced conditional abundance distribution

```text
p(y | theta, s) = integral p(y | theta, z, tau_n, s)
                         p(z, tau_n | s) dz d tau_n.
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

## 3. What counts as progress

A result advances the project only if it establishes at least one of the following:

1. a validated solver interface that perturbs physical rate nuisances and returns structured failures;
2. a measured convergence result for Monte Carlo abundance bands;
3. evidence that `C_rate(theta)` is non-constant, non-Gaussian or correlated across abundances;
4. a calibrated forward emulator `f(theta, z)` or marginalized model `p(y | theta)`;
5. a posterior comparison among central-rate, post-hoc-error, explicit-marginalization and learned-marginalization treatments;
6. a measured reduction in high-fidelity calls at matched posterior fidelity and coverage;
7. a physically important change in a cosmological conclusion after full marginalization.

Documentation, dashboards, manuscript release work and generic architecture experiments do not count as scientific progress unless they directly enable one of these items.

## 4. Staged reaction sets

The eventual nuisance space may contain dozens to approximately one hundred rates. The project must not begin with an undifferentiated full-network model.

### Stage R0 — mechanics and calibration

Use the three dominant deuterium-burning reactions:

```text
d(p,gamma)3He
d(d,n)3He
d(d,p)t
```

Treat neutron lifetime and weak-rate normalization separately. This stage establishes rate perturbation, abundance covariance, Monte Carlo convergence and the point-to-distribution map for `Y_p` and `D/H`.

### Stage R1 — four-abundance core

After R0 passes, add the leading `3He/7Be/7Li` production and destruction channels needed for calibrated `3He/H` and `7Li/H` uncertainty. The precise set is selected from published sensitivity and solver registries before execution; no lithium-specific claim is preselected.

### Stage R2 — core network

Expand to a preregistered set of roughly 10–20 reactions only when R0/R1 show missing variance or posterior sensitivity.

### Stage R3 — full-network stress

Use the full solver network only as a stress test, coverage audit or production requirement justified by earlier gates.

## 5. Fixed inference ladder

All implementations and papers use the following labels.

- `U-M0`: central-rate deterministic solver.
- `U-M1`: constant post-hoc theoretical covariance.
- `U-M2`: direct Monte Carlo or explicit joint marginalization over rate nuisances.
- `U-M3`: conditional forward emulator `f(theta, z)`.
- `U-M4`: learned marginalized abundance distribution `p(y | theta)`.
- `U-M5`: multi-solver/rate-library hierarchical treatment.
- `U-M6`: hybrid emulator with explicit direct-solver fallback.

No model is accepted solely because its pointwise MSE is small. Acceptance requires abundance-distribution calibration and posterior recovery.

## 6. Immediate experiments

### E0 — fixed-cosmology Monte Carlo benchmark

At a frozen standard-BBN point:

1. generate 1,000 nuisance draws;
2. compare with 3,000 and 10,000 draws when convergence requires it;
3. record empirical mean, covariance, skewness, tails and abundance correlations;
4. measure CPU time, failures and effective sample size;
5. reproduce theoretical bands on Schramm-style abundance curves.

### E1 — constant-error audit

At 16 cosmological points, test whether a covariance estimated at one fiducial point remains valid elsewhere. Report relative covariance drift, quantile drift and non-Gaussian diagnostics.

### E2 — formal 64-point response gate

Freeze 64 standard/posterior/boundary points and compute finite-difference or validated autodiff responses to `theta`, rate nuisances and weak nuisances. This gate decides whether production-scale data generation is warranted.

### E3 — emulator comparison

Train the simplest strong baselines first:

1. deterministic conditional MLP for `f(theta, z)`;
2. ensemble/heteroscedastic baseline;
3. conditional density model for `p(y | theta)` only if the empirical distribution requires it.

GAN, diffusion, normalizing flow or Transformer architectures are not predetermined.

### E4 — inference comparison

Using the same data, priors and solver physics, compare `U-M0` through `U-M4` on posterior location, interval width, topology, posterior predictive calibration and end-to-end cost.

## 7. Self-contained implementation policy

The project may be implemented from scratch using public and pinned solvers, rate tables and nuclear-data products. This is the default if private legacy assets are absent.

Permitted sources include audited public versions of LINX, PRyMordial, PRIMAT, PArthENoPE and AlterBBN, subject to their licences and exact revision capture. Newly generated training labels must be produced by an approved numerical solver. AI-generated, interpolated or augmented values that were not validated by a solver cannot be treated as physical truth.

The minimum clean-room path is

```text
public solver and rate-prior audit
-> common nuisance interface
-> fixed-point Monte Carlo bands
-> 16-point covariance-drift smoke
-> 64-point formal gate
-> conditional emulator baselines
-> posterior recovery
-> optional non-standard cosmology application.
```

## 8. Validation thresholds

Before a learned model enters cosmological inference:

- every core posterior median shift relative to direct inference must be below `0.1 sigma`;
- every core credible-interval ratio must lie in `[0.95, 1.05]`;
- no posterior mode or decision-boundary topology may be lost;
- in-domain structured failure rate must be below `1%`;
- nominal 68% and 95% predictive/parameter coverage must pass preregistered tests;
- OOD and solver failures must be explicit, never silently clipped;
- direct-solver challenge points must include tails and rate-prior boundaries.

## 9. Stop and scale rules

- If 1,000 draws already converge for the required bands, do not run 100,000 merely to create a larger dataset.
- If `C_rate(theta)` is effectively constant and posterior differences remain below the null thresholds, close the distributional-physics claim and report the bound honestly.
- If direct solvers finish the registered inference workload within the existing two-worker budget, speed alone does not justify a new emulator.
- If 16-point smoke reveals substantial covariance drift, non-Gaussian tails or posterior-risk warnings, proceed to the formal 64-point gate.
- Pilot-1k/Pilot-10k, function-valued rate modes and Nature-tier campaigns require a signed gate decision.

## 10. Non-goals of the active plan

The following are not current critical-path tasks:

- submission or reproduction of the separate JCAP manuscript;
- proving or revisiting a stiff-phase lithium no-go;
- SGWB/SageNet integration;
- recovery of private legacy checkpoints as a prerequisite;
- debugging every feature of ABCMB or LINX;
- starting from all approximately one hundred rates;
- choosing a fashionable generative architecture before the distribution is measured;
- claiming a Nature-tier result before the physical effect and method necessity are established.
