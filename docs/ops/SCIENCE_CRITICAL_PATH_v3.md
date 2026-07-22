# Science critical path v3 — BBN nuclear-rate uncertainty only

> Effective date: 2026-07-23  
> Governing decision: `docs/decisions/ADR-0006-uncertainty-core-refocus.md`  
> Scientific scope: `docs/science/UNCERTAINTY_SCOPE_v1.md`

## 1. Deliverable

The active project has one deliverable:

> A self-contained, calibrated and computationally audited treatment of BBN nuclear-reaction-rate uncertainty, from solver perturbations to abundance distributions and cosmological posterior marginalization.

The separate JCAP stiff/SGWB manuscript is not part of this critical path.

## 2. First scientific figure

The first required paper-quality result is not a posterior corner plot and not a new neural-network architecture. It is a solver-grounded theoretical-band figure showing, at frozen cosmological inputs:

- central abundance curves;
- Monte Carlo 68% and 95% bands from physical rate perturbations;
- convergence of those bands with nuisance sample count;
- cross-abundance correlations;
- comparison of direct Monte Carlo with a constant-`sigma_th` approximation.

Until this figure and its machine-readable data exist, no production emulator campaign is authorized.

## 3. Phase U0 — scope, solvers and priors

### U0-SCOPE-FREEZE

- freeze the variables `theta`, `z`, weak nuisances, abundance conventions and units;
- freeze model labels `U-M0` through `U-M6`;
- specify which outputs are primary in each stage;
- confirm the JCAP manuscript is non-blocking and out of scope.

### U0-PUBLIC-SOLVER-BASELINES

Establish at least three executable, pinned paths from:

```text
LINX
PRyMordial
PRIMAT
PArthENoPE
AlterBBN
```

At minimum, each accepted path must return `Y_p` and `D/H`, structured failures, runtime and source/config hashes. Four-abundance support is added when the selected path can provide it reproducibly.

### U0-RATE-PRIOR-R0

Register:

```text
d(p,gamma)3He
d(d,n)3He
d(d,p)t
```

For every rate record central curve, temperature grid, units, uncertainty representation, covariance status, forward/reverse mapping, solver IDs, source revision and checksum.

### U0-WEAK-PRIOR

Register neutron lifetime and weak normalization separately. Do not count the same weak uncertainty twice.

## 4. Phase U1 — direct Monte Carlo bands

### U1-MC-FIDUCIAL-1K

At a frozen standard-BBN point:

- draw 1,000 nuisance vectors from the registered prior;
- run the direct solver;
- preserve every failure and seed;
- compute abundance quantiles, covariance, skewness and correlations;
- measure cost and throughput.

### U1-MC-CONVERGENCE

Compare cumulative results at at least:

```text
N = 100, 300, 1,000
```

and, if needed:

```text
N = 3,000, 10,000.
```

Stop when the preregistered quantile/covariance tolerances are met. Do not run a larger sample solely because the original concept document mentioned `10^5`.

### U1-SCHRAMM-BANDS

Produce central, 68% and 95% bands over a baryon-density or equivalent standard-BBN slice. Validate at selected points with a second solver/rate compilation.

### U1-POSTHOC-SIGMA-AUDIT

Construct the best possible constant theoretical covariance from the fiducial sample and document exactly what information it discards.

## 5. Phase U2 — theta dependence and formal gate

### U2-COVARIANCE-SMOKE-16

At 16 frozen cosmological points, measure:

- abundance means and quantiles;
- `C_rate(theta)`;
- cross-abundance correlations;
- skew/tail diagnostics;
- finite-difference responses to the R0 rates and weak nuisances;
- solver/rate-library differences.

This is an engineering and effect-size smoke, not a publication claim.

### U2-FISHER64

Freeze 64 points before execution. Include standard region, observationally relevant region, degeneracy directions, boundaries and failure-critical points. Use symmetric finite differences at two step sizes and validated autodiff where available.

