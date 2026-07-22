# NOVELTY_CLEARANCE_v1 — July 2026 UQ-only decision

Status: **DRAFT — CLAIMS NOT CLEARED; NATURE GATE CLOSED**  
Evidence review: [`FRONTIER_REVIEW_2026-07.md`](FRONTIER_REVIEW_2026-07.md)  
Competitor matrix: [`COMPETITOR_MATRIX_v1.md`](COMPETITOR_MATRIX_v1.md)  
Machine-readable registry: [`configs/literature/frontier_sources_2026-07.yaml`](../../configs/literature/frontier_sources_2026-07.yaml)  
Tasks: `P0-LIT-01`, `P0-WHY-NOT-01`, `UQ0-*`, `UQ1-*`, `UQ2-*`

## 1. Decision boundary

The active repository concerns BBN nuclear-reaction-rate uncertainty, abundance-distribution
prediction and nuisance marginalization. The separate JCAP stiff/SGWB manuscript is not a
project dependency and cannot be used to manufacture novelty for the UQ baseline.

This document records candidate deltas and stop rules. It is not permission to use “first”,
“unprecedented”, “complete”, “solver-independent”, “unbiased” or “exact” language.

## 2. What has already been done

The July 2026 review establishes that the following are existing baselines:

1. BBN Monte Carlo propagation of nuclear-rate uncertainty;
2. log-normal rate nuisance variables and low/median/high rate tables;
3. explicit rate marginalization with PRyMordial;
4. direct native Monte Carlo with modern PRIMAT;
5. fast differentiable BBN and joint CMB+BBN rate marginalization with LINX;
6. deterministic abundance emulation with BBNet;
7. standard-BBN local sensitivities for 63 rates and ranked error budgets;
8. Gaussian-process inference for the three leading deuterium reactions;
9. abundance–rate correlation and mutual-information studies;
10. general marginal SBI methods whose simulation requirements can be weakly dependent on nuisance dimension;
11. modern local and posterior-focused calibration methods for SBI.

Consequently, none of these components can carry the project by itself.

## 3. Candidate physics/statistics contribution

The smallest defensible UQ physics/statistics claim is:

> Current nuclear-rate probability information induces a joint abundance distribution whose
> covariance, tails or parameter dependence cannot always be represented by a fixed,
> independent, post-hoc theoretical error; quantifying that failure or validating its domain of
> adequacy changes a registered BBN inference or uncertainty statement.

Evidence must include:

- coherent rate-curve draws derived from a versioned probability model;
- actual-PDF versus scalar log-normal comparison, beginning with ETR25 R0 reactions;
- joint abundance quantiles, covariance and cross-element correlations;
- `C_rate(theta)` drift over a preregistered domain;
- `U-M1` versus direct `U-M2` posterior comparison;
- at least two rate compilations or solver/reference paths under matched physics;
- a variance/discrepancy decomposition that does not conflate engine, rate library and weak physics.

A null result is valid: the project may establish that a fixed `C_th` is accurate over a stated
domain. Such a result must be presented as a calibrated validity bound, not as a discovery.

## 4. Candidate computational contribution

A learned-model claim is available only if all of the following hold:

1. direct reference distributions and posteriors exist;
2. point accuracy, conditional quantiles, joint covariance and tails pass registered tests;
3. prior SBC and posterior SBC pass with multiple training seeds;
4. OOD and solver failures are explicit, with direct fallback;
5. training-label cost is included in the economics;
6. high-fidelity calls fall by at least `10x` or end-to-end wall time by at least `5x` at matched posterior fidelity;
7. the method is compared against simple conditional MLP/Gaussian/mixture baselines and TMNRE/AMNRE-style marginal ratio estimation.

Normalizing flows, GANs, diffusion models, Transformers and multi-fidelity learning are existing
method families. Selecting one is not an algorithmic contribution.

## 5. ETR25 changes the immediate project priority

ETR25 supplies statistically meaningful rate information for the R0 reactions and explicitly
distinguishes:

- low/median/high values from the percentiles of the **actual** rate probability density;
- a factor uncertainty based on a **log-normal approximation**.

The approximation need not be exact. Therefore the first potentially new audit is not another
central-rate network; it is:

```text
coherent ETR25/posterior rate curves
versus
scalar log-normal envelope
versus
solver-distributed legacy low/high representation
```

propagated to the joint abundance distribution and then, if warranted, to inference.

Independent random noise at each temperature point is physically invalid unless it is derived
from a registered functional posterior. A sampled nuclear-input realization must generate a
coherent rate curve across temperature.

## 6. Standard-BBN results that remain regression tests

The following are necessary but scientifically insufficient:

- central abundance agreement;
- a Schramm theoretical band at one fiducial point;
- identifying `d(p,gamma)3He`, `d(d,n)3He` and `d(d,p)t` as important;
- reproducing the 63-rate sensitivity atlas;
- reproducing a GP fit for the three R0 reactions;
- reproducing PRIMAT or PRyMordial Monte Carlo uncertainties;
- showing that an emulator is faster per forward call.

They validate the implementation and establish reference cost; they do not clear novelty.

## 7. Three principal rejection risks

