# Scientific asset handoff

Incoming solver source, BBNet weights/scalers, labeled data, generation scripts,
and MCMC/likelihood assets enter the project in quarantine. Registration records
their content hash and provenance but never executes or deserializes them.

Example:

```bash
python scripts/register_scientific_asset.py \
  --asset /path/to/uploaded/file.pth \
  --category bbnet_checkpoint \
  --origin 'operator handoff; original author/source to be recorded' \
  --license 'unknown_pending_review' \
  --relationship 'candidate BBNet paper checkpoint' \
  --expected-sha256 '<checksum if supplied out of band>' \
  --output /root/autodl-fs/projects/uncertainty/quarantine/manifests/checkpoint.json
```

Use the category names in
`configs/inventory/scientific_asset_intake_v1.yaml`. Prefer source archives or
clean directories without `.git`, secrets, symlinks, sockets, or device files.
The tool rejects archive traversal, archive links, encrypted ZIP entries,
forbidden secret-bearing suffixes, checksum mismatches, and undeclared file
types. It does not copy or extract the asset.

Every new manifest starts with:

```text
status: quarantined_unreviewed
approved_for_scientific_inference: false
approved_for_production: false
```

Category-specific review is still mandatory. In particular, PyTorch/pickle/
joblib files must be reviewed in an isolated environment, source must receive a
license and revision audit, and data must receive schema, units, provenance,
split, duplication, and label-solver review. Only those later review artifacts
may change acceptance state.
