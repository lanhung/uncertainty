# Science critical path v3.1 — BBN nuclear-rate uncertainty only

> Effective date: 2026-07-23  
> Governing decisions: `ADR-0006-uncertainty-core-refocus.md`, `ADR-0007-frontier-literature-2026-07.md`  
> Scientific scope: `docs/science/UNCERTAINTY_SCOPE_v1.md`  
> Frontier review: `docs/literature/FRONTIER_REVIEW_2026-07.md`

## 1. Deliverable

The active project has one deliverable:

> A self-contained, calibrated and computationally audited treatment of BBN nuclear-reaction-rate uncertainty, from current nuclear probability information and direct solver perturbations to joint abundance distributions and cosmological posterior marginalization.

The separate JCAP stiff/SGWB manuscript is not part of this critical path.

## 2. First scientific figure and first potentially new figure

### 2.1 First calibration figure

The first required paper-quality calibration result is a solver-grounded theoretical-band figure showing, at frozen cosmological inputs:

- central abundance curves;
- Monte Carlo 68% and 95% bands from physical rate perturbations;
- convergence of those bands with nuisance sample count;
- cross-abundance correlations;
- comparison of direct Monte Carlo with a constant-`C_th` approximation.

This figure is necessary but not novel by itself; Monte Carlo BBN bands already exist.

### 2.2 First potentially new figure

The first figure that can support a new claim compares, over a frozen domain:

```text
actual/posterior nuclear-rate PDFs
vs scalar log-normal approximation
vs fixed post-hoc C_th
```

and reports the resulting joint abundance quantiles, covariance, tails and posterior risk. Until these data products exist, no production emulator campaign is authorized.

## 3. Phase P0 — frontier freeze

### P0-FRONTIER-2026-07

Freeze and sign:

- `FRONTIER_REVIEW_2026-07.md`;
- the updated competitor matrix and novelty clearance;
- `frontier_sources_2026-07.yaml`;
- the claim blacklist;
- the mandatory direct and SBI baseline set.

The review establishes that native PRIMAT Monte Carlo, PRyMordial marginalization, LINX rate nuisances, standard sensitivity rankings, GP deuterium rates and nuisance-marginal SBI must be reproduced or benchmarked rather than rediscovered.

## 4. Phase UQ0 — current nuclear PDFs, direct baselines and priors

### UQ0-SCOPE-FREEZE

- freeze variables `theta`, scalar `z`, original nuclear draw `u`, weak nuisances and abundance conventions;
- freeze model labels `U-M0` through `U-M6`;
- confirm that ETR25 actual-PDF versus log-normal comparison is part of R0;
- confirm that the JCAP manuscript remains out of scope.

### UQ0-PUBLIC-SOLVER-BASELINES

Pin and execute the primary three paths:

```text
PRIMAT
PRyMordial
LINX
```

PArthENoPE and AlterBBN are later precision/engineering checks. At minimum, each accepted path returns `Y_p` and `D/H`, structured failures, runtime and source/config hashes.

### UQ0-ETR25-R0-INGEST

For:

```text
d(p,gamma)3He       ETR25 Table 6
d(d,n)3He           ETR25 Table 7
d(d,p)t             ETR25 Table 8
```

capture:

- paper, Zenodo and repository identifiers;
- exact downloadable files, revisions and checksums;
- temperature grids and units;
- low/median/high actual percentiles;
- factor uncertainties and their log-normal interpretation;
- available original posterior or nuclear-input products;
- missing cross-reaction covariance.

### UQ0-RATE-PDF-AUDIT

For each R0 reaction:

- measure low/median/high asymmetry versus temperature;
- compare actual/posterior quantiles with the scalar log-normal approximation;
- identify the BBN-relevant temperature interval;
- validate coherent rate-curve draws;
- prohibit independent random noise at each temperature bin;
- record whether the scalar model is adequate or must remain a competing approximation.

### UQ0-R0-RATE-PRIOR

Freeze the accepted actual/posterior model and scalar baseline, including solver mappings, reverse-rate handling and missing-correlation stress tests.

### UQ0-WEAK-PRIOR

Register neutron lifetime and weak normalization separately. Do not count the same weak uncertainty twice.

