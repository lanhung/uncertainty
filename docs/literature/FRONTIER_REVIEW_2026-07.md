# Frontier review — BBN nuclear-rate uncertainty and simulation-based inference

> Review date: **2026-07-23**  
> Scope: BBN thermonuclear-rate uncertainty, abundance-distribution prediction, cosmological marginalization, surrogate modeling and simulation-based inference  
> Status: **evidence review complete; scientific claims remain gated by execution**  
> Governing scope: `docs/science/UNCERTAINTY_SCOPE_v1.md`

## 1. Executive verdict

A substantial fraction of the original project concept already exists in public work, but the complete project is not redundant.

The following components are **already established** and must be treated as baselines rather than novelty claims:

1. direct Monte Carlo propagation of BBN nuclear-rate uncertainty;
2. log-normal scalar rate nuisance parameters;
3. explicit nuclear-rate marginalization in standard BBN and in joint CMB+BBN inference;
4. deterministic neural emulation of BBN abundances;
5. differentiable BBN and gradient-compatible joint inference;
6. standard-BBN sensitivity rankings for dozens of rates;
7. Gaussian-process inference for the three leading deuterium-burning reactions;
8. general SBI methods that marginalize high-dimensional nuisance parameters;
9. conformal, quantile and simulation-based calibration methods for learned posteriors.

The smallest still-defensible project contribution is therefore not “put reaction rates into a neural network.” It is the tested intersection of:

- modern, provenance-pinned nuclear-rate probability information;
- coherent rate-curve sampling rather than independent temperature-bin noise;
- the full joint abundance distribution `p(y | theta)`, including cross-abundance correlations and tails;
- a quantitative map of where a fixed post-hoc `C_th` approximation fails or succeeds;
- matched solver/rate-library/weak-physics comparisons;
- calibrated amortized marginalization with direct-solver posterior recovery and fallback;
- measured end-to-end economics for repeated inference, SBC and robustness studies.

During this review I did **not** find a published BBN study that simultaneously provides all of the following in one audited pipeline:

1. posterior- or Monte-Carlo-derived rate-curve priors from current nuclear data;
2. a calibrated conditional joint abundance distribution over a registered cosmological domain;
3. an explicit `constant C_th` versus direct marginalization failure map;
4. matched multi-solver factorization;
5. direct posterior recovery, coverage and OOD/fallback tests;
6. a measured simulation-budget comparison against modern nuisance-marginal SBI baselines.

This is a search-based assessment, not a proof that no unpublished or unindexed work exists. Monthly literature refreshes remain mandatory.

## 2. The current frontier in BBN software and inference

### 2.1 PRIMAT is now a direct Monte Carlo baseline, not only a precision reference

The public Python/C PRIMAT line now exposes direct log-normal rate variations and Monte Carlo propagation. At the review date:

- the repository `master` declares version `0.3.2`;
- the latest PyPI release visible in the audit is `0.3.1` from 2026-07-02;
- `p_<reaction>` parameters implement median-times-lognormal perturbations;
- `run_mc()` / `mc_uncertainty()` return raw per-sample abundance values;
- the CLI supports `--mc`, seeds and parallel workers;
- the small network, PArthENoPE-rate variant and large network are directly selectable.

**Project consequence:** `UQ1-FIDUCIAL-MC-1K` must first reproduce a native PRIMAT Monte Carlo result. Building a new generic Monte Carlo driver before reproducing this capability would be unnecessary duplication.

Primary resources:

- <https://github.com/CyrilPitrou/primat>
- <https://pypi.org/project/primat/>

### 2.2 PRyMordial already performs explicit rate marginalization

PRyMordial is a public Python BBN package designed for Standard Model and beyond-Standard-Model studies. It supports different rate philosophies, including NACRE-II-like and PRIMAT-like choices, and was explicitly designed to interface with Monte Carlo samplers.

Schöneberg's 2024 BBN baryon-abundance update used PRyMordial to marginalize log-normally distributed rate uncertainties and directly contrasted this treatment with the approximate final-abundance theoretical error used in PArthENoPE-based analyses. The paper shows that omitting rate marginalization dramatically shrinks the inferred uncertainty.

