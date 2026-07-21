# Conversation-generated artifact audit

> Status: canonical source audit for `lanhung/uncertainty`  
> Repository visibility: public  
> Rule: repository-worthy source, configuration templates, tests and scientific governance belong in Git; live infrastructure inventory, credentials, private meeting material and reproducible delivery bundles do not.

## 1. Canonical content already represented in GitHub

The following conversation-generated work is present in canonical, editable form on `main`:

- `AGENTS.md` and the mandatory governance volumes under `docs/agents/`;
- `AGENTS-ops.md`;
- the BBN ODE compute decision and the shared-control/elastic-AutoDL decisions under `docs/decisions/`;
- the control plane, SQLite ledger, dashboard, `taskctl`, heartbeat wrapper and task DAG;
- Vultr, generic worker and AutoDL bootstrap scripts;
- node-specific SSH setup, host-level resource leases, worker inventory capture and operational tests;
- the shared Vultr + two elastic AutoDL runbook;
- sanitized local-inventory templates such as `deploy/hosts.local.env.example`.

These canonical files are the source of truth. A copied ZIP, concatenated Markdown snapshot or machine-specific wrapper must never override them.

## 2. Generated files intentionally not committed verbatim

The following files were generated during planning or delivery but must not be committed verbatim to this public repository:

| Generated artifact | Reason not committed verbatim | Canonical replacement |
|---|---|---|
| `AGENTS.full.v0.2.0.md` | generated concatenation; creates a second source of truth | root `AGENTS.md` plus `docs/agents/*.md` |
| `uncertainty_AGENTS_v0.2.0_bundle.zip` | binary delivery bundle; reproducible from source files | governance source files and a future tagged Release |
| `uncertainty_research_ops_main_3e1abe6.zip` | binary checkout snapshot; becomes stale immediately | Git commit history and tagged releases |
| `uncertainty_local_topology_bundle.zip` | contains live operational endpoints and is local-machine specific | `scripts/render_local_topology_bundle.py` plus a gitignored inventory |
| `hosts.local.env` | contains live Vultr/AutoDL endpoints and forwarded SSH ports | `deploy/hosts.local.env.example`; real file remains gitignored |
| `laptop_ssh_config.snippet` | contains the operator's live control endpoint and local key path | generated locally from the gitignored inventory |
| `bootstrap_autodl_westb.sh`, `bootstrap_autodl_bjb1.sh` | machine-specific convenience wrappers | generated locally; canonical logic lives in `scripts/bootstrap_autodl.sh` |
| meeting transcript and project PDF | private collaboration material; publication/authorisation not cleared | private source archive; only reviewed scientific decisions enter ADRs |

No bearer token, Tailscale auth key, password, SSH private key or collaboration-only result may be put into a generated bundle.

## 3. Reproduce the local topology files

On the shared Vultr control host:

```bash
cd /root/uncertainty
cp deploy/hosts.local.env.example deploy/hosts.local.env
chmod 600 deploy/hosts.local.env
$EDITOR deploy/hosts.local.env

python scripts/render_local_topology_bundle.py \
  --inventory deploy/hosts.local.env \
  --output-dir dist/uncertainty-local-topology \
  --archive dist/uncertainty_local_topology_bundle.zip
```

Or use:

```bash
make ops-local-bundle INVENTORY=deploy/hosts.local.env
```

The renderer accepts only an explicit allow-list of non-secret inventory fields. It rejects unknown fields, including attempted token/password/secret additions, and emits `SHA256SUMS` for the local files.

## 4. Upload policy

- Source and sanitized templates: commit through normal PR review.
- Live endpoints: keep in `deploy/hosts.local.env`, which is gitignored and mode `0600`.
- Credentials: keep only in project-scoped protected environment files or SSH key stores.
- Large immutable research artifacts: publish through approved object storage, Zenodo or a GitHub Release with checksums and manifests.
- Delivery ZIPs: create only from a tagged revision; do not store duplicate binary snapshots in ordinary Git history.
- Private source materials: upload only after explicit privacy, author and licence clearance.

## 5. Completion definition

For audit purposes, "uploaded to GitHub" means that every reusable and safe piece of work has a canonical source representation in the repository. It does **not** mean publishing live infrastructure details, credentials, private meeting records or duplicate binary bundles in a public repository.
