# Claim–evidence matrix v1

Status: **DRAFT — evidence mapped; claims not frozen**

Captured: 2026-07-22 UTC

Registry: `configs/claims/claim_evidence_matrix_v1.yaml`

## Purpose

This matrix prevents an available engineering or standard-point artifact from
being generalized into a physical, method, or broad-impact claim. Each claim
has a tier, exact scope, current evidence, missing evidence, falsifier, and
required independent sign-offs.

The registry is not a paper claim list. Candidate statements at `C2`–`C4` are
hypotheses and are unavailable for reporting until their gates pass.

## Current claim state

| Claim | Tier | Current state | Maximum allowed interpretation |
|---|---|---|---|
| `C0-OPS-CONTROL-01` | C0 | evidence registered; review pending | local/worker engineering smokes only |
| `C1-LINX-STANDARD-NUMERICS-01` | C1 | scope-limited evidence | one frozen standard-BBN point only |
| `C1-DIRECT-SOLVER-COST-01` | C1 | incomplete | W0–W3 fiducial runtime slices and accepted native-UQ reproductions only |
| `C2-HYBRID-CALIBRATION-01` | C2 | unavailable | no method claim |
| `C3-FUNCTIONAL-RATE-SHAPE-01` | C3 | unavailable | no functional-rate physics claim |
| `C3-SENSITIVITY-REORDERING-01` | C3 | unavailable | no reordering or experiment-priority claim |
| `C3-SGWB-DECISION-01` | C3 | unavailable | no SGWB/decision-change claim |
| `C4-BROAD-PHYSICS-01` | C4 | unavailable | no broad physical-impact claim |
| `C4-CROSS-TASK-METHOD-01` | C4 | unavailable | no cross-task method claim |

## Evidence boundaries

The accepted LINX V4 artifact supports only the registered standard-point
numerical candidate. It does not establish parameter-region fidelity, a finite
gradient, rate-nuisance correctness, extension fidelity, or posterior recovery.

All four W0–W3 standard-fiducial runtime slices are integrity-validated, but
they do not answer the direct-first decision. PRIMAT and PRyMordial native-UQ
reproductions are accepted; the frozen LINX candidate and sensitivity-atlas
slice are not accepted, while the GP abundance rerun is blocked by unavailable
public code, fitted hyperparameters, exact data, posterior draws, and seed.
The accepted R0 production prior, direct UQ workload, posterior recovery,
robustness, SBC, and joint-likelihood economics are still missing.

The current NUC-v1 file is a non-production schema with placeholders. It is not
evidence for scalar or functional nuclear priors. Consequently, all functional
rate, sensitivity-reordering and nuclear value-of-information claims remain
unavailable.

## Negative evidence

A falsifier is part of every registry entry. Failure of an effect, fidelity,
coverage, cost, rank-reordering or cross-task condition narrows or closes that
claim. It does not authorize changing the primary data, prior, reaction set,
endpoint, or route after inspecting the result.

## Sign-off

This registry was prepared by Codex as an evidence-control contract, not as
claim approval.

- A00 scientific lead: **pending**;
- A09 independent validation: **pending**;
- A11 literature and competition: **pending**;
- A12 publication strategy: **pending**.

Track B remains **NOT FROZEN** and the Nature-tier gate remains **CLOSED**.
