#!/usr/bin/env python3
"""Project-owned Stage-R0 reference-prior adapter utilities.

The module keeps prior construction independent of a particular solver
environment. Solver imports are supplied by the worker runner so the pure
contract and curve logic remain unit-testable on the control host.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_PROTOCOL_ID = "R0-REFERENCE-FAST-TRACK-v1"
EXPECTED_PRIOR_ID = "NUCLEAR-R0-REFERENCE-v1"


@dataclass(frozen=True)
class ReactionSpec:
    canonical_id: str
    native_id: str
    linx_q_index: int
    prymordial_constructor_index: int


REACTIONS = (
    ReactionSpec("dp_gamma_he3", "dpHe3g", 1, 1),
    ReactionSpec("dd_n_he3", "ddHe3n", 2, 2),
    ReactionSpec("dd_p_t", "ddtp", 3, 3),
)
REACTION_BY_CANONICAL = {reaction.canonical_id: reaction for reaction in REACTIONS}
REACTION_BY_NATIVE = {reaction.native_id: reaction for reaction in REACTIONS}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def git_revision(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def tracked_tree_clean(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"],
            cwd=path,
            check=False,
        ).returncode
        == 0
        and subprocess.run(
            ["git", "diff", "--cached", "--quiet", "HEAD", "--"],
            cwd=path,
            check=False,
        ).returncode
        == 0
    )


def validate_protocol(
    protocol: dict[str, Any],
    repository_root: Path,
) -> None:
    if (
        protocol.get("schema_version") != 1
        or protocol.get("protocol_id") != EXPECTED_PROTOCOL_ID
        or protocol.get("status") != "frozen_before_measurement"
    ):
        raise ValueError("fast-track protocol identity drift")
    boundary = protocol["claim_boundary"]
    for key in (
        "actual_ETR25_functional_posterior_reconstructed",
        "cross_reaction_covariance_inferred",
        "publication_prior_approved",
        "production_authorized",
        "final_cosmological_claim_allowed",
    ):
        if boundary.get(key) is not False:
            raise ValueError(f"fast-track claim overstatement: {key}")

    for source_id, source in protocol["frozen_inputs"].items():
        path = repository_root / source["path"]
        if not path.is_file():
            raise ValueError(f"missing frozen input: {source_id}")
        if sha256(path) != source["sha256"]:
            raise ValueError(f"frozen input hash drift: {source_id}")

    contract = protocol["canonical_contract"]
    if contract["coordinate_order"] != [
        "q_dp_gamma_he3",
        "q_dd_n_he3",
        "q_dd_p_t",
        "q_tau_n",
    ]:
        raise ValueError("canonical coordinate order drift")
    if contract["reaction_order"] != [reaction.canonical_id for reaction in REACTIONS]:
        raise ValueError("canonical reaction order drift")
    if contract["numeric_conversion"] != "identity_under_molar_mass_constant_convention":
        raise ValueError("rate-unit conversion drift")

    nodes = protocol["sigma_point_design"]["nodes"]
    if len(nodes) != 9 or len({node["id"] for node in nodes}) != 9:
        raise ValueError("sigma-point node identity drift")
    if any(len(node["q"]) != 4 for node in nodes):
        raise ValueError("sigma-point coordinate dimension drift")
    expected = {(0.0, 0.0, 0.0, 0.0)}
    for axis in range(4):
        for sign in (-1.0, 1.0):
            point = [0.0] * 4
            point[axis] = sign
            expected.add(tuple(point))
    if {tuple(float(value) for value in node["q"]) for node in nodes} != expected:
        raise ValueError("sigma-point design is not center plus symmetric axes")

    checks = protocol["plusminus_acceptance"]["check_ids"]
    if len(checks) != 12 or len(set(checks)) != 12:
        raise ValueError("plus/minus acceptance check set drift")


def validate_source_revision(
    source_dir: Path,
    expected_revision: str,
) -> None:
    revision = git_revision(source_dir)
    if revision != expected_revision:
        raise ValueError(f"solver revision drift: {revision} != {expected_revision}")
    if not tracked_tree_clean(source_dir):
        raise ValueError("solver source has tracked modifications")


def load_etr25_rows(package_path: Path) -> dict[str, list[dict[str, Any]]]:
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("package_id") != "ETR25-R0-TABLES-v1":
        raise ValueError("ETR25 table package identity drift")
    rows: dict[str, list[dict[str, Any]]] = {}
    for reaction in REACTIONS:
        records = package["reactions"][reaction.canonical_id]["rows"]
        t9 = [float(record["T9"]) for record in records]
        if (
            len(records) < 2
            or any(not math.isfinite(value) or value <= 0.0 for value in t9)
            or any(right <= left for left, right in zip(t9, t9[1:]))
        ):
            raise ValueError(f"invalid ETR25 temperature grid: {reaction.canonical_id}")
        for record in records:
            values = (
                float(record["low_p16"]),
                float(record["median_p50"]),
                float(record["high_p84"]),
                float(record["factor_uncertainty_lognormal"]),
            )
            if not all(math.isfinite(value) and value > 0.0 for value in values):
                raise ValueError(f"invalid ETR25 rate row: {reaction.canonical_id}")
            if not values[0] <= values[1] <= values[2]:
                raise ValueError(f"non-monotone ETR25 percentiles: {reaction.canonical_id}")
            if values[3] < 1.0:
                raise ValueError(f"invalid ETR25 factor uncertainty: {reaction.canonical_id}")
        rows[reaction.canonical_id] = records
    return rows


def representation_arrays(
    rows: dict[str, list[dict[str, Any]]],
    representation: str,
    canonical_id: str,
    q: float,
    *,
    z84: float = 0.9944578832097528,
) -> dict[str, list[float]]:
    if canonical_id not in REACTION_BY_CANONICAL:
        raise ValueError(f"unknown R0 reaction: {canonical_id}")
    records = rows[canonical_id]
    if representation == "R0_P2_legacy_solver_envelope":
        raise ValueError("legacy representation uses solver-native arrays")
    if representation not in {
        "R0_P0_ETR25_scalar_lognormal",
        "R0_P1_ETR25_asymmetric_quantile_rank1",
    }:
        raise ValueError(f"unsupported reference representation: {representation}")

    t9 = [float(record["T9"]) for record in records]
    median = [float(record["median_p50"]) for record in records]
    if representation == "R0_P0_ETR25_scalar_lognormal":
        exp_sigma = [float(record["factor_uncertainty_lognormal"]) for record in records]
    elif q < 0.0:
        exp_sigma = [
            math.exp(math.log(float(record["median_p50"]) / float(record["low_p16"])) / z84)
            for record in records
        ]
    else:
        exp_sigma = [
            math.exp(math.log(float(record["high_p84"]) / float(record["median_p50"])) / z84)
            for record in records
        ]
    return {"T9": t9, "median": median, "exp_sigma": exp_sigma}


def drawn_curve(arrays: dict[str, list[float]], q: float) -> list[float]:
    return [
        median * math.exp(q * math.log(exp_sigma))
        for median, exp_sigma in zip(arrays["median"], arrays["exp_sigma"])
    ]


def curve_manifest(
    rows: dict[str, list[dict[str, Any]]],
    representation: str,
    reaction_q: list[float],
) -> dict[str, Any]:
    if len(reaction_q) != len(REACTIONS):
        raise ValueError("R0 reaction-q vector must have length three")
    records: dict[str, Any] = {}
    for reaction, q in zip(REACTIONS, reaction_q):
        if representation == "R0_P2_legacy_solver_envelope":
            records[reaction.canonical_id] = {
                "native_id": reaction.native_id,
                "q": float(q),
                "source": "solver_native",
            }
            continue
        arrays = representation_arrays(
            rows,
            representation,
            reaction.canonical_id,
            float(q),
        )
        curve = drawn_curve(arrays, float(q))
        records[reaction.canonical_id] = {
            "T9_sha256": digest_json(arrays["T9"]),
            "curve_sha256": digest_json(curve),
            "exp_sigma_sha256": digest_json(arrays["exp_sigma"]),
            "knot_count": len(curve),
            "native_id": reaction.native_id,
            "q": float(q),
            "source": "ETR25_public_table",
        }
    return records


def linx_q_vector(reaction_q: list[float], vector_length: int = 12) -> list[float]:
    if len(reaction_q) != len(REACTIONS):
        raise ValueError("R0 reaction-q vector must have length three")
    vector = [0.0] * vector_length
    for reaction, q in zip(REACTIONS, reaction_q):
        vector[reaction.linx_q_index] = float(q)
    return vector


def prymordial_constructor_args(reaction_q: list[float]) -> list[float]:
    if len(reaction_q) != len(REACTIONS):
        raise ValueError("R0 reaction-q vector must have length three")
    vector = [0.0] * 12
    for reaction, q in zip(REACTIONS, reaction_q):
        vector[reaction.prymordial_constructor_index] = float(q)
    return vector


def tau_n_seconds(fiducial: dict[str, Any], q_tau_n: float) -> float:
    value = float(fiducial["tau_n_seconds"]) + float(q_tau_n) * float(
        fiducial["tau_n_sigma_seconds"]
    )
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("invalid neutron lifetime draw")
    return value


def patch_linx_network(
    modules: dict[str, Any],
    rows: dict[str, list[dict[str, Any]]],
    representation: str,
    reaction_q: list[float],
) -> Any:
    """Construct a LINX network with project-owned ETR25 arrays.

    The native network is never edited on disk. Only the three R0 Reaction
    objects are replaced in memory, after which LINX rebuilds its forward and
    reverse callable dictionaries from the same objects.
    """

    network = modules["NuclearRates"](nuclear_net="key_recommended", interp_type="linear")
    if representation == "R0_P2_legacy_solver_envelope":
        return network
    if len(reaction_q) != len(REACTIONS):
        raise ValueError("R0 reaction-q vector must have length three")
    jnp = modules["jnp"]
    q_by_native = {reaction.native_id: float(q) for reaction, q in zip(REACTIONS, reaction_q)}
    for reaction in network.reactions:
        specification = REACTION_BY_NATIVE.get(reaction.name)
        if specification is None:
            continue
        arrays = representation_arrays(
            rows,
            representation,
            specification.canonical_id,
            q_by_native[reaction.name],
        )
        object.__setattr__(reaction, "T9_vec", jnp.asarray(arrays["T9"], dtype=jnp.float64))
        object.__setattr__(
            reaction,
            "mu_median_vec",
            jnp.asarray(arrays["median"], dtype=jnp.float64),
        )
        object.__setattr__(
            reaction,
            "expsigma_vec",
            jnp.asarray(arrays["exp_sigma"], dtype=jnp.float64),
        )
        object.__setattr__(reaction, "interp_type", "linear")
    return modules["NuclearRates"](
        reactions=network.reactions,
        interp_type="linear",
        max_i_species=network.max_i_species,
    )


def install_prymordial_arrays(
    init: Any,
    rows: dict[str, list[dict[str, Any]]],
    representation: str,
    reaction_q: list[float],
) -> dict[str, Any]:
    """Install ETR25 arrays in PRyMordial globals and return a restore record."""

    if representation == "R0_P2_legacy_solver_envelope":
        return {}
    if len(reaction_q) != len(REACTIONS):
        raise ValueError("R0 reaction-q vector must have length three")
    import numpy as np

    saved: dict[str, Any] = {}
    for reaction, q in zip(REACTIONS, reaction_q):
        arrays = representation_arrays(
            rows,
            representation,
            reaction.canonical_id,
            float(q),
        )
        for suffix, values in (
            ("T9", arrays["T9"]),
            ("median", arrays["median"]),
            ("expsigma", arrays["exp_sigma"]),
        ):
            name = f"{reaction.native_id}_{suffix}"
            saved[name] = getattr(init, name)
            setattr(init, name, np.asarray(values, dtype=np.float64))
    return saved


def restore_prymordial_arrays(init: Any, saved: dict[str, Any]) -> None:
    for name, value in saved.items():
        setattr(init, name, value)
