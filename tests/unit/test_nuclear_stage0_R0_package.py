from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from scripts.build_nuclear_stage0_R0_package import EXPECTED_REVISION, EXPECTED_TABLES


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "artifacts/priors/NUCLEAR-STAGE0-R0-LINX-KEY-RECOMMENDED-v1/package.json"


def load_package() -> dict:
    return json.loads(PACKAGE.read_text(encoding="utf-8"))


def test_package_is_pinned_to_the_exact_linx_source_and_three_r0_tables() -> None:
    package = load_package()

    assert package["source"]["revision"] == EXPECTED_REVISION
    assert package["source"]["tree"] == "dfb6290f5dc91079a147ed3e60944cc7bab50e14"
    assert set(package["reactions"]) == set(EXPECTED_TABLES)
    for reaction_id, expected in EXPECTED_TABLES.items():
        reaction = package["reactions"][reaction_id]
        assert reaction["source_sha256"] == expected["sha256"]
        assert reaction["source_git_blob"] == expected["git_blob"]
        assert reaction["linx_q_index"] == expected["q_index"]


def test_package_contains_positive_common_curves_and_log_factor_envelopes() -> None:
    package = load_package()
    grid = package["coordinate"]["grid"]

    assert len(grid) == 150
    assert grid[0] == 0.001
    assert grid[-1] == 10.0
    assert all(right > left for left, right in zip(grid, grid[1:]))
    for reaction in package["reactions"].values():
        assert len(reaction["central_rate"]) == len(grid)
        assert len(reaction["exp_sigma"]) == len(grid)
        assert len(reaction["log_sigma"]) == len(grid)
        assert all(value > 0 for value in reaction["central_rate"])
        assert all(value >= 1 for value in reaction["exp_sigma"])
        assert all(
            math.isclose(log_value, math.log(factor), rel_tol=0, abs_tol=1e-15)
            for factor, log_value in zip(reaction["exp_sigma"], reaction["log_sigma"])
        )


def test_package_keeps_scalar_and_covariance_limitations_machine_readable() -> None:
    package = load_package()

    assert package["status"] == "engineering_scalar_prior_scientific_signoff_pending"
    assert package["functional_posterior_boundary"]["included"] is False
    assert package["within_reaction_covariance"]["rank"] == 1
    assert package["cross_reaction_covariance"]["status"] == (
        "missing_not_evidence_of_independence"
    )
    assert package["interpolation"]["log_symmetric_transform_exact_only_at_table_knots"] is True


def test_package_bytes_are_stable() -> None:
    assert hashlib.sha256(PACKAGE.read_bytes()).hexdigest() == (
        "aacca2ad92c2132a67995801d091d9b642f3616cf7cf70b2a54a6e1d4348c745"
    )
