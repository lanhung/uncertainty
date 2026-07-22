# WEAK-PRIOR-v1: neutron-lifetime and weak-normalization contract

Status: **implementation contract frozen; scientific sign-off pending; production use prohibited**

Task: `UQ0-WEAK-PRIOR`

Registry: `configs/physics/weak_prior_WEAK-v1.yaml`

## Decision

Stage R0 has one active continuous weak-physics nuisance: the canonical free-neutron
lifetime `tau_n_seconds`, drawn from the already preregistered `NEUTRON-v1` scenarios.
An independent residual weak-theory normalization variable, `w_weak_norm`, is registered
separately but fixed to one and not sampled. No reviewed prior currently separates such a
residual correction from lifetime information, so inventing a width would create an
untraceable or duplicated uncertainty.

This is an implementation freeze, not the missing A00 or independent weak-physics
approval. It authorizes adapter construction and deterministic mapping tests only. It does
not authorize production labels, Track B inference or a weak-physics claim.

## Canonical sampling rule

Each project-level draw owns exactly one `tau_n_seconds` value. Solver-native lifetime
sampling is disabled. The adapter converts that value once, and the solver applies the
corresponding weak-rate normalization once.

| Path | Canonical conversion | Required branch | Double-counting guard |
|---|---|---|---|
| LINX `ec2e9d2` | `tau_n_fac = tau_n_seconds / 879.4 s` | dimensionless tables divided by `879.4 s * tau_n_fac` | do not pre-scale weak tables; keep `m_e` fixed |
| PRyMordial `725d8a8` | `tau_n = tau_n_seconds * second` | `tau_n_flag = True`, giving `1/(Fn*tau_n)` | do not also modify `NormWeakRates`; do not enable `NP_nTOp` |
| PRIMAT `21ff8f3` | `tau_n = tau_n_seconds` | `tau_n_normalization = True`, giving `NormWeakRates = 1/tau_n` | set native `std_tau_n=0`; do not combine external and native MC draws |

The exact Git blobs, SHA256 values, line spans and adapter invariants are frozen in the
machine-readable registry.

## Source-audit findings

### LINX

LINX stores weak-rate tables normalized to the neutron decay width. Both directions are
divided inside the abundance ODE by `const.tau_n * tau_n_fac`. Consequently, feeding the
canonical seconds value directly into `tau_n_fac`, or pre-scaling the tables, would be
wrong. LINX also multiplies `tau_n_fac` by an electron-mass-dependent factor when `m_e`
changes; Stage R0 therefore fixes `m_e` to the upstream constant.

### PRyMordial

With `tau_n_flag=True`, PRyMordial uses `NormWeakRates = 1/(Fn*tau_n)` and applies it to
the raw forward and backward rates. The `False` branch instead uses an absolute
`GF/Vud/gA` normalization. These are mutually exclusive weak-physics model choices, not
two nuisances to apply together.

### PRIMAT

PRIMAT stores cached weak rates in lifetime-normalized units and applies
`NormWeakRates = 1/tau_n` when `tau_n_normalization=True`. Its native Monte Carlo routine
also draws `tau_n` using `std_tau_n`; project-level Monte Carlo must disable that draw to
avoid sampling the same uncertainty twice. PRIMAT's explicit free-neutron decay term is
used in the later decay-time era after thermal BBN and is not a simultaneous second
normalization of the thermal weak rates.

## Remaining evidence before scientific readiness

- Run central and symmetric `tau_n` regressions through the unified nuisance adapter.
- Store canonical and transformed values plus the weak branch in every run manifest.
- Obtain A00 scientific approval.
- Obtain independent weak-physics review of the normalization semantics and the decision
  to leave `w_weak_norm` inactive.
- Introduce a new ADR before sampling any independent residual weak-theory nuisance.

Until those items are complete, the contract must remain `scientific_readiness: not_ready`
and `ready_for_production_labels: false`.

## Validation

```bash
python scripts/validate_weak_prior_contract.py \
  --contract configs/physics/weak_prior_WEAK-v1.yaml \
  --neutron-registry configs/physics/neutron_lifetime_v1.yaml
```
