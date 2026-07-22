# ML4GW upstream audit v1

Status: source lineage registered; scientific validation incomplete

Captured: 2026-07-22

Manifest: `manifests/models/ml4gw_upstreams_v1.yaml`

## Registered repositories

The operator supplied two canonical project repositories. They are pinned as:

| Repository | Pinned revision | What it contributes now |
|---|---|---|
| `ML4GW/BBNet` | `9bd5147095f25fd8c6ac7cad30d78c71bcd3ece7` | Four MIT-licensed BBNet training/evaluation scripts and their exact preprocessing/architecture definitions |
| `ML4GW/SageNet` | `ab7face439b5ad47a8551d61e1a3fbdfd2d0ac55` | SageNet source, four SGWB checkpoints with embedded scalers, a 5,400-sample parameter-input corpus, and an exact stiffGWpy submodule revision |

The earlier `Hdiao112/BBNet` audit snapshot remains in place because it is a
different published lineage. It is not silently overwritten by the newer
ML4GW repository.

## BBNet finding

The ML4GW repository contains the actual PArthENoPE and AlterBBN training and
evaluation scripts. An exact source snapshot is stored at
`legacy/bbnet/ml4gw-9bd5147/` under the upstream MIT license. These scripts
establish the model class, feature names, preprocessing, test split behavior,
loss, and expected artifact formats.

They also expose unresolved interface defects. The file named
`mape_for_parthenope.py` expects AlterBBN-style feature/target names rather than
the schema emitted by `train_bbn_parthenope.py`. AlterBBN training uses
`dd0/dd0_rad`, while its evaluator expects `kappa10/DN_eff`; no conversion is
registered. Evaluators also load state dictionaries with `strict=False`.
These inconsistencies must be corrected and regression-tested against an
authoritative artifact, not guessed from parameter names.

The repository does **not** contain pretrained BBNet weights or scalers. The
tree entry named `weights` is a one-byte regular file, not the checkpoint
directory described in the README. All four reachable commits were inspected;
no model or data artifact is present in history. The README also retains TODO
placeholders for dependency versions and the data-release URL.

Consequently this source narrows, but does not clear, `P0-reproduce-bbnet`.
Reproduction still requires at least one attributable training dataset or an
approved data generator, plus the modified solver source or a documented
clean-room replacement. A paper checkpoint/scaler bundle would permit inference
recovery, but is not required if an exact retraining path is later established.

## SageNet finding

SageNet contains four real PyTorch ZIP checkpoints: CosmicNet2, LSTM, RNN, and
Transformer. Static archive inspection shows serialized `model_state`,
`x_scaler`, `y_scaler`, and `param_scaler` objects. The repository also contains
the model implementations and a 5,400-sample parameter-input JSON. The JSON
does not contain numerical spectra or interpolated targets, so it can exercise
inference inputs but cannot independently measure prediction error. Exact sizes
and SHA-256 values are frozen in the manifest; the binaries are fetched from
the pinned upstream rather than duplicated in this repository.

The checkpoint files contain pickle metadata. They must be treated as code:
verify commit and SHA-256 first, then load only in an isolated, unprivileged
environment. Upstream currently calls `torch.load(..., weights_only=False)`;
that call is not approved for the shared control host.

SageNet's `sagenetgw/stiffGWpy` is a separate GPL-3.0 submodule pinned at
`d6903d3f2552fc81f7de8f8765e9567766c4361e`. Its Cobaya wrapper expects an
external modified AlterBBN v2.2 executable. The solver source is therefore
still missing. The bundled LVK path is legacy O1--O3 lineage and cannot replace
the required current O1--O4a likelihood validation.

Two non-default DNN-UQ branches were also inspected. They change packaging and
documentation but do not contain the package, tests, or implementation claimed
by their README. Their performance claims remain unverified and are not an
allowed Track B baseline.

## Immediate use and remaining boundary

The repositories can now be used for:

- exact BBNet code migration and architecture/preprocessing audit;
- a SageNet legacy SGWB emulator baseline after isolated forward validation;
- reconstruction of old stiff-era/Cobaya parameter conventions;
- comparison of old and current likelihood/data interfaces;
- identification of the precise remaining handoff artifacts.

They cannot yet support:

- a reproduced BBNet accuracy or speed result;
- production BBN predictions;
- matched-physics PArthENoPE/AlterBBN comparisons;
- current LVK likelihood claims;
- any Nature-tier or novelty claim.

Use `scripts/fetch_ml4gw_upstreams.sh <persistent-external-dir>` to retrieve
both repositories at the registered commits and verify all material artifacts.
