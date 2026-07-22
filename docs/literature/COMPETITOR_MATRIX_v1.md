# COMPETITOR_MATRIX_v1 — BBN nuclear-rate UQ frontier

Status: **July 2026 evidence inventory complete; claims not cleared**  
Review date: **2026-07-23 UTC**  
Task: `P0-LIT-01` / `P0-WHY-NOT-01`  
Detailed review: [`FRONTIER_REVIEW_2026-07.md`](FRONTIER_REVIEW_2026-07.md)  
Machine-readable sources: [`configs/literature/frontier_sources_2026-07.yaml`](../../configs/literature/frontier_sources_2026-07.yaml)

This matrix records the strongest public baselines found for the active repository scope:
thermonuclear-rate uncertainty propagated through BBN ODEs into abundance distributions
and cosmological inference. “Reproducible” means that public artifacts were located; it is
not a scientific endorsement. Versions and dates must be refreshed monthly.

## 1. Direct BBN software and inference baselines

| Object | Public state at review | Already solves | Nuclear-rate uncertainty | Differentiable / joint inference | What this project must add |
|---|---|---|---|---|---|
| **PRIMAT Python/C** | repository `master` declares `0.3.2`; PyPI `0.3.1` dated 2026-07-02; GPL-3.0-or-later | precision BBN with fast C backend, Python fallback, multiple networks and raw abundance outputs | native `p_<reaction>` log-normal perturbations; `run_mc()` / `mc_uncertainty()`; raw per-draw abundance values and parallel workers | not JAX AD; can be embedded in external inference | reproduce native MC before writing a new MC engine; compare rate-PDF choices, joint abundance structure, `C_th` failure map and calibrated amortization |
| **PRyMordial** | arXiv `2307.07061`; public GPL code | standard and beyond-SM BBN with first-principles thermodynamics | explicit log-normal marginalization; PRIMAT-like and NACRE-II-like choices | external samplers; not a full JAX-AD stack | matched distribution/posterior comparison using current rate PDFs, explicit abundance covariance and stronger calibration |
| **Schöneberg 2024** | arXiv `2401.15054` | current BBN baryon-abundance analysis | directly contrasts PArthENoPE-style post-hoc abundance error with PRyMordial rate marginalization | BBN likelihood inference | blocks any claim that standard-BBN `U-M1` versus `U-M2` is new; project needs a domain-dependent failure map or new precision conclusion |
| **LINX** | arXiv `2408.14538`; active public MIT repository | fast, differentiable and extensible JAX BBN | scalar `nuclear_rates_q`; multiple network/rate choices | yes; gradient-based inference | mandatory direct/differentiable baseline; add actual rate-PDF audit, joint abundance calibration, matched solver factors and measured economics |
| **LINX joint CMB+BBN** | arXiv `2408.14531`, v2 dated 2025-11-27 | joint CMB+BBN likelihood | marginalizes nuclear rates for three networks together with Planck nuisances | yes | blocks “first joint CMB+BBN rate marginalization”; compare only after reproducing its registered baseline |
| **ABCMB + LINX** | ABCMB PyPI `0.3.1`, 2026-06-02; MIT | differentiable CMB spectra with a bundled LINX example | inherited from LINX | yes | benchmark the actual registered workload before claiming that direct inference is infeasible |
| **PArthENoPE 3.0** | official versioned distribution; GPLv3 | mature precision Fortran BBN | rate variations and established MC workflows | no | precision cross-check, matched rate/weak inputs and structured failure interface |
| **AlterBBN** | public v2 C code; GPLv3 | rapid BBN and alternative cosmologies | ERR bounds / MC-style options | no | engineering or non-standard-cosmology cross-check; not an independent precision nuclear truth by itself |
| **BBNet** | arXiv `2512.15266`; public deterministic emulator lineage | fast PArthENoPE/AlterBBN abundance emulation in extended cosmology | public baseline uses central-rate labels | embeddable, not differentiable solver truth | calibrated distributional UQ, complete provenance, posterior recovery and a demonstrated need beyond direct modern codes |

## 2. Nuclear-rate probability and sensitivity baselines

| Object | Public state | Already solves | Critical implication for this project |
|---|---|---|---|
| **ETR25** | ApJS 283, 17 (2026), arXiv `2601.20059`; Zenodo DOI `10.5281/zenodo.17610211`; RatesMC and evaluation inputs public | 78 evaluated experimental rates from 1 MK–10 GK; actual 16/50/84 percentile rates; factor uncertainty from a log-normal approximation; usually 50,000 samples for non-Bayesian rates | primary candidate R0 prior source; ingest coherent sampled rate curves, compare actual PDFs against the log-normal approximation and record missing cross-reaction covariance |
| **2026 BBN sensitivity atlas** | arXiv `2603.22414`; Physics Reports 1194, 1–40; public numerical outputs | 14 physics/cosmology parameters, 63 rates, two rate compilations and two weak normalizations; local sensitivities and ranked linear uncertainty budgets | standard ranking is a regression test; atlas neglects off-diagonal covariance in its reported linear budget, leaving joint distribution/correlation work relevant |
| **Data-driven D/H GP** | arXiv `2604.16600` | GP inference from experimental data for the three dominant deuterium reactions; validated uncertainty; identifies bias in low-order polynomial fits | “use a GP for the three reactions” is not new; compare posterior-derived rate-shape modes against scalar/log-normal approximations and propagate to joint inference |
| **Hierarchical `7Be(n,p)7Li` rate** | arXiv `1912.06210` | hierarchical Bayesian R-matrix posterior with normalization systematics | R1 must prefer original posterior products or reproducible nuclear models when available |
| **Bayesian `D(p,gamma)3He` evaluations** | representative arXiv `2109.00049` | hierarchical treatment of nuclear data and normalization uncertainty | a solver low/high flag is not automatically the complete nuclear posterior |
| **Iliadis–Coc 2020** | arXiv `2008.12200` | BBN MC, abundance–rate mutual information and genetic search for a lithium nuclear solution | abundance–rate correlations and MC are long-established; simple sensitivity/MI plots are not novelty |

