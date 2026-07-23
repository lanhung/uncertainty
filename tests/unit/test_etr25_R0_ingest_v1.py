from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.validate_etr25_R0_ingest_v1 import validate


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/physics/etr25_R0_ingest_v1.yaml"
STAGE = ROOT / "configs/physics/nuclear_stage0_R0_v1.yaml"
PACKAGE = ROOT / "artifacts/priors/ETR25-R0-TABLES-v1/package.json"


def test_official_public_product_ingest_validates_without_unlocking_production() -> None:
    assert validate(REGISTRY, STAGE, ROOT) == {
        "reactions": 3,
        "temperature_knots_per_reaction": 60,
        "table_rows": 180,
        "high_temperature_matched_rows": 26,
        "production_enabled_reactions": 0,
    }


def test_package_is_pinned_to_registry_hash() -> None:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    digest = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()

    assert digest == registry["derived_package"]["sha256"]


def test_actual_percentiles_are_not_the_lognormal_approximation() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))

    for reaction in package["reactions"].values():
        assert reaction["percentile_semantics"]["source"] == "actual_rate_probability_density"
        assert reaction["factor_uncertainty_semantics"]["model"] == "lognormal_approximation"
        assert (
            reaction["factor_uncertainty_semantics"]["not_derived_directly_from_actual_percentiles"]
            is True
        )


def test_validator_rejects_invented_cross_reaction_independence(
    tmp_path: Path,
) -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    package["source_boundary"]["missing_covariance_is_independence_evidence"] = True
    bad_package = tmp_path / "package.json"
    bad_package.write_text(json.dumps(package), encoding="utf-8")

    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    registry["derived_package"]["path"] = str(bad_package)
    registry["derived_package"]["sha256"] = hashlib.sha256(bad_package.read_bytes()).hexdigest()
    bad_registry = tmp_path / "registry.yaml"
    bad_registry.write_text(yaml.safe_dump(registry), encoding="utf-8")

    with pytest.raises(ValueError, match="evidence boundary"):
        validate(bad_registry, STAGE, ROOT)
