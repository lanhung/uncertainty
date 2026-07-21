#!/usr/bin/env python3
"""Render operator-local topology helpers from a gitignored inventory.

The input is intentionally restricted to a fixed allow-list of non-secret host
metadata.  Tokens, passwords, Tailscale auth keys and private-key material are
rejected instead of being copied into an archive accidentally.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import stat
import sys
import zipfile
from pathlib import Path
from typing import Iterable

PROJECT_KEYS = (
    "PROJECT_SLUG",
    "PROJECT_PORT",
    "CONTROL_SSH_ALIAS",
    "CONTROL_PUBLIC_HOST",
    "CONTROL_SSH_PORT",
    "CONTROL_SSH_USER",
    "AUTODL1_ALIAS",
    "AUTODL1_HOST",
    "AUTODL1_PORT",
    "AUTODL1_USER",
    "AUTODL1_NODE_NAME",
    "AUTODL1_REGION",
    "AUTODL2_ALIAS",
    "AUTODL2_HOST",
    "AUTODL2_PORT",
    "AUTODL2_USER",
    "AUTODL2_NODE_NAME",
    "AUTODL2_REGION",
    "AUTODL_KEY_DIR",
)
ALLOWED_KEYS = frozenset(PROJECT_KEYS)
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.:-]{0,252}$")


class InventoryError(ValueError):
    """Raised when the local inventory is unsafe or malformed."""


def _decode_value(raw: str, *, line_number: int) -> str:
    try:
        parts = shlex.split(raw, comments=False, posix=True)
    except ValueError as exc:
        raise InventoryError(f"line {line_number}: invalid shell quoting: {exc}") from exc
    if len(parts) != 1:
        raise InventoryError(
            f"line {line_number}: values must be one literal shell token, got {raw!r}"
        )
    return parts[0]


def load_inventory(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise InventoryError(f"inventory does not exist: {path}")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise InventoryError(f"line {line_number}: expected KEY=VALUE")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_KEYS:
            raise InventoryError(
                f"line {line_number}: field {key!r} is not allowed in a local topology bundle"
            )
        if key in values:
            raise InventoryError(f"line {line_number}: duplicate field {key}")
        values[key] = _decode_value(raw_value.strip(), line_number=line_number)

    missing = [key for key in PROJECT_KEYS if not values.get(key)]
    if missing:
        raise InventoryError("missing required fields: " + ", ".join(missing))
    validate_inventory(values)
    return values


def _validate_port(values: dict[str, str], key: str) -> None:
    try:
        port = int(values[key])
    except ValueError as exc:
        raise InventoryError(f"{key} must be an integer") from exc
    if not 1 <= port <= 65535:
        raise InventoryError(f"{key} must be between 1 and 65535")


def validate_inventory(values: dict[str, str]) -> None:
    if not SLUG_RE.fullmatch(values["PROJECT_SLUG"]):
        raise InventoryError("PROJECT_SLUG has an invalid value")
    for key in ("PROJECT_PORT", "CONTROL_SSH_PORT", "AUTODL1_PORT", "AUTODL2_PORT"):
        _validate_port(values, key)
    for key in (
        "CONTROL_SSH_ALIAS",
        "CONTROL_SSH_USER",
        "AUTODL1_ALIAS",
        "AUTODL1_USER",
        "AUTODL1_NODE_NAME",
        "AUTODL1_REGION",
        "AUTODL2_ALIAS",
        "AUTODL2_USER",
        "AUTODL2_NODE_NAME",
        "AUTODL2_REGION",
    ):
        if not NAME_RE.fullmatch(values[key]):
            raise InventoryError(f"{key} contains unsupported characters")
    for key in ("CONTROL_PUBLIC_HOST", "AUTODL1_HOST", "AUTODL2_HOST"):
        if not HOST_RE.fullmatch(values[key]):
            raise InventoryError(f"{key} is not a simple host/IP literal")
    key_dir = Path(values["AUTODL_KEY_DIR"])
    if not key_dir.is_absolute() or ".." in key_dir.parts:
        raise InventoryError("AUTODL_KEY_DIR must be an absolute path without '..'")


def normalized_inventory(values: dict[str, str]) -> str:
    lines = [
        "# LOCAL OPERATIONAL INVENTORY — DO NOT COMMIT",
        "# Generated from a gitignored source; contains no passwords, tokens or private keys.",
    ]
    sections = (
        ("PROJECT_SLUG", "PROJECT_PORT"),
        (
            "CONTROL_SSH_ALIAS",
            "CONTROL_PUBLIC_HOST",
            "CONTROL_SSH_PORT",
            "CONTROL_SSH_USER",
        ),
        (
            "AUTODL1_ALIAS",
            "AUTODL1_HOST",
            "AUTODL1_PORT",
            "AUTODL1_USER",
            "AUTODL1_NODE_NAME",
            "AUTODL1_REGION",
        ),
        (
            "AUTODL2_ALIAS",
            "AUTODL2_HOST",
            "AUTODL2_PORT",
            "AUTODL2_USER",
            "AUTODL2_NODE_NAME",
            "AUTODL2_REGION",
        ),
        ("AUTODL_KEY_DIR",),
    )
    for section in sections:
        lines.append("")
        lines.extend(f"{key}={shlex.quote(values[key])}" for key in section)
    return "\n".join(lines) + "\n"


def laptop_ssh_config(values: dict[str, str]) -> str:
    alias = values["CONTROL_SSH_ALIAS"]
    return f"""Host {alias}
  HostName {values['CONTROL_PUBLIC_HOST']}
  Port {values['CONTROL_SSH_PORT']}
  User {values['CONTROL_SSH_USER']}
  IdentityFile ~/.ssh/id_ed25519_research_vultr
  IdentitiesOnly yes
  ForwardAgent no
  ServerAliveInterval 30
  ServerAliveCountMax 6
  ControlMaster auto
  ControlPersist 10m
  ControlPath ~/.ssh/cm-%C
