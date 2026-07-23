#!/usr/bin/env python3
"""Validate a frozen PRyMordial native abundance-UQ reproduction directory."""

from __future__ import annotations

import argparse
import json
import math
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.run_prymordial_native_uq_reproduction import (
        DEFAULT_PROTOCOL,
        EXPECTED_PROTOCOL_ID,
        EXPECTED_REVISION,
        EXPECTED_TASK_ID,
        OUTPUT_FILENAMES,
        RATE_PARAMETER_NAMES,
        add_record_digest,
        digest_json,
        draw_manifest_digest,
        generate_draw_manifest,
        load_jsonl,
        load_protocol,
        relative_drift,
        sha256,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from run_prymordial_native_uq_reproduction import (  # type: ignore[no-redef]
        DEFAULT_PROTOCOL,
        EXPECTED_PROTOCOL_ID,
        EXPECTED_REVISION,
        EXPECTED_TASK_ID,
        OUTPUT_FILENAMES,
        RATE_PARAMETER_NAMES,
        add_record_digest,
        digest_json,
        draw_manifest_digest,
        generate_draw_manifest,
        load_jsonl,
        load_protocol,
        relative_drift,
        sha256,
    )


def load_digest_json(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    stored = value.pop("evidence_sha256", None)
    if not isinstance(stored, str) or digest_json(value) != stored:
        raise ValueError(f"{label} evidence digest mismatch")
    value["evidence_sha256"] = stored
    return value


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def validate_runtime_environment(protocol: dict[str, Any]) -> None:
    expected = protocol["environment"]
    if platform.python_version() != expected["python"]:
        raise RuntimeError(
            f"validator Python drift: {platform.python_version()} != {expected['python']}"
        )
    if np.__version__ != expected["numpy"]:
        raise RuntimeError(f"validator NumPy drift: {np.__version__} != {expected['numpy']}")


def assert_exact_keys(record: dict[str, Any], expected: set[str], label: str) -> None:
    if set(record) != expected:
        raise ValueError(f"{label} field set drift: {sorted(set(record) ^ expected)}")


def bootstrap_sigma_interval(
    values: np.ndarray,
    *,
    seed: int,
    resamples: int,
    quantiles: tuple[float, float],
) -> list[float]:
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    standard_deviations = np.empty(resamples, dtype=np.float64)
    for start in range(0, resamples, 256):
        stop = min(start + 256, resamples)
        indices = generator.integers(0, len(values), size=(stop - start, len(values)))
        standard_deviations[start:stop] = np.std(values[indices], axis=1, ddof=1)
    try:
        result = np.quantile(standard_deviations, quantiles, method="linear")
    except TypeError:  # NumPy < 1.22, used only by lightweight local tests.
        result = np.quantile(standard_deviations, quantiles, interpolation="linear")
    return [float(value) for value in result]


def validate_run_manifest(
    manifest: dict[str, Any],
    *,
    protocol_path: Path,
    protocol: dict[str, Any],
    draws: list[dict[str, Any]],
) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "task_id",
        "run_id",
        "config_path",
        "config_sha256",
        "source",
        "environment",
        "draw_manifest_sha256",
        "output_files",
        "created_at_utc",
        "evidence_sha256",
    }
    assert_exact_keys(manifest, required, "run manifest")
    if manifest["schema_version"] != 1:
        raise ValueError("run manifest schema drift")
    if manifest["protocol_id"] != EXPECTED_PROTOCOL_ID:
        raise ValueError("run manifest protocol identity drift")
    if manifest["task_id"] != EXPECTED_TASK_ID:
        raise ValueError("run manifest task identity drift")
    if manifest["config_sha256"] != sha256(protocol_path):
        raise ValueError("run manifest protocol digest drift")
    if manifest["output_files"] != OUTPUT_FILENAMES:
        raise ValueError("run manifest output contract drift")
    if manifest["draw_manifest_sha256"] != draw_manifest_digest(draws):
        raise ValueError("run manifest draw-manifest digest drift")
    expected_run_id = digest_json(
        {
            "protocol_sha256": sha256(protocol_path),
            "source_revision": EXPECTED_REVISION,
            "draw_manifest_sha256": manifest["draw_manifest_sha256"],
        }
    )
    if manifest["run_id"] != expected_run_id:
        raise ValueError("run identity drift")
    try:
        datetime.fromisoformat(manifest["created_at_utc"])
    except (TypeError, ValueError) as error:
        raise ValueError("run creation timestamp is invalid") from error

    source = manifest["source"]
    configured_source = protocol["source"]
    if source["repository"] != configured_source["repository"]:
        raise ValueError("source repository drift")
    if source["revision"] != configured_source["revision"]:
        raise ValueError("source revision drift")
    if source["license"] != configured_source["license"]:
        raise ValueError("source license drift")
    if source["tracked_worktree_matches_HEAD"] is not True:
        raise ValueError("source worktree provenance was not clean")
    expected_hashes = {
        relative: details["sha256"]
        for relative, details in configured_source["required_files"].items()
    }
    if source["required_file_sha256"] != expected_hashes:
        raise ValueError("source file provenance drift")

    environment = manifest["environment"]
    configured_environment = protocol["environment"]
    for name in ("python", "numpy", "scipy", "precision", "backend"):
        if environment.get(name) != configured_environment[name]:
            raise ValueError(f"recorded environment drift: {name}")
    if environment.get("lock_path") != configured_environment["lock_path"]:
        raise ValueError("recorded environment lock path drift")
    if environment.get("lock_sha256") != configured_environment["lock_sha256"]:
        raise ValueError("recorded environment lock digest drift")
    if not isinstance(environment.get("platform"), str) or not environment["platform"]:
        raise ValueError("recorded platform is missing")


def validate_draws(
    draws: list[dict[str, Any]], protocol: dict[str, Any]
) -> dict[int, dict[str, Any]]:
    expected = generate_draw_manifest(protocol)
    if draws != expected:
        raise ValueError("draw manifest does not reproduce the frozen seed contract")
    by_id = {int(record["draw_id"]): record for record in draws}
    if len(by_id) != len(draws):
        raise ValueError("draw manifest IDs are not unique")
    return by_id


def validate_terminal_records(
    results: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    draws: dict[int, dict[str, Any]],
    protocol: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result_fields = {
        "schema_version",
        "draw_id",
        "input_record_sha256",
        "Yp_BBN",
        "D_over_H",
        "elapsed_seconds",
        "record_sha256",
    }
    failure_fields = {
        "schema_version",
        "draw_id",
        "input_record_sha256",
        "error_type",
        "error_message",
        "traceback_tail",
        "record_sha256",
    }
    terminal_ids: list[int] = []
    for record in results:
        assert_exact_keys(record, result_fields, "result record")
        draw_id = int(record["draw_id"])
        if draw_id not in draws:
            raise ValueError("result references an unknown draw")
        if record["schema_version"] != 1:
            raise ValueError("result schema drift")
        if record["input_record_sha256"] != draws[draw_id]["record_sha256"]:
            raise ValueError("result input provenance drift")
        for field in ("Yp_BBN", "D_over_H"):
            if not finite_number(record[field]) or float(record[field]) <= 0.0:
                raise ValueError("result abundance is non-finite or non-positive")
        if not finite_number(record["elapsed_seconds"]) or record["elapsed_seconds"] < 0.0:
            raise ValueError("result elapsed time is invalid")
        terminal_ids.append(draw_id)
    for record in failures:
        assert_exact_keys(record, failure_fields, "failure record")
        draw_id = int(record["draw_id"])
        if draw_id not in draws:
            raise ValueError("failure references an unknown draw")
        if record["schema_version"] != 1:
            raise ValueError("failure schema drift")
        if record["input_record_sha256"] != draws[draw_id]["record_sha256"]:
            raise ValueError("failure input provenance drift")
        if not all(
            isinstance(record[field], str) and record[field]
            for field in ("error_type", "error_message", "traceback_tail")
        ):
            raise ValueError("failure accounting is incomplete")
        terminal_ids.append(draw_id)
    expected_ids = set(range(int(protocol["rng"]["draw_count"])))
    if len(terminal_ids) != len(set(terminal_ids)):
        raise ValueError("draw has duplicate terminal accounting")
    if set(terminal_ids) != expected_ids:
        raise ValueError("terminal draw accounting is incomplete")
    return (
        sorted(results, key=lambda record: int(record["draw_id"])),
        sorted(failures, key=lambda record: int(record["draw_id"])),
    )


def validate_controls_and_statistics(
    summary: dict[str, Any],
    *,
    results: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    draws: dict[int, dict[str, Any]],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    boundary = summary["scientific_boundary"]
    if boundary != protocol["scientific_boundary"]:
        raise ValueError("scientific boundary drift")
    for field in (
        "project_R0_prior_used",
        "accepted_scientific_prior",
        "production_authorized",
        "posterior_marginalization_reproduced",
        "scientific_signoff_provided",
    ):
        if boundary[field] is not False:
            raise ValueError("summary overclaims scientific acceptance")

    result_by_id = {int(record["draw_id"]): record for record in results}
    central = summary["central_result"]
    control_fields = {
        "draw_id",
        "input_record_sha256",
        "Yp_BBN",
        "D_over_H",
        "elapsed_seconds",
    }
    assert_exact_keys(central, control_fields, "central control")
    if central["draw_id"] != -1:
        raise ValueError("central control identity drift")
    prior = protocol["native_prior"]
    central_input = add_record_digest(
        {
            "schema_version": 1,
            "draw_id": -1,
            "seed_entropy": None,
            "seed_spawn_key": [],
            "bit_generator": None,
            "tau_n_seconds": float(prior["neutron_lifetime"]["mean_seconds"]),
            "nuclear_rate_parameter_names": list(RATE_PARAMETER_NAMES),
            "nuclear_rate_q": [0.0] * len(RATE_PARAMETER_NAMES),
        }
    )
    if central["input_record_sha256"] != central_input["record_sha256"]:
        raise ValueError("central control input provenance drift")
    for field in ("Yp_BBN", "D_over_H"):
        if not finite_number(central[field]) or central[field] <= 0.0:
            raise ValueError("central control output is nonphysical")

    sentinel_ids = [int(value) for value in protocol["execution"]["sentinel_repeat_draw_indices"]]
    repeat_rows = summary["sentinel_repeat_results"]
    if [int(record["draw_id"]) for record in repeat_rows] != sentinel_ids:
        raise ValueError("sentinel repeat set drift")
    maximum_repeat = 0.0
    for record in repeat_rows:
        expected_fields = {
            "draw_id",
            "original_success",
            "input_record_sha256",
            "repeated_Yp_BBN",
            "repeated_D_over_H",
            "repeated_elapsed_seconds",
            "Yp_BBN_relative_drift",
            "D_over_H_relative_drift",
        }
        assert_exact_keys(record, expected_fields, "sentinel repeat")
        draw_id = int(record["draw_id"])
        if record["original_success"] is not True or draw_id not in result_by_id:
            raise ValueError("registered sentinel did not complete successfully")
        original = result_by_id[draw_id]
        if record["input_record_sha256"] != draws[draw_id]["record_sha256"]:
            raise ValueError("sentinel repeat input provenance drift")
        for field in ("repeated_Yp_BBN", "repeated_D_over_H"):
            if not finite_number(record[field]) or float(record[field]) <= 0.0:
                raise ValueError("sentinel repeat output is nonphysical")
        if (
            not finite_number(record["repeated_elapsed_seconds"])
            or float(record["repeated_elapsed_seconds"]) < 0.0
        ):
            raise ValueError("sentinel repeat elapsed time is invalid")
        recomputed = {
            "Yp_BBN_relative_drift": relative_drift(
                float(original["Yp_BBN"]), float(record["repeated_Yp_BBN"])
            ),
            "D_over_H_relative_drift": relative_drift(
                float(original["D_over_H"]), float(record["repeated_D_over_H"])
            ),
        }
        for field, value in recomputed.items():
            if record[field] != value:
                raise ValueError("sentinel repeat drift was not reproducible")
            maximum_repeat = max(maximum_repeat, value)
    if maximum_repeat != float(summary["maximum_sentinel_repeat_relative_drift"]):
        raise ValueError("maximum sentinel repeat drift summary mismatch")

    yp = np.asarray([record["Yp_BBN"] for record in results], dtype=np.float64)
    dh = np.asarray([record["D_over_H"] for record in results], dtype=np.float64)
    reference = protocol["public_reference"]["exact_row"]
    acceptance = protocol["acceptance"]
    rng = protocol["rng"]
    interval_quantiles = tuple(float(value) for value in acceptance["bootstrap_interval_quantiles"])
    expected_statistics: dict[str, Any] = {}
    for offset, (name, values, center_key, sigma_key) in enumerate(
        (
            ("Yp_BBN", yp, "Yp_BBN", "sigma_Yp_BBN"),
            ("D_over_H", dh, "D_over_H", "sigma_D_over_H"),
        )
    ):
        public_center = float(reference[center_key])
        public_sigma = float(reference[sigma_key])
        sample_sigma = float(np.std(values, ddof=1))
        interval = bootstrap_sigma_interval(
            values,
            seed=int(rng["bootstrap_seed"]) + offset,
            resamples=int(rng["bootstrap_resamples"]),
            quantiles=interval_quantiles,
        )
        expected_statistics[name] = {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "sample_standard_deviation": sample_sigma,
            "sample_quantiles": {
                "q005": float(np.quantile(values, 0.005)),
                "q025": float(np.quantile(values, 0.025)),
                "q160": float(np.quantile(values, 0.16)),
                "q500": float(np.quantile(values, 0.5)),
                "q840": float(np.quantile(values, 0.84)),
                "q975": float(np.quantile(values, 0.975)),
                "q995": float(np.quantile(values, 0.995)),
            },
            "public_center": public_center,
            "public_sigma": public_sigma,
            "median_reference_offset_in_public_sigma": abs(float(np.median(values)) - public_center)
            / public_sigma,
            "sample_to_public_sigma_ratio": sample_sigma / public_sigma,
            "bootstrap_sample_sigma_interval_99_percent": interval,
            "public_sigma_inside_bootstrap_interval": interval[0] <= public_sigma <= interval[1],
        }
    if summary["statistics"] != expected_statistics:
        raise ValueError("statistics were not independently reproducible")

    central_offsets = {
        "Yp_BBN": abs(float(central["Yp_BBN"]) - float(reference["Yp_BBN"]))
        / float(reference["sigma_Yp_BBN"]),
        "D_over_H": abs(float(central["D_over_H"]) - float(reference["D_over_H"]))
        / float(reference["sigma_D_over_H"]),
    }
    if summary["central_reference_offset_in_public_sigma"] != central_offsets:
        raise ValueError("central reference offset drift")
    attempted = len(results) + len(failures)
    failure_fraction = len(failures) / attempted
    if (
        summary["attempted_draws"] != attempted
        or summary["successful_draws"] != len(results)
        or summary["failed_draws"] != len(failures)
        or summary["failure_fraction"] != failure_fraction
    ):
        raise ValueError("draw totals or failure fraction drift")

    covariance = np.cov(np.vstack((yp, dh)), ddof=1).tolist()
    correlation = np.corrcoef(np.vstack((yp, dh))).tolist()
    if summary["joint_abundance_covariance_order"] != ["Yp_BBN", "D_over_H"]:
        raise ValueError("joint abundance order drift")
    if summary["joint_abundance_covariance"] != covariance:
        raise ValueError("joint abundance covariance drift")
    if summary["joint_abundance_correlation"] != correlation:
        raise ValueError("joint abundance correlation drift")

    sigma_low, sigma_high = (float(value) for value in acceptance["public_sigma_ratio_interval"])
    expected_checks = {
        "attempted_draw_count_exact": attempted == int(acceptance["expected_attempted_draws"]),
        "minimum_successful_draws_met": len(results) >= int(acceptance["minimum_successful_draws"]),
        "maximum_failure_fraction_met": failure_fraction
        <= float(acceptance["maximum_failure_fraction"]),
        "all_outputs_finite_and_positive": bool(
            len(results)
            and np.all(np.isfinite(yp))
            and np.all(np.isfinite(dh))
            and np.all(yp > 0.0)
            and np.all(dh > 0.0)
        ),
        "central_reference_offsets_met": all(
            value <= float(acceptance["maximum_central_reference_offset_in_public_sigma"])
            for value in central_offsets.values()
        ),
        "median_reference_offsets_met": all(
            item["median_reference_offset_in_public_sigma"]
            <= float(acceptance["maximum_median_reference_offset_in_public_sigma"])
            for item in expected_statistics.values()
        ),
        "public_sigma_ratios_met": all(
            sigma_low <= item["sample_to_public_sigma_ratio"] <= sigma_high
            for item in expected_statistics.values()
        ),
        "public_sigmas_inside_bootstrap_intervals": all(
            item["public_sigma_inside_bootstrap_interval"] for item in expected_statistics.values()
        ),
        "sentinel_repeats_met": maximum_repeat
        <= float(acceptance["maximum_repeat_relative_drift"]),
    }
    if summary["acceptance_checks"] != expected_checks:
        raise ValueError("acceptance checks were not independently reproducible")
    if not all(expected_checks.values()):
        raise ValueError("one or more frozen acceptance checks failed")
    if summary["accepted"] is not True:
        raise ValueError("accepted summary flag is false")
    if summary["status"] != "accepted_C0_native_abundance_MC":
        raise ValueError("accepted status drift")
    return {
        "attempted_draws": attempted,
        "successful_draws": len(results),
        "failed_draws": len(failures),
        "maximum_sentinel_repeat_relative_drift": maximum_repeat,
        "Yp_sigma_ratio": expected_statistics["Yp_BBN"]["sample_to_public_sigma_ratio"],
        "D_over_H_sigma_ratio": expected_statistics["D_over_H"]["sample_to_public_sigma_ratio"],
    }


def validate_state(
    state: dict[str, Any],
    *,
    manifest: dict[str, Any],
    results: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    expected_draws: int,
) -> None:
    required = {
        "schema_version",
        "run_id",
        "status",
        "expected_attempted_draws",
        "completed_draw_ids",
        "successful_draws",
        "failed_draws",
        "updated_at_utc",
        "evidence_sha256",
    }
    assert_exact_keys(state, required, "run state")
    if state["schema_version"] != 1 or state["run_id"] != manifest["run_id"]:
        raise ValueError("run state identity drift")
    if state["status"] != "accepted":
        raise ValueError("run state is not accepted")
    if state["expected_attempted_draws"] != expected_draws:
        raise ValueError("run state expected count drift")
    ids = sorted(int(record["draw_id"]) for record in [*results, *failures])
    if state["completed_draw_ids"] != ids:
        raise ValueError("run state completed-ID accounting drift")
    if state["successful_draws"] != len(results) or state["failed_draws"] != len(failures):
        raise ValueError("run state terminal totals drift")
    try:
        datetime.fromisoformat(state["updated_at_utc"])
    except (TypeError, ValueError) as error:
        raise ValueError("run state timestamp is invalid") from error


def validate(
    output_dir: Path,
    *,
    protocol_path: Path = DEFAULT_PROTOCOL,
) -> dict[str, Any]:
    protocol_path = protocol_path.resolve()
    protocol = load_protocol(protocol_path)
    validate_runtime_environment(protocol)
    expected_files = set(OUTPUT_FILENAMES.values())
    observed_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if observed_files != expected_files:
        raise ValueError(f"run directory file set drift: {sorted(observed_files ^ expected_files)}")

    manifest = load_digest_json(output_dir / OUTPUT_FILENAMES["run_manifest"], "run manifest")
    draws = load_jsonl(output_dir / OUTPUT_FILENAMES["draw_manifest"])
    draw_by_id = validate_draws(draws, protocol)
    validate_run_manifest(
        manifest,
        protocol_path=protocol_path,
        protocol=protocol,
        draws=draws,
    )
    results = load_jsonl(output_dir / OUTPUT_FILENAMES["results"])
    failures = load_jsonl(output_dir / OUTPUT_FILENAMES["failures"])
    results, failures = validate_terminal_records(results, failures, draw_by_id, protocol)
    summary = load_digest_json(output_dir / OUTPUT_FILENAMES["summary"], "summary")
    if summary["schema_version"] != 1:
        raise ValueError("summary schema drift")
    if summary["artifact_id"] != EXPECTED_PROTOCOL_ID:
        raise ValueError("summary artifact identity drift")
    if summary["task_id"] != EXPECTED_TASK_ID:
        raise ValueError("summary task identity drift")
    if summary["run_id"] != manifest["run_id"]:
        raise ValueError("summary run identity drift")
    metrics = validate_controls_and_statistics(
        summary,
        results=results,
        failures=failures,
        draws=draw_by_id,
        protocol=protocol,
    )
    state = load_digest_json(output_dir / OUTPUT_FILENAMES["state"], "run state")
    validate_state(
        state,
        manifest=manifest,
        results=results,
        failures=failures,
        expected_draws=int(protocol["rng"]["draw_count"]),
    )
    metrics.update(
        {
            "accepted": True,
            "run_id": manifest["run_id"],
            "summary_sha256": sha256(output_dir / OUTPUT_FILENAMES["summary"]),
        }
    )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    args = parser.parse_args()
    result = validate(args.output_dir.resolve(), protocol_path=args.protocol)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
