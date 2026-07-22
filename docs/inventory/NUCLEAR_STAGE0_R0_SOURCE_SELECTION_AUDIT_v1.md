# R0 nuclear-rate source-selection audit v1

Status: **provenance prepared; numerical prior and scientific selection pending**

Date: 2026-07-23 UTC

Task: `UQ0-R0-RATE-PRIOR`

## Outcome

The existing public inventory is sufficient to bind seven solver-distributed
collections to 21 tracked files at four exact Git revisions. It contains 18
unique byte payloads and three duplicate payload groups. All three duplicate
groups are the LINX `key_PRIMAT_2023` tables copied into ABCMB's bundled LINX
tree; they are one software lineage, not two independent nuclear inputs.

`configs/physics/nuclear_stage0_R0_source_candidates_v1.yaml` now maps each
canonical R0 reaction ID to every captured candidate path and SHA256. The
deterministic validator rejects missing files, revision/license drift,
unacknowledged duplicate lineage, any selected primary candidate, or any claim
of numerical-prior credit.

This does **not** complete any of the three reaction units in
`UQ0-R0-RATE-PRIOR`. The source-selection audit is a provenance preparation
artifact only.

## What is established

| Repository | Frozen revision | Collections | Files | Scientific interpretation |
|---|---|---:|---:|---|
| LINX | `ec2e9d2ca455e8204137e884da29f5dd13a638fa` | 2 | 6 | Exact distributed bytes only |
| PRyMordial | `725d8a8db3ad5ea2630580d825c9d0d69ed76533` | 2 | 6 | Exact distributed bytes only |
| PRIMAT | `21ff8f39fa18e3937e9fdf386cfa982361bfdfce` | 2 | 6 | Exact distributed bytes only |
| ABCMB | `5eabbab4ed7e53f264e16024743d1ba517845c37` | 1 | 3 | Exact copy of LINX bytes |

The canonical-to-file association is intentionally labelled
`filename_token_candidate_only`. A physically validated solver mapping requires
source-code/parser review and a `z=0,+1,-1` regression; matching a filename is
not enough.

## Which fields exact source can and cannot establish

| R0 field or evidence | Exact pinned source can establish | Still requires literature/physics review |
|---|---|---|
| repository revision/tree, tracked path, Git blob, SHA256, size, line count | Yes; already captured | No additional numerical interpretation follows |
| byte-identical copies across repositories | Yes; already captured | Whether two non-identical tables share upstream data/systematics |
| `source_revision` and raw `source_checksum` | Yes, after a primary candidate is selected | The primary selection itself and authoritative upstream data identity |
| numeric rows and parser/interpolation implementation | Yes, by independent extraction from the pinned checkout | Whether the implementation matches the publication and physical convention |
| column labels, grid variable and units | Only when unambiguously declared by pinned code/documentation | Independent confirmation against the primary publication/data release |
| central curve versus low/high, factor uncertainty, `sigma_i(T)` or draws | Only the implemented transformation can be read | Statistical meaning, coverage and suitability as the registered prior |
| solver filename/internal rate token | Candidate token can be read | Canonical reaction mapping and `z_i` transform require regression validation |
| covariance and shared normalization | Only if an explicit matrix/model is present | Completeness, cross-reaction systematics and missing-correlation stress design |
| detailed balance / reverse-rate code | Formula and constants can be read | Unit-consistent physical validation and forward/reverse regression |
| `production_enabled` | No | A03, A00 and A09 must approve the full numerical package |

Thus exact source can safely fill software provenance and, after a reviewed
selection, immutable raw-source identifiers. It cannot by itself turn the table
inventory into a numerical prior or authorize production.

## Evidence that is still missing

For each of `d(p,gamma)3He`, `d(d,n)3He`, and `d(d,p)t`, the current repository
still lacks a reviewed package that jointly establishes:

1. the underlying primary publication, public data release and immutable raw
   input checksum;
2. every table column, temperature coordinate, interpolation convention and
   physical unit;
3. which values define the central curve and which define `sigma_i(T)`, a
   factor uncertainty, or posterior draws;
4. shared experimental normalization and cross-reaction covariance, or a
   preregistered stress test when those correlations are unavailable;
5. forward/reverse detailed-balance handling;
6. the solver-internal reaction identifier and exact transform from canonical
   `z_i` to the solver input;
7. central and symmetric `z_i=+1,-1` regression results with structured
   failures;
8. A03 nuclear-data review, A00 scientific sign-off and A09 independent
   validation.

Therefore the capture cannot populate `central_curve`, `temperature_grid`,
`units`, `uncertainty_model`, `covariance_status`, `detailed_balance`, or a
validated `solver_mappings` entry in
`configs/physics/nuclear_stage0_R0_v1.yaml`.

## Safe next sequence

1. Audit the parsers and upstream documentation at the already frozen source
   revisions; record primary citations and table-column semantics without
   choosing a result-favourable compilation.
2. Select the R0 baseline and at least one alternative compilation using
   predeclared provenance, covariance and solver-support criteria.
3. Create an immutable numerical source package containing raw tables,
   normalized curves, units/grids, covariance representation, licenses and
   checksums.
4. Implement versioned adapter mappings and run the required central/`+1`/`-1`
   regressions before generating any Monte Carlo label.
5. Obtain A03/A00/A09 reviews. Until then, `production_enabled` remains false
   and missing covariance must not be interpreted as independence.

## Reproduction

```bash
python scripts/validate_nuclear_stage0_R0_source_candidates.py \
  --candidates configs/physics/nuclear_stage0_R0_source_candidates_v1.yaml \
  --capture artifacts/provenance/PUBLIC-NUCLEAR-RATE-PROVENANCE-v1/capture-20260722T200435Z.json \
  --stage configs/physics/nuclear_stage0_R0_v1.yaml
```

Expected summary at this revision:

```text
{"bound_files": 21, "candidate_collections": 7, "copied_lineage_hashes": 3, "pending_selection_gates": 12, "unique_byte_payloads": 18}
```