### UQ0-NUISANCE-ADAPTER and PLUSMINUS regression

Implement:

```text
simulate(theta, rate_draw, tau_n, solver, network, precision) -> y, status, provenance
```

and validate:

- central values;
- scalar `z=+/-1`;
- coherent source-posterior curves;
- units and reverse mappings;
- deterministic seeds;
- structured failures.

### UQ0-NATIVE-UQ-REPRO

Before custom production, reproduce:

1. PRIMAT native `run_mc()` / `mc_uncertainty()`;
2. PRyMordial explicit rate marginalization;
3. LINX central and `nuclear_rates_q` perturbations;
4. one R0 sensitivity-atlas slice;
5. the structure of the 2026 GP deuterium prior.

These are calibration baselines, not novelty claims.

## 5. Phase UQ1 — direct abundance distributions

### UQ1-FIDUCIAL-MC-1K

At a frozen standard-BBN point:

- draw 1,000 coherent nuclear-rate realizations;
- preserve the source draw or nuisance vector, rate-curve hashes, seed, failure and runtime;
- compute abundance quantiles, covariance, skewness, tails and correlations;
- run at least one independent reference path.

### UQ1-MC-CONVERGENCE

Compare cumulative results at:

```text
N = 100, 300, 1,000
```

and, only when required:

```text
N = 3,000, 10,000.
```

Stop when preregistered quantile/covariance/tail tolerances are met. Do not run `10^5` solely because the original concept note mentioned it.

### UQ1-RATE-PDF-PROPAGATION

Compare three representations under matched central physics:

1. actual or original-posterior rate draws;
2. scalar log-normal envelope;
3. solver-distributed legacy low/high representation.

Report the difference in the joint abundance distribution, not only one-dimensional standard deviations.

### UQ1-SCHRAMM-BANDS

Produce central, 68% and 95% bands over a baryon-density or equivalent standard-BBN slice. Validate selected points with a second solver/rate compilation. Label this as a reproduction/calibration result unless a new distributional effect is demonstrated.

### UQ1-POSTHOC-SIGMA-AUDIT

Construct the best possible constant theoretical covariance from the fiducial sample and document exactly what it discards:

- parameter dependence;
- cross-abundance correlation;
- skewness and tails;
- rate-PDF model dependence;
- solver/rate-library discreteness.

## 6. Phase UQ2 — parameter dependence, novelty and production gate

### UQ2-COVARIANCE-SMOKE-16

At 16 frozen cosmological points, measure:

- abundance means and quantiles;
- `C_rate(theta)`;
- cross-abundance correlations;
- skew/tail diagnostics;
- actual-PDF versus scalar-lognormal differences;
- finite-difference responses to R0 rates and weak nuisances;
- matched solver/rate-library differences.

This is an effect-size smoke, not a publication claim.

### UQ2-FISHER64

Freeze 64 points before execution. Include the standard region, observationally relevant region, degeneracy directions, boundaries and failure-critical points. Use symmetric finite differences at two step sizes and validated autodiff where available.

### UQ2-DIRECT-ECONOMICS

Measure complete registered workloads for:

- PRIMAT native MC;
- PRyMordial explicit marginalization;
- LINX direct/differentiable inference;
- repeated posterior analyses;
- 1,000 SBC replicates.

Count labels, failures, CPU-core-hours, GPU-hours, wall time and monetary cost.

### UQ2-METHOD-BASELINE-MANIFEST

Before authorizing learned models, freeze the comparison set:

```text
deterministic conditional MLP
heteroscedastic multivariate Gaussian
ensemble
mixture or calibrated quantile model
TMNRE / AMNRE-style marginal ratio estimation
neural likelihood or flow only if required
posterior SBC and local calibration
```

### UQ2-GATE-REPORT

Issue one decision covering both physical novelty and method necessity:

- `G0`: distributions effectively constant/near-Gaussian, `U-M1` adequate and direct tools affordable; stop scaling;
- `G1`: modest parameter/PDF dependence or repeated-workload benefit; authorize targeted labels and simple baselines only;
- `G2`: important covariance/tail/PDF drift, posterior shift or direct cost; authorize broader rates and learned distributions;
- `G3`: qualitative inference change or strong matched solver disagreement; authorize independent red team and high-impact route.