## 3. Nuisance-aware SBI and calibration baselines

| Method | Public source | Already solves | Required project response |
|---|---|---|---|
| **TMNRE** | arXiv `2111.08030`, JCAP 09 (2022) 004 | marginal neural ratio estimation for cosmology; simulator count reported effectively independent of nuisance dimension | mandatory post-Gate posterior baseline when targets are low-dimensional and rates are nuisance variables |
| **AMNRE** | arXiv `2110.00449` | amortized arbitrary parameter-subset marginals without numerical integration | include when comparing learned marginal posterior strategies |
| **Bayesian active learning with nuisances** | UAI 2024, PMLR 244 | identifies negative interference when target-focused acquisition underlearns nuisances | acquisition must allocate budget to nuisance calibration, not only posterior concentration |
| **Posterior SBC** | arXiv `2502.03279` | calibration checking conditional on the observed-data neighborhood; includes ODE and amortized examples | require both prior SBC and posterior-focused SBC |
| **CP4SBI** | arXiv `2508.17077` | local conformal calibration with finite-sample local coverage guarantees | candidate local-coverage baseline if learned posteriors are used |
| **Calibrated neural quantiles** | PRL 136, 161001 (2026) | many approximate simulations plus a smaller high-fidelity calibration set | mandatory multi-fidelity comparison if cheap and precise BBN paths are combined |
| **Residual neural likelihood / deep ensembles** | PRD 113, 124064 (2026) and arXiv `2507.13495` | exposes training-seed and model-misspecification uncertainty | require multiple seeds, ensembles and training-noise reporting |
| **Simformer-class models** | ICML 2024 | arbitrary conditionals and function-valued parameters | architecture family only; not justified until scalar/direct diagnostics demonstrate need |

## 4. Precision-observation context

| Result | Current value / scope | Project implication |
|---|---|---|
| **LBT `Y_p` Project IV** | `Y_p = 0.2458 ± 0.0013` | helium precision is now about 0.5%; weak-rate and covariance bookkeeping must be explicit |
| **LBT Project V** | joint cosmological interpretation of the new helium determination | future `OBS-v1` baseline/stress context |
| **2026 `N_eff` determination** | `N_eff = 2.990 ± 0.070` from combined primordial abundances, CMB and BAO | precision context for later cosmological inference; not part of R0 fixed-point mechanics |
| **Kislitsyn D/H update** | `(D/H)_p = (2.533 ± 0.024)×10^-5` | theory-rate choices can be comparable to current observational precision; data role remains governed by the existing observation freeze |

## 5. Claim boundary after the July 2026 review

The following claims are unavailable:

- first BBN Monte Carlo propagation of nuclear-rate uncertainty;
- first log-normal rate nuisance model;
- first explicit standard-BBN rate marginalization;
- first joint CMB+BBN inference with nuclear-rate nuisances;
- first differentiable BBN solver;
- first BBN neural emulator;
- first identification of the three dominant deuterium reactions;
- first large standard-BBN reaction-sensitivity atlas;
- first GP/function-level inference for the three deuterium reactions;
- first abundance–rate correlation or mutual-information analysis;
- first use of a flow, ratio estimator, diffusion model or Transformer for nuisance marginalization;
- first Schramm theoretical band;
- a blanket statement that direct BBN inference is computationally impossible.

## 6. Smallest defensible project delta

The candidate contribution is the **tested intersection** of:

1. current posterior or actual-PDF nuclear-rate information, beginning with ETR25;
2. coherent temperature-dependent rate-curve sampling;
3. calibrated joint abundance distributions `p(y | theta)`, not independent error bars only;
4. an explicit map of where a fixed post-hoc `C_th` approximation fails or remains adequate;
5. matched decomposition of rate library, weak physics, network, numerical engine and precision;
6. direct posterior recovery, prior/posterior SBC, OOD detection and solver fallback;
7. measured end-to-end economics against PRIMAT, PRyMordial, LINX and TMNRE/AMNRE-style baselines.

No component alone is a cleared claim. A scientific contribution exists only if the registered
experiments measure a distributional, posterior or computational effect beyond the frozen null
boundaries.

## 7. Immediate reproduction and implementation queue

1. ingest ETR25 R0 files, revisions and checksums;
2. preserve coherent rate-curve draws and audit actual-PDF versus log-normal behavior;
3. reproduce PRIMAT native `run_mc()` / `mc_uncertainty()` at the frozen point;
4. reproduce one PRyMordial explicit-marginalization result;
5. run LINX central and `nuclear_rates_q` perturbation checks;
6. reproduce one sensitivity-atlas R0 slice;
7. reproduce the structure of the 2026 GP deuterium prior;
8. measure the joint `p(Y_p,D/H | theta)` and `C_rate(theta)` drift;
9. compare `U-M1` against direct `U-M2` before training a complex model;
10. freeze the post-Gate method baseline set including TMNRE/AMNRE and modern calibration.

## 8. Search limitation

The review used primary journal pages, arXiv, official repositories, PyPI and official data
archives. Failure to locate a paper is not proof that it does not exist; terminology differences,
private work, conference material and newly posted unindexed manuscripts may be missed.
Monthly refresh and independent A11 review remain required.

Prepared by: Codex in the A02/A11 literature role.  
A00/A11/A09 claim sign-off: **pending**.  
Nature-tier status: **CLOSED pending measured effect and method necessity**.