**Project consequence:** `U-M1` versus `U-M2` in ordinary standard BBN is not a first result. The project must add a domain-dependent failure map, joint abundance structure, modern rate PDFs, stronger calibration or a decision-relevant posterior result.

Primary resources:

- PRyMordial: arXiv:2307.07061
- Schöneberg update: arXiv:2401.15054
- <https://github.com/vallima/PRyMordial>

### 2.3 LINX already supplies fast differentiable rate-nuisance inference

LINX is a public JAX BBN code built for speed, differentiability and extensibility. Its public workflows include BBN uncertainty propagation and multiple reaction networks. A joint CMB+BBN analysis using LINX already marginalized Planck nuisance parameters and nuclear rates and reported constraints for three reaction networks.

**Project consequence:** neither scalar `q_i` inputs nor joint BBN+CMB rate marginalization are novel. LINX is a mandatory direct/differentiable baseline for posterior economics and gradient checks.

Primary resources:

- LINX: arXiv:2408.14538
- joint CMB+BBN analysis: arXiv:2408.14531, version 2 dated 2025-11-27
- <https://github.com/cgiovanetti/LINX>

### 2.4 ABCMB removes another part of the “direct inference is impossible” argument

ABCMB is a Python+JAX differentiable CMB code. Version `0.3.1` was released on PyPI on 2026-06-02 and includes an `ABCMB_with_LINX` example.

**Project consequence:** before claiming that an emulator is necessary for cosmological posterior inference, the project must benchmark the actual registered workload against LINX alone and ABCMB+LINX. Standard-point speed or a generic statement about ODE cost is insufficient.

Primary resources:

- arXiv:2602.15104
- <https://pypi.org/project/ABCMB/0.3.1/>

### 2.5 PArthENoPE and AlterBBN remain useful, but play different roles

PArthENoPE 3.0 is a mature precision code with updated deuterium-burning rates. AlterBBN is valuable for alternative cosmologies and engineering cross-checks, but it is not a substitute for a precision nuclear reference under matched inputs.

**Project consequence:** do not label an unmatched PArthENoPE-versus-AlterBBN difference as “solver uncertainty.” Separate numerical engine, rate compilation, weak physics, network and extension implementation.

## 3. The current frontier in nuclear-rate probability information

### 3.1 ETR25 is the most important new input for this project

The 2025 Evaluation of Experimental Thermonuclear Reaction Rates (ETR25), published in 2026, evaluates 78 charged-particle rates over 1 MK to 10 GK. It supplies:

- low, median and high rates as the 16th, 50th and 84th percentiles of the actual rate probability density;
- factor uncertainties from a log-normal approximation;
- RatesMC inputs and outputs;
- 50,000-sample Monte Carlo evaluations for most rates;
- public code and data through GitHub and Zenodo.

ETR25 contains all three Stage-R0 reactions:

- Table 6: `D(p,gamma)3He`;
- Table 7: `D(d,n)3He`;
- Table 8: `D(d,p)3H`.

It also contains several natural Stage-R1 reactions, including `3He(alpha,gamma)7Be` and `7Be(n,p)7Li`.

The critical statistical warning is that the tabulated low/median/high values come from the **actual** Monte Carlo rate distribution, while the factor uncertainty assumes a log-normal approximation. ETR25 explicitly notes that the approximation can fail when the actual rate density is not log-normal.

**Project consequences:**

1. ETR25 becomes the primary candidate experimental-rate prior source for R0.
2. The project must audit actual percentiles/PDFs against the scalar log-normal approximation.
3. Independent random draws at every temperature bin are prohibited. A single nuclear-input draw induces a coherent rate curve over temperature.
4. Solver-distributed low/high tables are transport formats, not automatically authoritative nuclear posteriors.
5. Cross-reaction correlations absent from ETR25 must be recorded as unmodeled, not assumed zero without a registered stress test.

Primary resources:

- ETR25 paper: arXiv:2601.20059; ApJS 283, 17; DOI 10.3847/1538-4365/ae2bdc
- data: <https://zenodo.org/records/17610211>
- RatesMC: <https://github.com/rlongland/RatesMC>
- evaluation inputs: <https://github.com/TUNL-Reaction-Rates-Group/2025-rates-evaluation>