## 7. Phase UQ3 — learned models, only after G1+

### UQ3-FORWARD-EMU

Train a modest conditional baseline:

```text
(theta, z or u, tau_n) -> y.
```

Record learning curves versus high-fidelity calls.

### UQ3-MARGINAL-DIST / RATIO

Depending on the direct distribution and target:

- use a multivariate Gaussian or mixture when sufficient;
- learn `p(y|theta)` only when distribution diagnostics require it;
- include TMNRE/AMNRE when the main target is a low-dimensional posterior with high-dimensional nuisances;
- use flows/diffusion/Simformer-class models only for demonstrated complexity.

### UQ3-CALIBRATION

Validate:

- held-out point accuracy;
- conditional quantiles and covariance;
- 68%/95% coverage;
- tails;
- prior and posterior SBC;
- multiple seeds/ensembles;
- OOD and direct fallback;
- direct-solver challenge points.

## 8. Phase UQ4 — cosmological inference

Compare, using identical data and priors:

```text
U-M0 central rates
U-M1 constant post-hoc C_th
U-M2 explicit/direct marginalization
U-M3 forward emulator plus explicit nuisance marginalization
U-M4 learned p(y|theta) or authorized marginal ratio model
```

Primary outputs:

- normalized posterior shifts;
- credible-interval ratios;
- posterior topology/mode changes;
- posterior predictive and SBC coverage;
- rate/weak/solver variance decomposition;
- high-fidelity calls and full cost.

## 9. Optional later extensions

The following are conditional, not active assumptions:

- add `3He/H` and `Li7/H` core reactions;
- expand from R0 to 10–20 or full-network rates;
- introduce function-valued S-factor/rate modes beyond already published deuterium GP baselines;
- apply the framework to `Delta N_eff`, stiff expansion, reheating or SGWB;
- develop nuisance-safe multi-fidelity active learning;
- pursue Nature Astronomy, Nature Computational Science or Nature Machine Intelligence.

Each requires a signed gate and a specific scientific or computational necessity.

## 10. Compute policy

- One available AutoDL worker is sufficient for P0–UQ2; the second worker is optional capacity.
- Solver generation is primarily CPU/FP64 work; GPU availability does not define scientific progress.
- Long jobs use heartbeat/checkpoint/resource lease.
- Report solver calls, CPU-core-hours, GPU-hours, wall time and cost separately.
- No Pilot-10k or larger production data set before `UQ2-GATE-REPORT`.

## 11. Immediate 14-day sequence

### Days 1–2

- reconcile plan version 4;
- freeze and sign the July frontier artifacts;
- capture ETR25 R0 files and exact provenance;
- pin PRIMAT, PRyMordial and LINX;
- create the frozen standard-BBN point manifest.

### Days 3–5

- audit actual/posterior versus log-normal R0 rate representations;
- reproduce PRIMAT native MC, PRyMordial and LINX uncertainty paths;
- implement the common nuisance adapter;
- run central, `z=+/-1` and coherent-curve regression tests.

### Days 6–8

- execute `UQ1-FIDUCIAL-MC-1K`;
- compute convergence, joint covariance and tails;
- compare rate-PDF representations;
- produce the first theoretical-band data product.

### Days 9–10

- complete Schramm bands;
- compare direct joint distributions with constant `C_th`;
- decide whether 3k/10k draws are necessary.

### Days 11–14

- freeze and run the 16-point covariance/PDF smoke;
- issue a provisional effect-size and duplication-risk memo;
- prepare the 64-point and method-baseline manifests.

## 12. Definition of being unblocked

The project is scientifically moving when at least one is true:

- current nuclear probability products are being ingested and validated;
- direct coherent-rate draws are producing registered labels;
- convergence diagnostics update with sample count;
- actual-PDF and scalar-lognormal abundance distributions are being compared;
- a Schramm theoretical band exists from solver truth;
- `C_rate(theta)` is measured at multiple points;
- posterior treatments are compared;
- an authorized learned model is calibrated against direct distributions.

Creating additional governance documents, manuscript artifacts, generic model architectures or unrelated solver audits does not by itself satisfy this definition.
