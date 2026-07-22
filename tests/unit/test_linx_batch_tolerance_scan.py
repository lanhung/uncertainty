import pytest

from pathlib import Path

import yaml

from scripts.linx_batch_tolerance_scan import (
    absolute_differences,
    evaluate_scan,
    normalized_differences,
    observation_sigmas,
)


def abundances(yp: float, doh: float) -> dict[str, float]:
    return {
        "Neff": 3.045,
        "YPBBN": yp,
        "DoH": doh,
        "He3oH": 1.0e-5,
        "Li7oH": 5.0e-10,
    }


def case(scalar: dict[str, float], batch: dict[str, float], sigma_max: float) -> dict:
    return {
        "status": "ok",
        "scalar_abundances": scalar,
        "batch_abundances": batch,
        "maximum_scalar_batch_difference_observation_sigma": sigma_max,
        "maximum_repeat_drift": 0.0,
        "maximum_within_batch_spread": 0.0,
    }


def acceptance() -> dict:
    return {
        "candidate_case_ids": ["registered", "tight", "tighter"],
        "maximum_scalar_batch_difference_observation_sigma": 0.01,
        "maximum_plateau_difference_observation_sigma": 0.001,
        "tolerance_plateau_pair": ["tight", "tighter"],
        "sampling_plateau_pair": ["sampling_200", "sampling_300"],
        "require_zero_repeat_drift": True,
        "require_zero_within_batch_spread": True,
    }


def test_observation_normalization_uses_raw_abundance_units() -> None:
    observation = {
        "main_likelihood": {
            "helium4_mass_fraction": {"sigma": 0.0013},
            "deuterium_number_ratio": {"sigma": 0.030},
        }
    }
    sigmas = observation_sigmas(observation)
    left = abundances(0.246, 2.50e-5)
    right = abundances(0.2460013, 2.50003e-5)

    assert sigmas["YPBBN"] == 0.0013
    assert sigmas["DoH"] == pytest.approx(3.0e-7)
    assert normalized_differences(left, right, sigmas)["YPBBN"] == pytest.approx(0.001)
    assert normalized_differences(left, right, sigmas)["DoH"] == pytest.approx(0.001)
    assert absolute_differences(left, right)["He3oH"] == 0.0


def test_scan_pass_requires_batch_budget_and_both_plateaus() -> None:
    sigmas = {"YPBBN": 0.0013, "DoH": 3.0e-7}
    reference = abundances(0.246, 2.50e-5)
    batch = abundances(0.2460013, 2.50003e-5)
    cases = {
        "registered": case(reference, batch, 0.001),
        "tight": case(reference, batch, 0.001),
        "tighter": case(reference, batch, 0.001),
        "sampling_200": case(reference, batch, 0.001),
        "sampling_300": case(reference, batch, 0.001),
    }

    result = evaluate_scan(cases, acceptance(), sigmas)

    assert result["passed"] is True
    assert result["numerical_consistency_status"] == "accepted"
    assert result["plateaus"]["tolerance"]["passed"] is True
    assert result["plateaus"]["weak_rate_sampling"]["passed"] is True


def test_scan_rejects_a_missing_case_or_repeat_drift() -> None:
    sigmas = {"YPBBN": 0.0013, "DoH": 3.0e-7}
    reference = abundances(0.246, 2.50e-5)
    cases = {
        "registered": case(reference, reference, 0.0),
        "tight": case(reference, reference, 0.0),
        "tighter": case(reference, reference, 0.0),
        "sampling_200": case(reference, reference, 0.0),
    }
    cases["tight"]["maximum_repeat_drift"] = 1.0e-12

    result = evaluate_scan(cases, acceptance(), sigmas)

    assert result["passed"] is False
    assert result["all_required_cases_complete"] is False
    assert result["repeat_drift_pass"] is False
    assert result["plateaus"]["weak_rate_sampling"]["passed"] is False


def test_v2_extended_scan_keeps_v1_threshold_and_separates_axes() -> None:
    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load(
        (root / "configs/benchmarks/linx_extended_convergence_scan_v2.yaml").read_text()
    )
    cases = {case["id"]: case for case in config["cases"]}
    acceptance = config["acceptance"]

    assert config["parent_result"] == "complete_not_accepted"
    assert acceptance["maximum_plateau_difference_observation_sigma"] == 0.001
    assert cases["production_candidate"] == {
        "id": "production_candidate",
        "group": "joint_candidate",
        "rtol": 1.0e-8,
        "atol": 1.0e-11,
        "sampling_nTOp": 2400,
    }
    assert acceptance["tolerance_plateau_pair"] == [
        "tolerance_3e-8_sampling_2400",
        "production_candidate",
    ]
    assert acceptance["sampling_plateau_pair"] == [
        "sampling_1200_tolerance_1e-8",
        "production_candidate",
    ]


def test_v3_max_steps_diagnostic_keeps_strict_candidate_and_threshold() -> None:
    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load(
        (root / "configs/benchmarks/linx_max_steps_diagnostic_v3.yaml").read_text()
    )
    cases = {case["id"]: case for case in config["cases"]}

    assert config["parent_result"] == "complete_with_failures_not_accepted"
    assert config["acceptance"]["maximum_plateau_difference_observation_sigma"] == 0.001
    assert [cases[f"max_steps_{value}"]["max_steps"] for value in (8192, 16384, 32768)] == [
        8192,
        16384,
        32768,
    ]
    assert all(case["rtol"] == 1.0e-8 for case in cases.values())
    assert all(case["sampling_nTOp"] == 2400 for case in cases.values())
    assert config["acceptance"]["plateau_pairs"] == {
        "max_steps_invariance": ["max_steps_16384", "max_steps_32768"]
    }


def test_generic_plateau_pair_supports_max_steps_diagnostic() -> None:
    sigmas = {"YPBBN": 0.0013, "DoH": 3.0e-7}
    reference = abundances(0.246, 2.50e-5)
    batch = abundances(0.2460013, 2.50003e-5)
    cases = {
        "max_steps_16384": case(reference, batch, 0.001),
        "max_steps_32768": case(reference, batch, 0.001),
    }
    diagnostic_acceptance = {
        "candidate_case_ids": ["max_steps_16384", "max_steps_32768"],
        "maximum_scalar_batch_difference_observation_sigma": 0.01,
        "maximum_plateau_difference_observation_sigma": 0.001,
        "plateau_pairs": {"max_steps_invariance": ["max_steps_16384", "max_steps_32768"]},
        "require_zero_repeat_drift": True,
        "require_zero_within_batch_spread": True,
    }

    result = evaluate_scan(cases, diagnostic_acceptance, sigmas)

    assert result["passed"] is True
    assert result["plateaus"]["max_steps_invariance"]["passed"] is True
