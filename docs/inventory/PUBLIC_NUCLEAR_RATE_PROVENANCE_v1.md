# Public nuclear-rate provenance inventory v1

Status: exact-source inventory captured; scientific prior freeze still pending

Date: 2026-07-22 UTC

Tasks: `NUC-01`, `P2-rate-registry`, `P0-WHY-NOT-01`

## Purpose

This inventory binds the three registered head-deuterium rate tables distributed
by the exact public LINX, PRyMordial, PRIMAT and ABCMB source checkouts. The
capture records the source commit and tree, path, Git blob, SHA256, byte size and
line count. It also reports byte-identical copies across repositories so copied
lineage can be distinguished from independent nuclear information.

The machine-readable protocol is
`configs/physics/public_nuclear_rate_provenance_v1.yaml`; the deterministic
capture tool is `scripts/capture_public_nuclear_rate_provenance.py`.

## Included public collections

- LINX `key_PRIMAT_2023` and `key_recommended`;
- PRyMordial `key_nacreii_rates` and `key_primat_rates`;
- PRIMAT `primat` and `parthenope3.0` tables;
- ABCMB's bundled-LINX `key_PRIMAT_2023` tables.

Every collection must contain `d(p,gamma)3He`, `d(d,n)3He`, and `d(d,p)t`.
The initial capture therefore covers 21 tracked files across four exact source
commits.

## Scientific boundary

This is software/input provenance, not `NUC-v1` scientific provenance. A solver
repository distributing a table does not by itself establish the underlying
nuclear experiment version, covariance, normalization correlations, physical
units, temperature grid semantics, reverse-rate mapping, scalar uncertainty
envelope, or functional posterior. Byte-identical copies are not independent
rate libraries.

Consequently this work can narrow the provenance search and prevent accidental
double counting, but it cannot freeze a prior, authorize `RATE-F01`, or replace
A03/A00/A09 review. `NUC-v1` remains **NOT FROZEN**.

## Captured result

The exact-source capture at main `705d2e7` accepted all 21 registered tracked
files across the four frozen repositories. It found three byte-identical
content groups; these are recorded as copied-lineage evidence and not counted
as independent nuclear inputs. The complete machine-readable result is
`artifacts/provenance/PUBLIC-NUCLEAR-RATE-PROVENANCE-v1/capture-20260722T200435Z.json`.

This closes only the public solver-table hashing step. Underlying experiment
versions, units, covariance, correlation, detailed balance, functional bases
and scientific sign-offs remain open, so no `P2-rate-registry` progress credit
is assigned.
