import pytest

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
