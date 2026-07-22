# COMPETITOR_MATRIX_v1

Status: evidence inventory complete; independent claim audit pending
Freeze date: 2026-07-21 UTC
Task: `P0-LIT-01` / scientific blocker `LIT-02`

This matrix records the strongest relevant baseline known at the freeze date.
Versions and licenses were checked against the authors' repository, package
registry, project site, paper, or experiment document. “Reproducible” below
describes accessible artifacts, not scientific endorsement.

## Mandatory matrix

| Object | Frozen version/date | Solved problem | Rate uncertainty | Non-standard cosmology | Differentiable | Joint inference | Code / license | Reproducibility at freeze | Minimum project delta |
|---|---|---|---|---|---|---|---|---|---|
| BBNet | arXiv `2512.15266v1`, 2025-12-17; code `ea66fe6` | PArthENoPE/AlterBBN abundance emulator for extended cosmology | central-value emulator in public package | yes: dark radiation and stiff EOS in training solvers | no | embeddable | [repository](https://github.com/Hdiao112/BBNet), nested MIT license | partial: source and scalers exist at HEAD, but pretrained `.pth` weights are absent at HEAD | calibrated distributional UQ, nuisance variables, complete artifacts, solver/rate decomposition |
| LINX | `v0.1.2`, 2026-06-19, `ec2e9d2` | fast JAX BBN with multiple networks | scalar `nuclear_rates_q`; multiple network/rate choices | extensible | yes | demonstrated CMB+BBN workflows | [repository](https://github.com/cgiovanetti/LINX), MIT | high: tagged release, tests and documentation | project stiff/SGWB implementation, functional rates, multi-solver audit, SBC-scale cost evidence |
| ABCMB + LINX | ABCMB `v0.3.1`, 2026-06-02, `5eabbab`; LINX `v0.1.2` | differentiable CMB power spectra plus direct BBN | inherited from LINX | ABCMB is extensible; project extension not supplied | yes | yes | [ABCMB](https://github.com/TonyZhou729/ABCMB), [LINX](https://github.com/cgiovanetti/LINX), MIT | high for tagged baseline; project extension untested | benchmark gradients, FP64, HMC/NUTS and extension cost before claiming emulator necessity |
| PRyMordial | paper arXiv `2307.07061`; code `725d8a8`, 2026-05-08 | first-principles thermodynamics/BBN within and beyond SM | log-normal marginalization; NACRE-II-like and PRIMAT-like choices | yes | limited / not JAX AD | external samplers | [repository](https://github.com/vallima/PRyMordial), GPL-3.0-or-later | medium-high: source and demos, but no tagged release at freeze | functional rates, project extension, matched-physics solver comparison and end-to-end budget |
| PRIMAT | Python/C `v0.3.2`, 2026-07-14 | precision BBN, detailed weak physics and full networks | nuclear MC/rate uncertainties | limited; modifiable | no | Cobaya companion announced/available | [repository](https://github.com/CyrilPitrou/primat), GPL per [official site](https://www2.iap.fr/users/pitrou/primat.htm) | high for current public package; legacy Mathematica line remains a separate version | independent precision points, functional-mode challenge and matched weak/rate inputs |
| PArthENoPE | `3.0`, 2021-03-10; CPC 2022 | mature Fortran BBN with updated deuterium rates | rate variations / MC workflows, not project functional posterior | limited built-ins; source-modifiable | no | external | [official site](https://parthenope.na.infn.it/), GPLv3; [program archive](https://doi.org/10.17632/wvgr7d8yt9.2) | medium-high: versioned distribution and manual; no canonical GitHub | audit modified project fork, expose structured failures, functional rates and matched-factor experiments |
| AlterBBN | v2 paper arXiv `1806.11095`, 2018 | fast BBN in alternative cosmologies | ERR bounds and MC-style options | yes | no | external | [official project](https://alterbbn.hepforge.org/), GPLv3 in program paper | medium: public C code, but freeze-time canonical release commit is not identified | engineering cross-check only; cannot stand in for independent precision nuclear physics |
| Cook–Meyers expansion PCA | arXiv `2512.11163v2`, 2026-02-24 / PRD 113 043519 | general positive expansion-history perturbations and PCA during BBN | modern inputs, not full functional/multi-solver UQ | yes | no | Cobaya + modified AlterBBN | paper public; modified code link not found in paper/source | low-medium: equations public, exact modified solver/pipeline unavailable | add complete nuclear/weak/solver UQ and SGWB connection; do not claim PCA itself as novel |
| 2026 sensitivity atlas | arXiv `2603.22414v1`; data `d3ea183`, 2026-04-09 | 14 parameters and 63 rates, two compilations and two weak normalizations | yes, ranked | BSM-relevant reference but mainly local sensitivities | no | no | [atlas](https://github.com/Anne-KatherineBurns/bbn-sensitivity-atlas), CC0-1.0; PRyMordial GPL | high for published tables/figures; computation depends on PRyMordial | demonstrate non-standard rank reordering and nuclear value-of-information, not repeat standard ranking |
| 2026 GP D/H | arXiv `2604.16600v1`, 2026-04-17 | GP fits to three deuterium-burning S factors and propagation to D/H | functional GP posterior for three rates | standard BBN in paper | no | no | paper/source public; no separate analysis repository linked; LINX `v0.1.2` contains GP/Chen rate additions | medium: method and TeX public, exact end-to-end analysis artifact not identified | propagate registered functional modes into extended posterior/GW endpoints and compare scalar vs functional models |
| LVK O1–O4a stiff search | DCC `P2500150-v13`; arXiv `2510.26848v2` | direct SGWB constraints for stiff era with CBC background | not applicable | stiff expansion / kination | no | GW Bayesian analysis | [DCC](https://dcc.ligo.org/LIGO-P2500150/public); [GWOSC O4a](https://gwosc.org/O4/O4a/) strain CC BY 4.0 | partial: manuscript and strain public; standalone stiff likelihood/posterior not attached at freeze | self-consistent BBN UQ plus validated LVK likelihood, not an approximate bound overlay |

## Claim boundary

The matrix makes the following claims unavailable without additional evidence:

- neural emulation of BBN abundance is not new;
- scalar nuclear-rate marginalization is not new;
- differentiable direct BBN or CMB+BBN inference is not new;
- identifying the three dominant deuterium reactions is not new;
- PCA of a general BBN expansion history is not new;
- GP/function-level inference for the three head deuterium reactions is not new;
- direct stiff-era constraints from O1–O4a are not new.

The smallest defensible project delta is the intersection of project-specific
non-standard expansion/SGWB physics with functional nuclear-rate uncertainty,
matched multi-solver discrepancy, calibrated posterior inference, and a measured
end-to-end cost or scientific-decision change. Whether that delta yields a strong
claim remains an empirical question.

## Reproduction queue

Literature verification does not substitute for execution. The following remain
registered implementation tasks:

1. reproduce BBNet from a provenance-pinned source and recover or retrain weights;
2. run LINX standard BBN plus `nuclear_rates_q`;
3. run PRyMordial rate marginalization;
4. compare PRIMAT and LINX PRIMAT-network central values;
5. reproduce one sensitivity-atlas slice;
6. reproduce the GP prior/thermal-propagation structure;
7. benchmark ABCMB+LINX Fisher and gradient-based sampling;
8. obtain or validate an LVK stiff likelihood implementation.

No “first”, “unprecedented”, “solver-independent”, “unbiased”, or “complete”
wording is cleared by this document.

Prepared by: Codex acting in the A02 literature/competition role.
A00/A11/A09 claim sign-off: **pending**.
Track B status: **NOT FROZEN**.