"""


def autodl_wrapper(values: dict[str, str], prefix: str) -> str:
    node_name = values[f"{prefix}_NODE_NAME"]
    region = values[f"{prefix}_REGION"]
    project = values["PROJECT_SLUG"]
    port = values["PROJECT_PORT"]
    return f"""#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${{CONTROL_TAILNET_IP:?Export CONTROL_TAILNET_IP from 'tailscale ip -4' on Vultr first}}"

PROJECT={shlex.quote(project)}
REPO_DIR="/root/autodl-tmp/projects/${{PROJECT}}/repo"
mkdir -p "$(dirname "$REPO_DIR")"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone https://github.com/lanhung/uncertainty.git "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" pull --ff-only
fi
cd "$REPO_DIR"

# Leave empty when the physical node already has a persistent host-level identity.
read -r -s -p 'Tailscale auth key (optional): ' TAILSCALE_AUTHKEY
echo
export TAILSCALE_AUTHKEY

CONTROL_TAILNET_IP="$CONTROL_TAILNET_IP" \\
RESEARCH_OPS_PROJECT="$PROJECT" \\
RESEARCH_OPS_PORT={shlex.quote(port)} \\
AUTODL_NODE_NAME={shlex.quote(node_name)} \\
AUTODL_REGION={shlex.quote(region)} \\
WORKER_ROLE=elastic \\
WORKER_INDEX={'1' if prefix == 'AUTODL1' else '2'} \\
bash scripts/bootstrap_autodl.sh

unset TAILSCALE_AUTHKEY
"""


def local_readme(values: dict[str, str], generated_names: Iterable[str]) -> str:
    names = "\n".join(f"- `{name}`" for name in generated_names)
    return f"""# Local topology files for `{values['PROJECT_SLUG']}`

These files are operator-local deployment helpers. They contain live host
endpoints but no password, bearer token, Tailscale auth key or SSH private key.
Do not commit them to the public repository.

Generated files:

{names}

Recommended installation on the shared Vultr host:

```bash
install -m 600 hosts.local.env \\
  /root/{values['PROJECT_SLUG']}/deploy/hosts.local.env
cd /root/{values['PROJECT_SLUG']}
bash scripts/setup_control_autodl_ssh.sh \\
  --inventory deploy/hosts.local.env
bash scripts/setup_control_autodl_ssh.sh \\
  --inventory deploy/hosts.local.env --install
```

The bootstrap wrappers still prompt securely for runtime credentials. Never add
a token, password, auth key or private-key body to `hosts.local.env`.
"""


def write_text(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, mode)
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_archive(archive: Path, files: list[Path], root: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_name(archive.name + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(files, key=lambda item: item.name):
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IMODE(path.stat().st_mode) & 0xFFFF) << 16
            bundle.writestr(info, path.read_bytes())
    temporary.replace(archive)


def render(inventory: Path, output_dir: Path, archive: Path, *, force: bool) -> dict[str, str]:
    values = load_inventory(inventory)
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise InventoryError(
            f"output directory is not empty: {output_dir}; pass --force to replace generated files"
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    generated: dict[str, tuple[str, int]] = {
        "hosts.local.env": (normalized_inventory(values), 0o600),
        "laptop_ssh_config.snippet": (laptop_ssh_config(values), 0o600),
        f"bootstrap_{values['AUTODL1_NODE_NAME']}.sh": (autodl_wrapper(values, "AUTODL1"), 0o700),
        f"bootstrap_{values['AUTODL2_NODE_NAME']}.sh": (autodl_wrapper(values, "AUTODL2"), 0o700),
    }
    readme_names = [*generated, "README_LOCAL.md", "SHA256SUMS"]
    generated["README_LOCAL.md"] = (local_readme(values, readme_names), 0o600)

    for name, (content, mode) in generated.items():
        write_text(output_dir / name, content, mode)

    sums = "".join(
        f"{sha256(output_dir / name)}  {name}\n" for name in sorted(generated)
    )
    write_text(output_dir / "SHA256SUMS", sums, 0o600)
    files = [output_dir / name for name in [*generated, "SHA256SUMS"]]
    create_archive(archive, files, output_dir)
    return {
        "archive": str(archive),
        "archive_sha256": sha256(archive),
        "output_dir": str(output_dir),
        "project": values["PROJECT_SLUG"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=Path("deploy/hosts.local.env"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist/uncertainty-local-topology"),
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("dist/uncertainty_local_topology_bundle.zip"),
    )
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = render(args.inventory, args.output_dir, args.archive, force=args.force)
    except InventoryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
