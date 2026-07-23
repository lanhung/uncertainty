# Native-UQ external reproducibility blockers v1

Status: **audited; exact reproduction remains 3/5; external audits are non-blocking under ADR-0008**

This record closes the unregistered guess-and-rerun loop for the two remaining
`UQ0-NATIVE-UQ-REPRO` baselines. It does not convert either baseline into an
accepted reproduction.

## Sensitivity atlas

The atlas paper (`arXiv:2603.22414v1`) was published on 2026-03-23. The
registered public PRyMordial revision,
`725d8a8db3ad5ea2630580d825c9d0d69ed76533`, was committed on 2026-05-08.
The last public PRyMordial revision before the paper was
`bf24c3d064fe35ec2d612f2ccd8f03306d570b6a`, committed on 2023-08-03.

The public comparison between those PRyMordial revisions contains two commits
but changes only:

```text
PRyMrates/nuclear/key_nacreii_rates/dpHe3g.txt
```

The registered atlas slice uses the PRIMAT compilation, not NACRE-II. The
three solver source files used by the run also have identical SHA256 digests
at both revisions. Re-running the older public commit would therefore repeat
the same registered code and PRIMAT rate path; it cannot resolve the observed
Li7 central-value mismatch.

The pinned atlas repository contains 701 paths and no files with common
generator-code extensions (`.py`, `.ipynb`, `.jl`, `.m`, `.r`, `.sh`). It
publishes result tables but no generator revision. The existing independent
run is retained with its four frozen acceptance failures and grants no exact-
reproduction credit. The required exact-reproduction unblock is the generating
code, exact solver revision and complete input configuration, or an upstream
correction.

## GP deuterium prior

The public paper structure is captured and hash-pinned, but an exact abundance
rerun still lacks:

- analysis code;
- fitted hyperparameters;
- exact experimental data bundle;
- posterior draws;
- random seed.

The required exact-reproduction unblock is a public package containing those
inputs and a seeded draw manifest sufficient to rerun the published abundance
distribution.

## ADR-0008 execution consequence

The frozen exact-reproduction status remains `3/5`; neither threshold is
relaxed and neither result is relabeled as accepted. However, these two objects
are literature-paper reproductions rather than sources of the project-owned R0
prior. `ADR-0008-self-contained-fast-track.md` therefore removes them from the
exploratory calculation dependency chain.

The active reference-prior path uses only public, versioned information already
captured in the repository and is explicitly labeled conditional on
`NUCLEAR-R0-REFERENCE-v1`. It may support exploratory direct calculations and a
validity/failure study of fixed `C_th`; it may not claim exact reconstruction of
the unpublished atlas or GP pipelines.

## Decision

`UQ0-NATIVE-UQ-REPRO` remains historically `3/5` and moves to the non-blocking
execution/evidence lane in plan version 6. External blocker evidence remains
immutable. Exploratory reference-prior calculations are authorized separately;
publication-grade nuclear-posterior claims and independent scientific sign-off
remain closed.
