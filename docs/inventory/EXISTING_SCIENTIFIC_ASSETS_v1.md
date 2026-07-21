# Existing scientific assets inventory v1

Status: complete for the locations and credentials available on 2026-07-21

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
| BBNet source or fork | 0 | No matching repository, branch, tag, or host path was found. |
| Project-specific PArthENoPE patches | 0 | No source tree, patch series, build directory, or solver card was found. |
| Project-specific AlterBBN patches | 0 | No source tree, patch series, build directory, or solver card was found. |
| LINX / PRyMordial / PRIMAT checkout | 0 | No existing checkout was found on the registered hosts. These remain external baselines to acquire reproducibly. |
| Existing BBN MCMC implementation | 0 | No matching project source, chain manifest, or checkpoint was found. |
| BBN training/validation data | 0 | No dataset manifest, approved solver shard, or checksum registry was found. |
| BBN trained models | 0 | No model card, checkpoint manifest, or attributable model artifact was found. |
| Operations/control-plane code | present | The repository contains the ledger, dashboard, heartbeat wrapper, worker bootstrap, resource lease, and topology documentation. |
| Westb worker inventory | present | Hardware inventory and the completed operations smoke test exist in project-scoped persistent storage; these are infrastructure artifacts, not scientific assets. |

## Repository-history finding

The repository history begins with governance and research-operations files.
All visible feature branches are also operations/topology branches. No earlier
scientific-code branch or release tag exists in the inspected remote.

## Migration decision

`P0-code-inventory` can close: the available asset set has been enumerated and
contains no scientific implementation to migrate. `P0-repo-migrate` must not
invent or silently substitute the missing project code. Its next valid inputs
are either:

1. an operator-provided path/archive/repository containing the original BBNet,
   MCMC, and modified solver sources; or
2. a separately registered clean-room baseline acquisition from the published
   upstream projects, with upstream commits, licenses, and local patches
   recorded explicitly.

Until one of these inputs exists, any newly written scientific implementation
is new work and must be labelled as such rather than represented as a migration.

## Reproduction notes

The inventory used read-only Git branch/tag/history inspection, authenticated
GitHub repository listing, and bounded filename searches on the registered
hosts. A repeated inventory must record its date and commit and append any newly
discovered source location instead of overwriting this result.
