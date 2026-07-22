#!/usr/bin/env python3
"""Register an incoming scientific asset without executing or deserializing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


DEFAULT_POLICY = (
    Path(__file__).resolve().parents[1] / "configs/inventory/scientific_asset_intake_v1.yaml"
)


class AssetIntakeError(ValueError):
    """Raised when an asset cannot be safely registered under the frozen policy."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_name(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    windows_drive = bool(path.parts and path.parts[0].endswith(":"))
    return not path.is_absolute() and not windows_drive and ".." not in path.parts


def inspect_archive(path: Path, member_limit: int) -> dict[str, Any]:
    """Inspect archive headers only; do not extract or deserialize payloads."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > member_limit:
                raise AssetIntakeError("archive member limit exceeded")
            unsafe = [
                member.filename for member in members if not _safe_member_name(member.filename)
            ]
            symlinks = [
                member.filename
                for member in members
                if stat.S_ISLNK((member.external_attr >> 16) & 0xFFFF)
            ]
            encrypted = [member.filename for member in members if member.flag_bits & 0x1]
        if unsafe or symlinks or encrypted:
            raise AssetIntakeError(
                f"unsafe zip metadata: traversal={unsafe}, symlinks={symlinks}, encrypted={encrypted}"
            )
        return {"format": "zip", "member_count": len(members), "safe_paths": True}

    if tarfile.is_tarfile(path):
        with tarfile.open(path, mode="r:*") as archive:
            members = archive.getmembers()
            if len(members) > member_limit:
                raise AssetIntakeError("archive member limit exceeded")
            unsafe = [member.name for member in members if not _safe_member_name(member.name)]
            links = [member.name for member in members if member.issym() or member.islnk()]
        if unsafe or links:
            raise AssetIntakeError(f"unsafe tar metadata: traversal={unsafe}, links={links}")
        return {"format": "tar", "member_count": len(members), "safe_paths": True}

    return {"format": "not_an_archive", "member_count": None, "safe_paths": None}


def _matches_suffix(path: Path, allowed: list[str]) -> bool:
    lowered = path.name.lower()
    return any(lowered.endswith(suffix.lower()) for suffix in allowed)


def inventory_asset(path: Path, forbidden_suffixes: list[str]) -> tuple[str, list[dict[str, Any]]]:
    if path.is_symlink():
        raise AssetIntakeError("asset symlinks are forbidden")
    if path.is_file():
        if _matches_suffix(path, forbidden_suffixes):
            raise AssetIntakeError("asset has a forbidden secret-bearing suffix")
        digest = sha256_file(path)
        return digest, [
            {"relative_path": path.name, "sha256": digest, "size_bytes": path.stat().st_size}
        ]
    if not path.is_dir():
        raise AssetIntakeError("asset must be a regular file or directory")

    entries: list[dict[str, Any]] = []
    for candidate in sorted(path.rglob("*")):
        if candidate.is_symlink():
            raise AssetIntakeError(f"directory contains symlink: {candidate.relative_to(path)}")
        if candidate.is_dir():
            continue
        if not candidate.is_file():
            raise AssetIntakeError(
                f"directory contains non-regular file: {candidate.relative_to(path)}"
            )
        relative = candidate.relative_to(path).as_posix()
        if _matches_suffix(candidate, forbidden_suffixes):
            raise AssetIntakeError(f"directory contains forbidden suffix: {relative}")
        digest = sha256_file(candidate)
        entries.append(
            {"relative_path": relative, "sha256": digest, "size_bytes": candidate.stat().st_size}
        )
    if not entries:
        raise AssetIntakeError("asset directory contains no regular files")
    tree = hashlib.sha256()
    for entry in entries:
        tree.update(
            f"{entry['relative_path']}\0{entry['size_bytes']}\0{entry['sha256']}\n".encode()
        )
    return tree.hexdigest(), entries


def register_asset(
    asset: Path,
    category: str,
    origin: str,
    license_name: str,
    relationship: str,
    expected_sha256: str | None = None,
    policy_path: Path = DEFAULT_POLICY,
) -> dict[str, Any]:
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    try:
        category_policy = policy["categories"][category]
    except KeyError as exc:
        raise AssetIntakeError(f"unknown asset category: {category}") from exc
    if asset.is_symlink():
        raise AssetIntakeError("asset symlinks are forbidden")
    asset = asset.resolve(strict=True)
    if asset.is_dir() and not category_policy["allow_directory"]:
        raise AssetIntakeError(f"directories are forbidden for category {category}")
    if asset.is_file() and not _matches_suffix(asset, category_policy["allowed_suffixes"]):
        raise AssetIntakeError(
            f"{asset.name} does not match allowed suffixes for category {category}"
        )
    if not origin.strip() or not license_name.strip() or not relationship.strip():
        raise AssetIntakeError("origin, license, and relationship must be non-empty")

    digest, files = inventory_asset(asset, policy["forbidden_suffixes"])
    if expected_sha256 is not None and digest.lower() != expected_sha256.lower():
        raise AssetIntakeError(f"checksum mismatch: {digest} != {expected_sha256}")
    archive = (
        inspect_archive(asset, int(policy["archive_member_limit"]))
        if asset.is_file()
        else {"format": "directory", "member_count": len(files), "safe_paths": True}
    )
    return {
        "schema_version": 1,
        "policy_id": policy["policy_id"],
        "registered_at_utc": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "asset_name": asset.name,
        "asset_kind": "directory" if asset.is_dir() else "file",
        "sha256": digest,
        "size_bytes": sum(item["size_bytes"] for item in files),
        "file_count": len(files),
        "files": files,
        "archive_inspection": archive,
        "provenance": {
            "origin": origin,
            "license": license_name,
            "relationship_to_project": relationship,
        },
        "status": policy["default_status"],
        "approved_for_scientific_inference": False,
        "approved_for_production": False,
        "next_review": category_policy["next_review"],
        "security": {
            "deserialization_performed": False,
            "execution_performed": False,
            "extraction_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--license", dest="license_name", required=True)
    parser.add_argument("--relationship", required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    args = parser.parse_args()

    resolved_asset = args.asset.resolve(strict=True)
    resolved_output = args.output.resolve(strict=False)
    if resolved_asset.is_dir() and resolved_asset in resolved_output.parents:
        raise AssetIntakeError("manifest output must be outside the asset directory")

    manifest = register_asset(
        args.asset,
        args.category,
        args.origin,
        args.license_name,
        args.relationship,
        args.expected_sha256,
        args.policy,
    )
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
