# NOVELTY_CLEARANCE_v1

Status: **DRAFT — CLAIMS NOT CLEARED; TRACK B NOT FROZEN**

Evidence freeze inherited from: `COMPETITOR_MATRIX_v1`, 2026-07-21 UTC

Tasks: `LIT-02`, `WHY-01`, `RATE-F01`, `FISH-01`

## Decision boundary

This document records the smallest candidate scientific and computational
deltas, the experiments that could support them, and the results that would
stop them. It is not a novelty approval. No “first”, “unprecedented”,
“solver-independent”, “unbiased”, or “complete” wording is cleared.

The claims below are hypotheses constrained by the frozen competitor matrix.
They become reportable only after their linked evidence exists and the required
independent sign-offs are recorded.

## Q1 — Minimum difference from BBNet, LINX, PRyMordial, and PRIMAT

The smallest candidate project delta is the tested intersection of:

1. a registered non-standard expansion/SGWB model;
2. scalar and posterior-derived functional nuclear-rate uncertainty;
3. matched decomposition of engine, rate-library, weak-physics, extension, and
   network effects;
4. calibrated posterior inference with explicit failures and certified direct
   solver fallback;
5. a measured change in a preregistered physics decision or a measured
   end-to-end computational advantage at matched fidelity.

No component alone is novel. BBNet already covers BBN emulation for extended
cosmology; LINX covers fast differentiable BBN and scalar rate nuisances;
PRyMordial covers explicit rate marginalization beyond standard cosmology; and
PRIMAT provides a precision BBN reference. The intersection remains a candidate
delta, not a cleared claim, until `SOL-01`, `RATE-F01`, `FISH-01`, and `WHY-01`
produce evidence.

## Q2 — Standard-BBN results used only as regression tests

The following results are regression or calibration targets and cannot carry a
novelty claim:

- neural emulation of BBN abundances;
- scalar nuclear-rate marginalization;
- differentiable direct BBN or CMB+BBN inference;
- the importance of `d(p,gamma)3He`, `d(d,n)3He`, and `d(d,p)t` in standard BBN;
- standard-BBN sensitivity rankings;
- GP or function-level inference for the three head deuterium reactions;
- PCA descriptions of general BBN expansion histories;
- direct stiff-era constraints from LVK O1–O4a.

Standard fiducial values, local Jacobians, sensitivity-atlas slices, and
cross-solver central values are therefore used to detect implementation errors
and establish matched inputs. Reproducing them is necessary but scientifically
insufficient.

## Q3 — Candidate physics result if AI is removed

The physical candidate survives removal of AI only if direct or conventional
surrogate calculations show that, under a registered non-standard expansion:

- functional rate-shape uncertainty changes a preregistered posterior or
  detector-overlap endpoint beyond its frozen null boundary; or
- reaction sensitivity ordering changes across at least two rate libraries and
  produces a robust change in nuclear experimental value-of-information; or
- full nuclear/weak/multi-solver uncertainty changes a registered stiff-era or
  SGWB decision boundary.

The required evidence is the Fisher gate followed, if authorized, by matched
direct-solver and posterior validation. If all effects remain below the frozen
`0.1 sigma`, 5% interval-width, and no-topology-change boundaries, the physical
effect route stops; AI performance cannot rescue it.

## Q4 — Candidate method result if BBN is removed

A computational or machine-learning claim survives removal of BBN only if the
same nuisance-aware multi-fidelity method:

- preserves registered posterior fidelity, exact-binomial SBC coverage, and
  explicit OOD/fallback behavior;
- achieves the frozen `10x` high-fidelity-call or `5x` end-to-end wall-time
  advantage against strong direct and simple-surrogate baselines; and
- reproduces the advantage on at least one independent public stiff-ODE or
  scientific-simulator task, with multiple budgets and seeds.

No cross-task simulator, algorithmic contribution, or qualifying result is
currently registered. The NMI and broad computational-method claims therefore
remain unavailable.

## Q5 — Three most likely rejection reasons

| ID | Likely rejection | Why it is currently credible |
|---|---|---|
| `R1` | The physics effect is a known standard-BBN sensitivity result or is too small to change a decision. | Standard head reactions and their functional GP treatment are already known; no non-standard Fisher or posterior effect has passed. |
| `R2` | The claimed method is unnecessary because direct LINX/PRyMordial/PRIMAT or ABCMB+LINX is already feasible. | Only standard-point LINX/PRIMAT runtime slices exist; matched posterior, extensions, gradients, W1/W3, and full economics remain open. |
| `R3` | The result confounds solver engine, rate library, weak physics, extension implementation, or network choice and lacks independent calibration. | The matched factorial matrix, functional priors, modified S0/S1 solvers, posterior recovery, SBC, and red-team validation are incomplete. |

## Q6 — Experiments mapped to the rejection risks

| Risk | Preregistered experiment | Passing evidence | Failure action |
|---|---|---|---|
| `R1` | `FISH-01`, `RATE-F01`, standard-atlas regression, non-standard ranking, nuclear value-of-information | Effect exceeds a frozen endpoint threshold and is stable across registered data/rate-library strata. | Report the null result; do not broaden priors, data, reaction sets, or endpoints after inspection. |
| `R2` | `WHY-01`: W0 LINX, W1 PRyMordial, W2 PRIMAT, W3 ABCMB+LINX; matched posterior recovery and full workload projection | A missing-physics or measured cost/fidelity constraint survives the direct-first rule. | Use the qualifying direct stack; close the speed-only emulator claim. |
| `R3` | `SOL-01` matched E/R/W/X/nu experiments, M2-M7 posterior recovery, 1,000 SBC runs, challenge/OOD tests, independent rerun | Factor-specific residuals are identified, registered fidelity thresholds pass, and A09 evidence is independent. | Narrow or reject the flagship claim; do not label pipeline discrepancy as solver discrepancy. |

The experiments must retain their preregistered data, priors, thresholds, and
failure records. Unsupported competitor features are recorded as unsupported,
not silently replaced by the project's implementation.

## Q7 — Stop rule if the main physical effect is small

If the Fisher G0 condition holds—every registered core shift below `0.1 sigma`,
every interval-width change below 5%, and no topology change—Pilot-10k remains
unauthorized and the tested Nature Astronomy effect route closes. The project
may publish a calibrated null or Track A result, but it may not respond by:

- changing the primary observation compilation or neutron scenario;
- widening priors or adding endpoints after seeing the result;
- promoting lithium from null test to primary claim;
- searching additional reactions or non-standard models solely for
  significance;
- replacing physical endpoints with MSE, network size, or single-forward speed.

If direct tools pass the registered 14-day/672-worker-hour gate at matched
fidelity, speed alone also stops the new-emulator route. If a hybrid fails
coverage, posterior fidelity, or explicit-failure requirements, it is rejected
regardless of throughput.

## Evidence still required

- complete W0-W3 direct-solver measurements and final economics memo;
- modified PArthENoPE and AlterBBN sources plus matched solver-factor results;
- frozen `NUC-v1` numerical priors and validated functional bases;
- Fisher/Jacobian evidence and an authorized Gate report;
- posterior recovery, SBC, OOD, and challenge evidence;
- detector/extension contracts and frozen remaining endpoint thresholds;
- current monthly literature refresh when its scheduled date arrives;
- independent A00/A11/A09 claim review.

## Sign-off

Draft contract prepared by Codex from the frozen competitor inventory and
existing preregistered gates; this is not claim approval.

- A00 scientific lead: **pending**;
- A11 literature and competition: **pending**;
- A09 independent validation and red team: **pending**.

Track B remains **NOT FROZEN**.
