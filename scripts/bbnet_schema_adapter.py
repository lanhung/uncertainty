#!/usr/bin/env python3
"""Fail-closed structural adapter for the audited public BBNet interfaces."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_REGISTRY = (
    Path(__file__).resolve().parents[1] / "configs/models/bbnet_interface_schema_v1.yaml"
)


class BBNetSchemaError(ValueError):
    """Raised when a public BBNet interface cannot be mapped without guessing."""


@dataclass(frozen=True)
class NormalizedBBNetRow:
    interface_id: str
    canonical: dict[str, float]
    unresolved: dict[str, float]
    approved_for_scientific_inference: bool


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    if registry.get("schema_id") != "BBNET-INTERFACES-v1":
        raise BBNetSchemaError("unexpected BBNet interface registry")
    return registry


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BBNetSchemaError(f"{name} must be a numeric scalar")
    converted = float(value)
    if not math.isfinite(converted):
        raise BBNetSchemaError(f"{name} must be finite")
    return converted


def _exact_row(row: Mapping[str, Any], columns: list[str], interface_id: str) -> None:
    missing = sorted(set(columns) - set(row))
    unknown = sorted(set(row) - set(columns))
    if missing or unknown:
        raise BBNetSchemaError(
            f"{interface_id} schema mismatch: missing={missing}, unknown={unknown}"
        )


def normalize_inputs(
    interface_id: str,
    row: Mapping[str, Any],
    registry: dict[str, Any] | None = None,
) -> NormalizedBBNetRow:
    """Normalize a source row while retaining every physically unresolved field."""
    registry = registry or load_registry()
    try:
        interface = registry["interfaces"][interface_id]
    except KeyError as exc:
        raise BBNetSchemaError(f"unknown BBNet interface: {interface_id}") from exc
    columns = interface["input_columns"]
    _exact_row(row, columns, interface_id)

    canonical: dict[str, float] = {}
    unresolved: dict[str, float] = {}
    for source_name in columns:
        value = _finite_number(source_name, row[source_name])
        target = interface["input_mapping"][source_name]["canonical"]
        if target is None:
            unresolved[source_name] = value
        elif target in canonical:
            raise BBNetSchemaError(f"duplicate canonical input mapping: {target}")
        else:
            canonical[target] = value
    return NormalizedBBNetRow(
        interface_id=interface_id,
        canonical=canonical,
        unresolved=unresolved,
        approved_for_scientific_inference=bool(interface["approved_for_scientific_inference"]),
    )


def materialize_inputs(
    interface_id: str,
    canonical: Mapping[str, Any],
    registry: dict[str, Any] | None = None,
) -> list[float]:
    """Create an ordered source row only when every physical mapping is registered."""
    registry = registry or load_registry()
    try:
        interface = registry["interfaces"][interface_id]
    except KeyError as exc:
        raise BBNetSchemaError(f"unknown BBNet interface: {interface_id}") from exc

    unresolved = [
        source_name
        for source_name, mapping in interface["input_mapping"].items()
        if mapping["canonical"] is None
    ]
    if unresolved:
        raise BBNetSchemaError(
            f"{interface_id} has unresolved physical mappings: {sorted(unresolved)}"
        )

    required = [
        interface["input_mapping"][source_name]["canonical"]
        for source_name in interface["input_columns"]
    ]
    missing = sorted(set(required) - set(canonical))
    unknown = sorted(set(canonical) - set(registry["canonical_inputs"]))
    if missing or unknown:
        raise BBNetSchemaError(f"canonical schema mismatch: missing={missing}, unknown={unknown}")
    return [_finite_number(name, canonical[name]) for name in required]


def normalize_outputs(
    interface_id: str,
    row: Mapping[str, Any],
    registry: dict[str, Any] | None = None,
) -> dict[str, float]:
    registry = registry or load_registry()
    try:
        interface = registry["interfaces"][interface_id]
    except KeyError as exc:
        raise BBNetSchemaError(f"unknown BBNet interface: {interface_id}") from exc
    columns = interface["output_columns"]
    _exact_row(row, columns, interface_id)
    return {
        interface["output_mapping"][source_name]: _finite_number(source_name, row[source_name])
        for source_name in columns
    }
