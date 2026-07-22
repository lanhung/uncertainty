# Existing scientific assets inventory v1

Status: amended after ML4GW canonical-upstream discovery on 2026-07-22

Task: `P0-code-inventory`

Inventory commit: `634abdf9271606c3173fb7823125d785c2c749cc`

## Purpose and scope

This inventory determines whether pre-existing BBNet, MCMC, BBN solver patch,
scientific data, or trained-model assets are available to migrate into this
repository. It is an asset-discovery record, not evidence that absent assets do
not exist outside the inspected locations.

The following locations were inspected without modifying unrelated projects:

- every local and remote branch and tag of `lanhung/uncertainty`;
- the current Vultr checkout and filename matches under `/root` for BBNet,
  PArthENoPE, AlterBBN, LINX, PRyMordial, PRIMAT, and MCMC terms;
- the three registered AutoDL workers, using the same bounded filename search;
- repositories visible to the authenticated `lanhung` GitHub account.

Live SSH endpoints, passwords, tokens, private keys, and unrelated-project file
names are deliberately excluded from this document.

## Results

| Asset class | Located | Evidence and interpretation |
|---|---:|---|
| BBNet source or fork | 2 public upstream lineages | No project-owned copy was found in the original scope. Later audits located `Hdiao112/BBNet` and the operator-identified canonical `ML4GW/BBNet`; see the amendments below. |
| Project-specific PArthENoPE patches | 0 | No source tree, patch series, build directory, or solver card was found. |
| Project-specific AlterBBN patches | 0 | No source tree, patch series, build directory, or solver card was found. |
| LINX / PRyMordial / PRIMAT checkout | 0 | No existing checkout was found on the registered hosts. These remain external baselines to acquire reproducibly. |
| Existing BBN MCMC implementation | 0 | No matching project source, chain manifest, or checkpoint was found. |
| BBN training/validation data | 0 | No dataset manifest, approved solver shard, or checksum registry was found. |
| BBN trained models | 0 | No attributable BBNet checkpoint was found. SageNet has separate SGWB checkpoints, not BBN abundance checkpoints. |
| SGWB trained models | 4 public upstream checkpoints | `ML4GW/SageNet` provides CosmicNet2, LSTM, RNN and Transformer checkpoints with embedded scalers plus 5,400 parameter-only test inputs; target spectra and forward validation are pending. |
| Operations/control-plane code | present | The repository contains the ledger, dashboard, heartbeat wrapper, worker bootstrap, resource lease, and topology documentation. |
| Westb worker inventory | present | Hardware inventory and the completed operations smoke test exist in project-scoped persistent storage; these are infrastructure artifacts, not scientific assets. |

## Repository-history finding

The repository history begins with governance and research-operations files.
All visible feature branches are also operations/topology branches. No earlier
scientific-code branch or release tag exists in the inspected remote.

## Migration decision

`P0-code-inventory` can close: the available asset set has been enumerated and
contained no project-owned scientific implementation to migrate.
`P0-repo-migrate` must not invent or silently substitute missing project code.
Its valid inputs are either:

1. an operator-provided path/archive/repository containing the original BBNet,
   MCMC, and modified solver sources; or
2. a separately registered clean-room baseline acquisition from the published
   upstream projects, with upstream commits, licenses, and local patches
   recorded explicitly.

Until one of these inputs exists, any newly written scientific implementation
is new work and must be labelled as such rather than represented as a migration.

## Amendment: published BBNet upstream

A follow-up audit of the BBNet paper source located the explicitly cited public
repository `https://github.com/Hdiao112/BBNet`. This repository was outside the
original account-owned repository listing, so the original negative result is
retained as a scoped observation rather than deleted.

The repository provides a nested MIT-licensed package at commit
`ea66fe66b16d5189676a853337aaa5ae480839b0`. Its history also contains two
training scripts at commit `704274c780f91f7e090d478f1a4f03a8ff933df9` that
were later deleted. The licensed package text has been imported under
`legacy/bbnet/` with normalized line endings. The two root-level training
scripts are recorded by commit, blob and checksum but not redistributed because
the nested MIT license does not unambiguously cover them.

The import is not a scientific reproduction. The current upstream commit has no
checkpoints; no PArthENoPE checkpoint exists in reachable history; and the only
historical AlterBBN checkpoint is an exactly 5 MiB truncated PyTorch ZIP without
a central directory. Training data, split indices, solver commits and a complete
training configuration are also absent. The import is therefore marked
`non_runnable_audit_import` and cannot support inference or claims.

Machine-readable details are in:

- `manifests/models/bbnet_legacy_upstream_v1.yaml`;
- `configs/models/bbnet_legacy_v1.yaml`.

## Amendment: operator-identified ML4GW repositories

On 2026-07-22 the operator identified `https://github.com/ML4GW/BBNet` and
`https://github.com/ML4GW/SageNet` as canonical project repositories. They were
audited at fixed commits and registered in
`manifests/models/ml4gw_upstreams_v1.yaml`; the full assessment is in
`docs/inventory/ML4GW_UPSTREAM_AUDIT_v1.md`.

`ML4GW/BBNet` supplies four MIT-licensed training/evaluation scripts and has
been imported exactly at commit `9bd5147095f25fd8c6ac7cad30d78c71bcd3ece7`.
It does not supply the advertised weights: `weights` is a one-byte regular
file, and no checkpoint, scaler or dataset exists in reachable history.

`ML4GW/SageNet` supplies four real SGWB checkpoint/scaler bundles, model source,
and a 5,400-sample parameter-input corpus at commit
`ab7face439b5ad47a8551d61e1a3fbdfd2d0ac55`. The JSON contains parameters but
not target spectra. Its pinned stiffGWpy submodule is
GPL-3.0 and still expects an external modified AlterBBN executable. These
assets advance the legacy SGWB baseline but do not clear the missing BBN solver
or BBNet data/checkpoint blockers.

## Reproduction notes

The inventory used read-only Git branch/tag/history inspection, authenticated
GitHub repository listing, and bounded filename searches on the registered
hosts. A repeated inventory must record its date and commit and append any newly
discovered source location instead of overwriting this result.