### U2-GATE-REPORT

Issue one decision:

- `G0`: bands effectively constant and inference changes below thresholds; stop production scaling;
- `G1`: modest theta dependence or posterior effect; authorize targeted labels only;
- `G2`: important nonlinearity, covariance drift, posterior shift or ranking change; authorize model/data expansion;
- `G3`: qualitative decision change or strong solver disagreement; authorize independent red team and high-impact route.

## 6. Phase U3 — learned models

Only after `G1+`:

### U3-FORWARD-EMU

Train a deterministic conditional baseline

```text
(theta, z, tau_n) -> y.
```

Start with a modest MLP/residual network. Record learning curves versus high-fidelity calls.

### U3-MARGINAL-DIST

Learn

```text
p(y | theta)
```

only when direct Monte Carlo shows that a distributional model is required. Compare Gaussian/heteroscedastic, mixture and flow baselines before adopting a complex architecture.

### U3-CALIBRATION

Validate:

- held-out point accuracy;
- conditional quantiles;
- 68%/95% coverage;
- abundance covariance;
- tail behavior;
- OOD and fallback;
- multiple seeds;
- direct-solver challenge points.

## 7. Phase U4 — cosmological inference

Compare, using identical data and priors:

```text
U-M0 central rates
U-M1 constant post-hoc C_th
U-M2 explicit/direct marginalization
U-M3 forward emulator plus explicit z marginalization
U-M4 learned p(y|theta)
```

Primary outputs:

- normalized posterior shifts;
- credible-interval ratios;
- posterior topology/mode changes;
- posterior predictive coverage;
- high-fidelity calls;
- wall time, CPU/GPU hours and monetary cost.

## 8. Optional later extensions

The following are conditional, not active assumptions:

- add `3He/H` and `7Li/H` core reactions;
- expand from R0 to 10–20 or full-network rates;
- introduce function-valued S-factor/rate modes;
- apply the framework to `Delta N_eff`, stiff expansion, reheating or SGWB;
- develop multi-fidelity active learning;
- pursue Nature Astronomy, Nature Computational Science or Nature Machine Intelligence.

Each requires a signed gate and a specific scientific or computational necessity.

## 9. Compute policy

- One available AutoDL worker is sufficient for U0–U2; the second worker is optional capacity.
- Solver generation is primarily CPU/FP64 work; GPU availability does not define scientific progress.
- Long jobs use heartbeat/checkpoint/resource lease.
- Report solver calls, CPU-core-hours, GPU-hours, wall time and cost separately.
- No Pilot-10k or larger production data set before `U2-GATE-REPORT`.

## 10. Immediate 14-day sequence

### Days 1–2

- reconcile the UQ-only plan;
- freeze R0 rate/weak schemas;
- select the first executable direct path and independent check;
- create the fixed standard-BBN point manifest.

### Days 3–5

- implement the nuisance adapter;
- run deterministic `z=0` and `z=±1` regression tests;
- run 100/300-draw shakedowns;
- fix units, mappings and failure handling.

### Days 6–8

- execute `U1-MC-FIDUCIAL-1K`;
- compute distribution and convergence diagnostics;
- produce the first theoretical-band data product.

### Days 9–10

- complete Schramm bands;
- compare direct bands with constant `C_th`;
- decide whether 3k/10k draws are necessary.

### Days 11–14

- freeze and run the 16-point covariance smoke;
- issue a provisional effect-size memo;
- prepare the 64-point manifest without unblinding production significance.

## 11. Definition of being unblocked

The project is scientifically moving when at least one of the following is true:

- direct nuisance draws are actively producing registered labels;
- convergence diagnostics are updating with sample count;
- a Schramm theoretical band has been generated from solver truth;
- `C_rate(theta)` is being measured at multiple points;
- a learned model is being calibrated against direct distributions;
- posterior treatments are being compared.

Creating additional governance documents, manuscript artifacts or unrelated solver audits does not by itself satisfy this definition.