| ID | Likely rejection | Current reason |
|---|---|---|
| `R1-DUPLICATION` | The work reproduces native PRIMAT/PRyMordial/LINX uncertainty propagation or the published sensitivity atlas. | Fixed-point MC, scalar nuisances, standard rankings and direct joint inference already exist. |
| `R2-UNNECESSARY-ML` | A learned model is unnecessary because direct modern tools already complete the registered workload. | No full matched workload, SBC campaign or end-to-end economics has yet demonstrated a bottleneck. |
| `R3-INVALID-PRIOR` | The reaction-rate prior is an unphysical collection of independent temperature-bin errors or copied solver envelopes. | Current R0 numerical priors and covariance are not yet frozen; ETR25 and posterior nuclear models must be ingested coherently. |
| `R4-MISCALIBRATION` | The learned distribution has good MSE but wrong tails, covariance or posterior coverage. | No direct distributional challenge set, posterior SBC or fallback result exists yet. |
| `R5-CONFOUNDING` | Differences called “solver uncertainty” actually arise from rate libraries, weak physics or networks. | The matched factor matrix is not yet executed. |

## 8. Experiments mapped to rejection risks

| Risk | Required experiment | Passing evidence | Failure action |
|---|---|---|---|
| `R1` | ETR25 PDF audit, native PRIMAT MC, PRyMordial marginalization, LINX q-runs, atlas slice | Project result measures a registered distribution/posterior object not already provided by the baseline | Reframe as reproduction; do not claim novelty |
| `R2` | direct workload and 1,000-SBC economics | `10x` call or `5x` wall-time advantage after training cost at matched fidelity | use direct stack and close speed-only claim |
| `R3` | coherent rate-curve draw validation and source checksum audit | sampled curves reproduce source quantiles/correlations and solver mappings | prohibit production labels |
| `R4` | joint abundance challenge, prior/posterior SBC, multiple seeds, OOD/fallback | frozen coverage and posterior-risk thresholds pass | reject learned model regardless of speed |
| `R5` | matched engine × rate × weak × network pairs | factor-specific residuals are identified and stable | narrow claims to the identifiable factor |

## 9. Method baseline set if UQ2 authorizes learning

The default comparison order is:

1. direct PRIMAT native Monte Carlo;
2. PRyMordial explicit marginalization;
3. LINX direct/differentiable rate-nuisance inference;
4. deterministic conditional MLP `f(theta,z)`;
5. heteroscedastic multivariate Gaussian and deep ensemble;
6. Gaussian mixture or calibrated quantile model;
7. TMNRE/AMNRE-style marginal ratio estimator;
8. neural likelihood or flow only if direct distribution diagnostics require it;
9. calibrated multi-fidelity method only if a useful approximate/high-fidelity pair is measured;
10. diffusion/Simformer-class model only for a demonstrated function-valued or arbitrary-conditional need.

## 10. Quantitative claim gates

### Distribution/physics gate

Proceed beyond direct characterization when at least one is observed and reproduced:

- covariance or key quantile drift beyond its frozen numerical/MC uncertainty;
- meaningful non-Gaussian tail or cross-abundance correlation missed by `U-M1`;
- a core posterior shift `>= 0.1 sigma`;
- a credible-interval change `>= 5%`;
- a posterior mode, topology or data-tension interpretation change;
- a rate-PDF-shape effect above the same registered inference-risk threshold.

### Method gate

A learned model enters scientific inference only when:

- every core median shift relative to direct inference is `< 0.1 sigma`;
- every core interval ratio lies in `[0.95, 1.05]`;
- no registered mode or decision boundary is lost;
- local and global coverage pass;
- failures and fallback satisfy the frozen limits;
- the measured economics exceed the minimum benefit threshold.

## 11. Stop rules

Stop production scaling when any of the following holds:

- 1,000 draws already meet the registered quantile/covariance precision and larger samples add no decision value;
- actual-PDF and scalar log-normal treatments differ below all null thresholds;
- `C_rate(theta)` is effectively constant over the registered domain;
- `U-M1` and `U-M2` agree below the posterior-risk thresholds;
- direct PRIMAT/LINX/PRyMordial completes the full registered workload within budget;
- the learned model fails calibration or fallback requirements.

Do not respond to a null result by changing the primary data, broadening priors, adding reactions,
activating non-standard cosmology or switching architecture solely to obtain significance.

## 12. Current clearance

- Fixed-point MC and Schramm bands: **authorized as reproduction/calibration**.
- ETR25 R0 ingestion and actual-PDF audit: **highest priority**.
- Sixteen-point covariance/quantile drift study: **authorized after R0 prior validation**.
- Sixty-four-point formal gate: **authorized after smoke and frozen manifest**.
- Conditional emulator training: **not yet authorized**.
- Function-valued rate modes: **not yet authorized**.
- Full-network production: **not yet authorized**.
- Non-standard cosmology and Nature-tier claims: **not yet authorized**.

## 13. Sign-off

Review prepared from primary-source searches and public artifacts; absence from the search is not
proof of nonexistence.

- A00 scientific lead: **pending**;
- A11 literature/competition: **pending**;
- A03 nuclear-data review: **pending**;
- A09 independent validation: **pending**.

Nature-tier Gate remains **CLOSED**.
