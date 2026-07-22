# Historical foundations of BBN nuclear-rate uncertainty

> Review date: **2026-07-23**  
> Role: historical prior-art supplement to `FRONTIER_REVIEW_2026-07.md`  
> Scope: direct nuclear-data propagation, Monte Carlo abundance uncertainties, correlated cross-section systematics and rate-distribution libraries

## 1. Why this historical audit matters

The current project must not describe direct nuclear-data propagation, Monte Carlo abundance bands, abundance–rate correlations or statistically defined thermonuclear-rate distributions as inventions of the machine-learning era. These ideas have a long BBN and nuclear-astrophysics history.

The project opportunity lies in combining modern nuclear probability products with a parameter-dependent **joint** abundance distribution, a quantitative test of fixed post-hoc theoretical covariance, matched solver factorization, calibrated amortized inference and measured end-to-end economics.

## 2. Foundational BBN Monte Carlo work

### 2.1 Krauss & Romanelli 1990

`Big Bang nucleosynthesis: Predictions and uncertainties` reexamined the principal nuclear data and neutron lifetime and propagated them through a Monte Carlo BBN calculation to attach confidence levels to standard-BBN predictions.

**Boundary:** neither Monte Carlo BBN uncertainty nor confidence bands are new.

Reference: L. M. Krauss and P. Romanelli, *Astrophysical Journal* **358**, 47–59 (1990), DOI `10.1086/168962`.

### 2.2 Nollett & Burles 2000

`Estimating reaction rates and uncertainties for primordial nucleosynthesis` introduced a direct Monte Carlo treatment that worked from published experimental nuclear inputs rather than relying only on intermediate evaluated-rate summaries. It was designed to incorporate new measurements transparently and found that some previous BBN abundance-error estimates were too large by as much as a factor of three.

**Boundary:** direct incorporation of experimental nuclear inputs into BBN uncertainty propagation is established prior art. The current project may update, systematize and amortize it, but cannot claim to originate the concept.

Reference: K. M. Nollett and S. Burles, *Physical Review D* **61**, 123505 (2000), arXiv `astro-ph/0001440`, DOI `10.1103/PhysRevD.61.123505`.

### 2.3 Burles, Nollett & Turner 2001

The subsequent precision-cosmology work used improved BBN uncertainty estimates in baryon-density inference and precision BBN predictions.

**Boundary:** propagating improved nuclear inputs into cosmological parameter conclusions is also established; novelty requires a quantitatively new inference consequence or methodology.

Representative references:

- S. Burles, K. M. Nollett and M. S. Turner, *Physical Review D* **63**, 063512 (2001);
- S. Burles, K. M. Nollett and M. S. Turner, *Astrophysical Journal Letters* **552**, L1 (2001).

## 3. Correlated nuclear-data and network analyses

### 3.1 Cyburt 2004

`Primordial nucleosynthesis for the new cosmology: Determining uncertainties and examining concordance` critically modeled nuclear cross-section data, correlations and data-set systematic errors before propagating them to abundance and cosmological constraints.

**Boundary:** handling correlations and cross-experiment normalization systematics is not a new conceptual contribution. A modern implementation must reproduce or improve this statistical discipline rather than assume independent rate nuisances by default.

Reference: R. H. Cyburt, *Physical Review D* **70**, 023505 (2004), arXiv `astro-ph/0401091`, DOI `10.1103/PhysRevD.70.023505`.

### 3.2 Serpico et al. 2004

`Nuclear Reaction Network for Primordial Nucleosynthesis` analyzed weak rates, neutrino decoupling, nuclear-rate modeling, experimental data and uncertainty contributions for the main light nuclides.

**Boundary:** a detailed standard-BBN rate/network uncertainty inventory is established prior art.

Reference: P. D. Serpico et al., *JCAP* **12** (2004) 010, arXiv `astro-ph/0408076`, DOI `10.1088/1475-7516/2004/12/010`.

### 3.3 Coc, Uzan & Vangioni 2014

An extended-network BBN calculation propagated reaction-rate uncertainties to rare nuclides and CNO and analyzed yield–rate correlations.

**Boundary:** large-network Monte Carlo and reaction-importance/correlation analysis are not new by themselves.

Reference: A. Coc, J.-P. Uzan and E. Vangioni, arXiv `1403.6694`.

### 3.4 Iliadis & Coc 2020

This work combined BBN Monte Carlo, abundance–rate mutual information and a genetic search over simultaneous rate changes for the lithium problem.

**Boundary:** abundance–rate mutual information, rate ranking and simultaneous-rate search are established baselines.

Reference: C. Iliadis and A. Coc, *Astrophysical Journal* **901**, 127 (2020), arXiv `2008.12200`.

## 4. Statistical thermonuclear-rate libraries

### 4.1 Monte Carlo rate formalism

Longland and collaborators developed statistically defined low, median and high rates and log-normal approximations from Monte Carlo propagation of nuclear quantities. This formalism underlies STARLIB and the later ETR25 evaluation.

Representative references:

- R. Longland et al., *Nuclear Physics A* **841**, 1 (2010), `Charged-particle thermonuclear reaction rates: I. Monte Carlo method and statistical distributions`;
- R. Longland et al., conference summary, DOI `10.1063/1.3455927`.

### 4.2 STARLIB 2013

STARLIB distributed tabulated reaction rates together with uncertainties and rate probability distributions, commonly represented as log-normal distributions when adequate.

**Boundary:** distributing rate PDFs and using log-normal rate factors in Monte Carlo nucleosynthesis are established nuclear-astrophysics practices.

Reference: A. L. Sallaska et al., *Astrophysical Journal Supplement Series* **207**, 18 (2013), DOI `10.1088/0067-0049/207/1/18`.

### 4.3 ETR25 as the current update

ETR25 is not the beginning of rate-PDF evaluation; it is the current large experimental-rate update. It supplies actual 16th/50th/84th percentile rates and a factor-uncertainty log-normal approximation for 78 rates, with public data and code.

**Project role:** use ETR25 as a current source, while preserving the distinction between actual rate-density products and approximations.

## 5. Updated claim blacklist

The project must not claim:

- first Monte Carlo propagation of BBN nuclear uncertainty;
- first direct use of experimental nuclear inputs in BBN uncertainty propagation;
- first confidence bands or Schramm uncertainty bands;
- first treatment of correlated cross-section data or experiment-normalization systematics;
- first statistically defined low/median/high thermonuclear rates;
- first log-normal rate-factor library;
- first abundance–rate correlation, sensitivity or mutual-information analysis;
- first use of uncertainty propagation to update baryon-density or other cosmological inferences.

## 6. What remains potentially new

A defensible contribution requires a combination not supplied by the historical work alone:

1. current ETR25 or original posterior products with immutable provenance;
2. coherent sampled rate curves over temperature;
3. calibrated joint `p(y | theta)` rather than only marginal error bars;
4. a preregistered map of fixed-`C_th` validity or failure across cosmological parameter space;
5. matched rate-library, weak-physics, network and numerical-engine decomposition;
6. direct posterior recovery, prior/posterior SBC, local coverage, OOD and fallback;
7. an end-to-end comparison with modern PRIMAT, PRyMordial, LINX and nuisance-marginal SBI baselines.

The novelty is the measured intersection and its scientific consequence, not any one ingredient.

## 7. Immediate implementation consequence

The ETR25 ingestion task should explicitly compare against the methodological lineage above. When actual source products are missing or ambiguous, the project must remain fail-closed and document the limitation rather than silently constructing independent Gaussian temperature-bin perturbations.
