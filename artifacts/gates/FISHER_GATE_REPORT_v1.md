# Fisher Gate report v1

Status: **NOT EVALUATED**

Protocol: `docs/decisions/ADR-FISHER-GATE-v1.md`

Task: `P2.5-gate-report`

## Immutable inputs

| Input | Path/revision | SHA-256 | Status |
|---|---|---|---|
| canonical point manifest | pending | pending | not frozen |
| physics parameter schema | `configs/physics/parameter_schema.yaml` | pending at execution | standard subset only |
| observation snapshot | `configs/data/abundance_OBS-v1.yaml` | pending at execution | frozen, sign-off pending |
| nuclear prior/rate covariance | pending NUC-v1 | pending | blocked |
| functional modes | pending | pending | blocked |
| solver factorial/build cards | pending | pending | blocked |
| response arrays | pending | pending | not run |
| propagation code | pending | pending | not run |

## Coverage

| Region | Required | Accepted | Failed | Status |
|---|---:|---:|---:|---|
| standard BBN / observational region | pending allocation | 0 | 0 | not run |
| posterior high-density | pending allocation | 0 | 0 | blocked by reference posterior |
| extension regions | pending allocation | 0 | 0 | blocked by extension contract |
| decision boundaries / degeneracies | pending allocation | 0 | 0 | not frozen |
| OOD/failure critical | pending allocation | 0 | 0 | not frozen |
| **total distinct points** | **at least 64** | **0** | **0** | **not run** |

## Response validation

| Object | Finite fraction | step-size convergence | autodiff agreement | Status |
|---|---:|---:|---:|---|
| `J_theta` | pending | pending | pending | not run |
| `J_q` | pending | pending | pending | not run |
| `J_a` | pending | pending | pending | blocked by functional basis |
| `C_rate` | pending | pending | not applicable | blocked by NUC-v1 |
| `C_shape` | pending | pending | not applicable | blocked by functional basis |
| `C_solver` | pending | pending | not applicable | blocked by matched factorial |

The W0 LINX upstream source smoke produced a non-finite gradient component. It
is registered as failed evidence and is not entered into this table as an
accepted derivative.

## Approximate posterior effects

| Endpoint | center shift / sigma | interval change | topology | Status |
|---|---:|---:|---|---|
| core standard parameters | pending | pending | pending | not run |
| registered extension parameters | pending | pending | pending | blocked |
| detector-relevant volume | pending | pending | pending | blocked |
| nuclear value-of-information | pending | pending | not applicable | blocked |

## Decision

Gate: **NOT EVALUATED**

Pilot-10k authorization: **NO**

Reason: the response point set, NUC-v1 covariance, functional modes, matched
solver discrepancy and extension contract do not yet exist. This is an empty
report template, not a G0 finding.

## Sign-off

- A00 scientific lead: pending;
- A03 statistics validation: pending;
- A04 solver validation: pending;
- independent/red-team: pending if G3 is proposed.