### 3.2 Standard sensitivity ranking is no longer an open question

The 2026 BBN sensitivity atlas evaluates 14 particle/cosmological parameters and 63 thermonuclear rates using two rate compilations and two weak-rate normalizations, and ranks contributions to the theoretical error budget. Numerical results and figures are public.

**Project consequence:** reproducing the standard ranking of the three deuterium reactions is a regression test. A new result requires distributional structure, posterior consequences, rate-PDF shape effects, matched solver decomposition, or sensitivity reordering in a separately authorized application.

Primary resource: arXiv:2603.22414 and <https://github.com/Anne-KatherineBurns/bbn-sensitivity-atlas>.

Reproducibility audit (2026-07-23): the public result repository is frozen at
`d3ea1838d9450673698f07b7c6b8971efb87d0fd` under CC0-1.0. It contains the
response plots and PDF summary/budget tables, but not the generating scripts,
and the paper does not identify the PRyMordial commit used. The project's
independent R0-slice protocol therefore treats comparison with the published
table as a numerical calibration with an explicit version-mismatch risk, not
as a bitwise rerun.

### 3.3 Function-valued inference for the three deuterium reactions already exists

The 2026 data-driven D/H study uses Gaussian-process regression on the experimental data for `d(d,n)3He`, `d(d,p)t` and `d(p,gamma)3He`. It validates the GP uncertainty, finds that low-order polynomial fits can systematically overpredict D/H, and identifies the 0.1–0.6 MeV region as important for improved `dd` measurements.

**Project consequence:** “use a GP for the three head reactions” is not a novelty claim. A function-valued extension must compare posterior-derived shape modes with the scalar approximation and demonstrate an effect on joint abundance distributions, posterior coverage or a registered physics decision.

Primary resource: arXiv:2604.16600.

Reproducibility audit (2026-07-23): arXiv v1 source archive
`1123d5327c48fd57c55626cbb804854b5c3832443f1f49dd3c04626ae97cd04d`
fixes the public method description. The paper states that analysis code will
be released with later cosmological work; fitted hyperparameters, posterior
draws, the exact experimental-data bundle and random seeds are not currently
public. The prior structure and published abundance summaries can therefore
be captured exactly, but ADR-0008 forbids counting this as an independently
rerun abundance distribution until those inputs are released.

### 3.4 Reaction posteriors can require hierarchical nuclear models

Hierarchical Bayesian evaluations already exist for individual BBN reactions, including `7Be(n,p)7Li` and `D(p,gamma)3He`. They model normalization systematics and other experimental uncertainties rather than treating a low/high envelope as a complete posterior.

**Project consequence:** Stage R1/R2 must prefer original posterior products or reproducible nuclear-input models when available. A single solver flag must not be presented as the full nuclear epistemic uncertainty.

Representative resources:

- `7Be(n,p)7Li`: arXiv:1912.06210
- `D(p,gamma)3He`: arXiv:2109.00049
- nuclear-rate/lithium Monte Carlo and mutual information: arXiv:2008.12200

## 4. Observational precision raises the value of correct theoretical covariance

The LBT Yp Project reports `Y_p = 0.2458 +/- 0.0013`, a 0.5% measurement. A companion cosmological analysis combines it with deuterium and CMB data. A 2026 CMB+BAO+BBN analysis reports `N_eff = 2.990 +/- 0.070`. The 2024 Kislitsyn deuterium compilation reports `(D/H)_p = (2.533 +/- 0.024) x 10^-5` and a moderate Standard-Model tension.

**Project consequence:** theoretical covariance, abundance correlations and rate-library differences are no longer secondary bookkeeping. However, observational precision alone does not establish project novelty; the project must measure the posterior impact under frozen data choices.

Primary resources:

- LBT Yp Project IV: arXiv:2601.22238
- LBT Yp Project V: arXiv:2601.22239
- 2% `N_eff`: arXiv:2603.13226
- updated D/H: arXiv:2401.12797

## 5. The current frontier in nuisance-aware SBI

