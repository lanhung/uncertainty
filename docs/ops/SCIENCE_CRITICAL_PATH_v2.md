# Science critical path v2 — manuscript first, self-contained UQ second

> Effective date: 2026-07-23  
> Governing decision: `docs/decisions/ADR-0005-manuscript-baseline-self-contained-pivot.md`

## 1. The two deliverables

### Deliverable A — submit the existing four-abundance stiff-phase paper

The immediate paper is already scientifically formed. It tests a homogeneous pre-BBN stiff phase with self-consistent SGWB feedback, a four-abundance BBNet+ emulator, two BBN backends and Cobaya inference. The remaining work is release integrity, exact reproduction and submission hardening—not another open-ended method campaign.

### Deliverable B — decide whether nuclear-rate UQ changes the no-go result

The sequel asks whether full nuclear/weak/backend uncertainty changes the statement that every lithium-lowering stiff direction violates `D/H` or `Y_p`. This is a decision-focused extension of the manuscript, not a generic 100-dimensional emulator exercise.

## 2. Work explicitly paused

Until `M0-JCAP-FREEZE` or a documented blocker decision, do not start new work on:

- full ABCMB Fisher/HMC audit beyond what is needed for a manuscript claim;
- general LINX gradient debugging unrelated to the scalar-UQ smoke;
- generic W0–W3 challenge grids;
- Pilot-1k/Pilot-10k production;
- 12- or 100-reaction full registries;
- a new flow/GAN/diffusion/Transformer architecture;
- Nature Machine Intelligence or Nature Computational Science benchmark campaigns.

The code and protocols already produced remain available in Git history and can be reactivated by a future plan revision.

## 3. First 72 hours

### M0-MANUSCRIPT-REGISTER

- bind the manuscript title, physical definitions, reported results and figure/table inventory;
- list every claim that depends on a private or unpublished asset;
- identify every unresolved citation or placeholder;
- compare the data/software availability statement with the actual public repositories.

### M0-ASSET-HANDOFF

Collect or locate:

```text
BBNet+ four-output code
PArthENoPE weights/scalers
AlterBBN base + expert weights/scalers
training configuration
training data manifest or generator
modified PArthENoPE source/patch
modified AlterBBN source/patch
SageNet+ exact source/weights
stiffGWpy exact revision
Cobaya theory + likelihood + YAML
main/partial/consistency/hard-soft chains
deterministic scans
plotting scripts
```

Every binary enters the existing quarantine/intake process. Do not use a filename or README statement as provenance.

### M0-PHYSICS-CONTRACT

Freeze, with tests:

- `kappa10 = rho_stiff/rho_gamma` at `T=10 MeV`;
- the direct stiff term in `H(T)`;
- the SGWB-to-`Delta N_eff` integral and gate;
- `T_re`, `DN_re`, `r`, `n_t` and consistency-relation semantics;
- backend-specific transformations without inventing missing `dd0/dd0_rad` mappings.

### M0-DATA-STRATA

- retain `MANUSCRIPT-OBS-v1` exactly for the submitted paper;
- retain `OBS-v1` exactly for the UQ sequel;
- do not compare their numerical conclusions without explicitly naming the stratum.

## 4. Days 4–7: paper reproduction

### Emulator reproduction

On a clean worker environment, reproduce at minimum:

1. one standard four-abundance Schramm slice against each solver backend;
2. held-out metrics for all four abundances;
3. one single-point and one batch timing result;
4. the SGWB integration test and rejection behavior.

### Inference reproduction

Reproduce at minimum:

1. one full-search backend posterior and `log10(kappa10)_95`;
2. the D/H+`Y_p` partial likelihood;
3. the Li-only diagnostic and its deuterium cost;
4. one free-`Delta N_eff` or free-`kappa10` deterministic diagnostic;
5. chain convergence and exact config/source hashes.

A clean reproduction may use a released checkpoint. Retraining is not required for submission if the checkpoint lineage is complete. If checkpoint lineage cannot be established, retraining becomes mandatory.

## 5. Days 8–10: public release and manuscript audit

- publish BBNet+ four-abundance source, weights, scalers and exact environment;
- publish or accurately describe the modified solver availability;
- create the Zenodo deposition draft with chain summaries, scan tables, figure inputs and checksums;
- remove all unresolved bibliography placeholders;
- verify that every numerical statement in the abstract, tables and conclusions is sourced by a committed manifest;
- ensure the direct numerical benchmark is described only as a wall-time benchmark, not a converged posterior.

## 6. Days 11–14: scalar-UQ smoke

The first UQ experiment uses six thermonuclear reactions plus separately modeled neutron/weak uncertainty:

```text
d(p,gamma)3He
d(d,n)3He
d(d,p)t
3He(alpha,gamma)7Be
7Be(n,p)7Li
7Li(p,alpha)4He
```

Run a non-claim engineering smoke at 16 representative points. For each rate use at least `q=-1,0,+1`; use `q=-2,+2` where the source prior supports it. Compute finite-difference responses for:

- `Y_p`, `D/H`, `3He/H`, `7Li/H`;
- `log10(kappa10)_95` proxy or local constraint direction;
- deuterium/helium tension at the lithium plateau target;
- backend disagreement.

The 16-point smoke can discover implementation errors and obvious effect-size limits, but cannot replace the preregistered 64-point Fisher Gate.

## 7. Self-contained rebuild decision tree

### Original assets available

Use them, hash them, release them, and reproduce before retraining.

### Weights unavailable but generators/solvers available

Regenerate a versioned four-abundance dataset and retrain a simple deterministic baseline first. Do not begin with a new exotic architecture.

### Modified solvers unavailable

Implement the stiff model clean-room in a public solver. Recommended order:

1. LINX or PRyMordial for rapid transparent development;
2. official PArthENoPE 3.0 and AlterBBN 2.2 as independent checks where licensing and interfaces permit;
3. PRIMAT reference points;
4. only then train BBNet+ from newly generated labels.

### No exact paper pipeline can be recovered

The JCAP manuscript must change its data/software statement and reproducibility wording. The new clean-room work is labeled a new implementation and cannot be represented as exact recovery of the submitted result.

## 8. Submission go/no-go

`M0-JCAP-FREEZE` requires:

- a clean run reproducing the agreed core results;
- accessible code/weights or an accurate restricted-availability statement;
- immutable environment and source revisions;
- chain/scan archive ready for DOI assignment;
- all references and placeholders resolved;
- scientific-lead and independent reproducibility sign-off.

The paper does **not** wait for the full nuclear-rate UQ sequel.

## 9. UQ go/no-go

After the 16-point smoke, freeze and execute the 64-point Fisher set.

- `G0`: no Pilot-10k; write a robust-null/upper-bound result if useful;
- `G1`: targeted Pilot-1k only;
- `G2/G3`: authorize functional modes, Pilot-10k, cross-solver production and Nature-tier red team.

The active desired-state plan intentionally stops at the Gate. Conditional tasks are added only after the Gate decision.
