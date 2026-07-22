# BBNet legacy audit import

This directory preserves the MIT-licensed text of the BBNet package at upstream
commit `ea66fe66b16d5189676a853337aaa5ae480839b0`. It is an audit input, not an
installable or scientifically approved model.

Do not import this directory into production code. The upstream snapshot lacks
loadable checkpoints and training data and contains known packaging/artifact-name
defects. Exact provenance, missing artifacts, rejected historical artifacts and
the reproduction gate are recorded in:

- `manifests/models/bbnet_legacy_upstream_v1.yaml`;
- `configs/models/bbnet_legacy_v1.yaml`.

The two training scripts visible only in deleted upstream history are not copied
here because the repository's MIT license is nested under `BBNet/` and does not
unambiguously cover root-level files. Their commits, Git blob IDs and hashes are
recorded in the manifest for provenance and possible author clarification.