### 5.1 TMNRE and AMNRE are mandatory baselines

Truncated Marginal Neural Ratio Estimation (TMNRE) was designed for high-dimensional cosmological inference and reports that the required simulation count can be effectively independent of nuisance dimension. Arbitrary Marginal Neural Ratio Estimation (AMNRE) amortizes inference over arbitrary parameter subsets without numerical marginalization.

**Project consequence:** a conditional flow or GAN is not the only, or automatically the best, strategy. If the final target is a posterior over low-dimensional cosmological parameters with rates marginalized out, TMNRE/AMNRE-style ratio estimation must be included in the method baseline set.

Primary resources:

- TMNRE: arXiv:2111.08030; JCAP 09 (2022) 004
- AMNRE: arXiv:2110.00449

### 5.2 Nuisance-aware active learning has a known failure mode

Bayesian active learning with nuisance parameters can suffer “negative interference”: a budget focused only on target parameters can bias the target estimate because the nuisance structure remains poorly learned.

**Project consequence:** active acquisition must balance posterior relevance with nuisance calibration. Pure posterior-focused refinement is not automatically safe.

Primary resource: Sloman et al., UAI 2024, PMLR 244.

### 5.3 Calibration now has stronger tools than global prior SBC alone

Relevant current methods include:

- posterior SBC, which tests inference conditional on the observed-data neighborhood and includes differential-equation and amortized-inference examples;
- CP4SBI, which conformally calibrates credible sets with local finite-sample coverage guarantees;
- calibrated neural quantile estimation, which trains on many approximate simulations and calibrates with a smaller high-fidelity set;
- deep-ensemble diagnostics for training uncertainty and misspecification;
- residual neural likelihood estimation, which explicitly studies retraining noise and ensemble combinations.

**Project consequence:** validation must include prior SBC, posterior-focused SBC, multiple training seeds and local calibration diagnostics. A single held-out MSE or one nominal coverage number is inadequate.

Primary resources:

- posterior SBC: arXiv:2502.03279
- CP4SBI: arXiv:2508.17077
- calibrated neural quantile estimation: PRL 136, 161001 (2026)
- residual neural likelihood estimation: PRD 113, 124064 (2026)
- SBI deep ensembles: arXiv:2507.13495

### 5.4 Multi-fidelity learning is a baseline family, not a novelty by itself

Calibrated neural quantile estimation and multi-fidelity active-learning work show how approximate and high-fidelity simulators can be combined. Simformer and related all-in-one SBI models can handle function-valued parameters and arbitrary conditionals.

**Project consequence:** using a cheap solver plus a precise solver, or using a Transformer/diffusion model, is not sufficient. The contribution must be demonstrated through calibration, posterior fidelity, explicit failures and an end-to-end cost advantage.

## 6. Claim blacklist after the 2026-07 review

The project must not claim any of the following as new:

- the first BBN Monte Carlo propagation of nuclear-rate uncertainty;
- the first log-normal rate nuisance model;
- the first explicit rate marginalization in standard BBN;
- the first joint CMB+BBN inference with nuclear-rate nuisance parameters;
- the first differentiable BBN solver;
- the first BBN neural emulator;
- the first identification of the three dominant deuterium reactions;
- the first standard-BBN 60-plus-rate sensitivity atlas;
- the first GP treatment of the three deuterium S factors;
- the first use of a normalizing flow, ratio estimator, diffusion model or Transformer for high-dimensional nuisance marginalization in science;
- the first Monte Carlo abundance band or Schramm theoretical band;
- a general claim that direct BBN inference is computationally impossible.

## 7. Updated candidate contribution

### 7.1 Physics/statistics candidate

A defensible physics/statistics result would establish one or more of the following:

1. the actual ETR25/posterior rate distributions produce abundance tails or correlations missed by scalar log-normal approximations;
2. `C_rate(theta)` changes enough across the registered domain that a fixed `C_th` biases a posterior, interval or tension statement beyond the frozen null threshold;
3. a matched rate-library/weak/solver analysis identifies which layer dominates a precision-BBN conclusion;
4. a low-dimensional active subspace controls posterior-relevant abundance uncertainty, but differs from ordinary single-output sensitivity ranking;
5. the complete treatment changes a registered cosmological decision after independent direct validation.

### 7.2 Computational candidate

A defensible computational result would show that a calibrated learned treatment:

- matches direct `p(y | theta)` quantiles, covariance and tails;
- recovers direct posteriors within the registered risk budget;
- passes prior and posterior SBC plus OOD/fallback tests;
- reduces high-fidelity calls by at least `10x` or end-to-end wall time by at least `5x` after training cost is included;
- remains competitive with PRIMAT native MC, PRyMordial explicit marginalization, LINX direct inference and TMNRE/AMNRE baselines.

## 8. Revised implementation priorities

### Priority 0 — ingest current nuclear probability information

- capture ETR25 paper, Zenodo record, RatesMC revision and input checksums;
- regenerate or ingest coherent sampled rate curves for the three R0 reactions;
- compare actual percentiles/PDFs with the log-normal approximation in the BBN temperature window;
- document absent cross-reaction covariance.

### Priority 1 — reproduce, do not reinvent, direct baselines

- PRIMAT native `run_mc()` at the frozen standard point;
- PRyMordial explicit marginalization check;
- LINX `nuclear_rates_q` central and perturbed runs;
- one matched central-value and quantile comparison.

### Priority 2 — measure the first potentially new object

- joint `p(Y_p, D/H | theta)` rather than independent error bars;
- 16-point covariance, quantile, skewness and tail drift;
- constant-`C_th` approximation error;
- rate-PDF-shape versus scalar-lognormal difference.

### Priority 3 — formal posterior and method gate

- 64-point registered response set;
- direct `U-M1` versus `U-M2` posterior comparison;
- workload economics;
- decide whether `U-M3/U-M4` is scientifically and computationally necessary.

## 9. Method baseline hierarchy after the review

If the Gate authorizes learned models, compare in this order:

1. direct PRIMAT/PRyMordial/LINX reference;
2. deterministic conditional MLP `f(theta,z)`;
3. heteroscedastic multivariate Gaussian and ensemble;
4. Gaussian mixture or quantile-regression model;
5. TMNRE/AMNRE-style marginal ratio estimator for target posteriors;
6. neural likelihood or flow only if distribution diagnostics demand it;
7. calibrated multi-fidelity method if a useful approximate/high-fidelity solver pair exists;
8. diffusion/Simformer-class model only when function-valued inputs or arbitrary conditionals justify the extra complexity.

## 10. Stop rules

Stop or narrow the principal claim when:

- ETR25 actual PDFs and the scalar log-normal model yield indistinguishable abundance/posterior results below the registered null thresholds;
- `C_rate(theta)` is effectively constant over the registered domain;
- `U-M1` and `U-M2` agree within `0.1 sigma`, 5% interval width and no-topology-change thresholds;
- direct PRIMAT/LINX/PRyMordial completes the registered inference and calibration workload within the accepted budget;
- a learned model fails local coverage, posterior recovery or explicit-failure requirements.

A null result can still be publishable as a calibrated validation of the conventional approximation, but it does not support a Nature-tier or new-method claim.

## 11. Immediate repository actions authorized by this review

1. make ETR25 ingestion and log-normal-vs-actual-PDF auditing explicit UQ0 tasks;
2. mark fixed-point MC bands as a reproduction/calibration milestone, not a novelty claim;
3. update the competitor matrix and novelty clearance for the UQ-only scope;
4. require TMNRE/AMNRE and modern calibration methods in any post-Gate method comparison;
5. retain PRIMAT, PRyMordial and LINX as the primary three direct baselines;
6. keep full-network, function-valued, non-standard and Nature-tier work conditional on measured evidence.

## 12. Search limitations

The review used arXiv, primary journal pages, official repositories, PyPI and official data archives. Searches included combinations of BBN, nuclear-rate uncertainty, Monte Carlo, marginalization, covariance, emulator, normalizing flow, SBI and nuisance parameters. Absence from these searches is not proof of nonexistence. Conference proceedings, private code, papers under different terminology and very recent unindexed preprints may be missed.
