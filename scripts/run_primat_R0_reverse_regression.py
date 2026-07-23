#!/usr/bin/env python3
"""Audit PRIMAT R0 reverse-rate, cap, and consecutive-draw cache behaviour."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


REACTIONS = (
    "d_p__He3_g",
    "d_d__He3_n",
    "d_d__t_p",
)
Q_PROBES = (-3.0, -1.0, 0.0, 1.0, 3.0)
EXPECTED_REVISION = "21ff8f39fa18e3937e9fdf386cfa982361bfdfce"
CAP_RELATIVE_DETECTION_TOLERANCE = 1.0e-13


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def primat_source_root(imported_module_path: Path) -> Path:
    """Resolve the frozen source checkout, including non-editable local installs."""
    installed_root = imported_module_path.parents[1]
    if (installed_root / ".git").exists():
        return installed_root
    direct_url_text = importlib.metadata.distribution("primat").read_text(
        "direct_url.json"
    )
    if not direct_url_text:
        raise RuntimeError("installed PRIMAT lacks direct_url.json provenance")
    direct_url = json.loads(direct_url_text)
    parsed = urlparse(direct_url["url"])
    if parsed.scheme != "file":
        raise RuntimeError(f"PRIMAT direct_url is not a local checkout: {direct_url}")
    source_root = Path(unquote(parsed.path)).resolve()
    if not (source_root / ".git").exists():
        raise RuntimeError(f"PRIMAT direct_url is not a git checkout: {source_root}")
    return source_root


def set_draw(cfg: Any, reaction: str | None = None, q: float = 0.0) -> None:
    for name in REACTIONS:
        setattr(cfg, f"p_{name}", q if name == reaction else 0.0)
        setattr(cfg, f"delta_{name}", 0.0)


def clear_rate_cache(net: Any) -> None:
    net._cache_T_t = None
    net._cache_clamp = None


def evaluate(net: Any, temperature_t9: float, clamp: bool, *, fresh: bool) -> Any:
    if fresh:
        clear_rate_cache(net)
    return net.fill_buffer(
        temperature_t9 * 1.0e9,
        lambda _temperature: 0.0,
        lambda _temperature: 0.0,
        clamp=clamp,
    ).copy()


def relative_difference(value: float, reference: float) -> float:
    if reference == 0.0:
        return 0.0 if value == 0.0 else math.inf
    return value / reference - 1.0


def build_probe_grid(
    source_grid: list[float],
    native_grid: list[float],
    lt_min: float,
    lt_max: float,
) -> dict[str, Any]:
    published = sorted(value for value in source_grid if 0.06 <= value <= 2.0)
    published_midpoints = [
        math.sqrt(left * right)
        for left, right in zip(published, published[1:])
    ]
    native_lt = sorted(value for value in native_grid if lt_min <= value <= lt_max)
    native_lt_midpoints = [
        math.sqrt(left * right)
        for left, right in zip(native_lt, native_lt[1:])
    ]
    full = sorted(
        set(
            published
            + published_midpoints
            + native_lt
            + native_lt_midpoints
            + [lt_min, lt_max]
        )
    )
    actual_lt_probes = [value for value in full if lt_min <= value <= lt_max]
    return {
        "registered_ETR25_primary_knots": published,
        "registered_ETR25_primary_geometric_midpoints": published_midpoints,
        "PRIMAT_native_LT_grid_knots": native_lt,
        "PRIMAT_native_LT_grid_geometric_midpoints": native_lt_midpoints,
        "LT_boundary_points": [lt_min, lt_max],
        "full_diagnostic_grid": full,
        "actual_LT_probe_subset": actual_lt_probes,
        "actual_solver_temperature_trajectory_evaluated": False,
        "scope_interpretation": (
            "0.06<=T9<=2.0 is the registered all-R0 table-comparison scope, "
            "not a claimed physical sensitivity window; native LT knots and "
            "midpoints are dense probes, not a proof over the continuous interval "
            "or an emitted solver trajectory"
        ),
    }


def reaction_buffer_indices(net: Any, name: str) -> tuple[int, int, int]:
    name_index = net.names.index(name)
    if name_index == 0:
        raise ValueError("weak n__p reaction is not an R0 thermonuclear rate")
    table_index = name_index - 1
    return table_index, 2 + 2 * table_index, 3 + 2 * table_index


def audit_reaction(
    cfg: Any,
    net: Any,
    reaction: str,
    temperatures: list[float],
    actual_lt_probes: set[float],
) -> dict[str, Any]:
    table_index, forward_index, reverse_index = reaction_buffer_indices(net, reaction)
    alpha, beta, gamma = (float(value) for value in net._abg[table_index])

    set_draw(cfg)
    net.apply_variations(cfg)
    baseline: dict[float, dict[str, float]] = {}
    for temperature in temperatures:
        unclamped = evaluate(net, temperature, False, fresh=True)
        clamped = evaluate(net, temperature, True, fresh=True)
        baseline[temperature] = {
            "forward": float(unclamped[forward_index]),
            "reverse_unclamped": float(unclamped[reverse_index]),
            "reverse_clamped": float(clamped[reverse_index]),
        }

    rows: list[dict[str, Any]] = []
    max_ratio_residual = 0.0
    max_shift_residual = 0.0
    ratio_defined_rows = 0
    shift_defined_rows = 0
    ratio_excluded_rows = 0
    shift_excluded_rows = 0
    cap_active_rows = 0
    cap_active_actual_lt_probe_rows = 0
    for q in Q_PROBES:
        set_draw(cfg, reaction, q)
        net.apply_variations(cfg)
        for temperature in temperatures:
            unclamped = evaluate(net, temperature, False, fresh=True)
            clamped = evaluate(net, temperature, True, fresh=True)
            forward = float(unclamped[forward_index])
            reverse_unclamped = float(unclamped[reverse_index])
            reverse_clamped = float(clamped[reverse_index])
            detailed_balance_factor = (
                alpha
                * temperature**beta
                * math.exp(min(gamma / temperature, 700.0))
            )
            expected_reverse = detailed_balance_factor * forward
            base = baseline[temperature]
            if (
                expected_reverse < sys.float_info.min
                or reverse_unclamped < sys.float_info.min
            ):
                ratio_residual = None
                ratio_exclusion = "zero_or_subnormal_reverse"
                ratio_excluded_rows += 1
            else:
                ratio_residual = relative_difference(
                    reverse_unclamped, expected_reverse
                )
                ratio_exclusion = None
                ratio_defined_rows += 1
                max_ratio_residual = max(
                    max_ratio_residual, abs(ratio_residual)
                )
            if (
                forward < sys.float_info.min
                or reverse_unclamped < sys.float_info.min
                or base["forward"] < sys.float_info.min
                or base["reverse_unclamped"] < sys.float_info.min
            ):
                shift_residual = None
                shift_exclusion = "zero_or_subnormal_forward_or_reverse"
                shift_excluded_rows += 1
            else:
                shift_residual = (
                    (math.log(reverse_unclamped) - math.log(forward))
                    - (
                        math.log(base["reverse_unclamped"])
                        - math.log(base["forward"])
                    )
                )
                shift_exclusion = None
                shift_defined_rows += 1
                max_shift_residual = max(
                    max_shift_residual, abs(shift_residual)
                )
            cap_active = reverse_clamped < reverse_unclamped * (
                1.0 - CAP_RELATIVE_DETECTION_TOLERANCE
            )
            cap_active_rows += int(cap_active)
            cap_active_actual_lt_probe_rows += int(
                cap_active and temperature in actual_lt_probes
            )
            rows.append(
                {
                    "T9": temperature,
                    "in_actual_LT_probe_subset": temperature in actual_lt_probes,
                    "q": q,
                    "forward": forward,
                    "reverse_unclamped": reverse_unclamped,
                    "reverse_clamped": reverse_clamped,
                    "detailed_balance_factor": detailed_balance_factor,
                    "reverse_over_expected_minus_one": ratio_residual,
                    "reverse_ratio_exclusion_reason": ratio_exclusion,
                    "log_reverse_shift_minus_log_forward_shift": shift_residual,
                    "log_shift_exclusion_reason": shift_exclusion,
                    "reverse_cap_active_within_detection_tolerance": cap_active,
                }
            )

    return {
        "reaction": reaction,
        "source": net.sources[net.names.index(reaction)] if net.sources else None,
        "detailed_balance_coefficients": {
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        },
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "reverse_ratio_defined_rows": ratio_defined_rows,
            "reverse_ratio_excluded_rows": ratio_excluded_rows,
            "log_shift_defined_rows": shift_defined_rows,
            "log_shift_excluded_rows": shift_excluded_rows,
            "max_abs_reverse_over_expected_minus_one": max_ratio_residual,
            "max_abs_log_reverse_shift_minus_log_forward_shift": max_shift_residual,
            "reverse_cap_active_within_tolerance_rows": cap_active_rows,
            "reverse_cap_active_actual_LT_probe_rows": (
                cap_active_actual_lt_probe_rows
            ),
        },
    }


def audit_consecutive_draw_cache(cfg: Any, net: Any, temperature_t9: float) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for reaction in REACTIONS:
        _, forward_index, reverse_index = reaction_buffer_indices(net, reaction)
        for clamp in (False, True):
            set_draw(cfg)
            net.apply_variations(cfg)
            baseline = evaluate(net, temperature_t9, clamp, fresh=True)

            set_draw(cfg, reaction, 3.0)
            net.apply_variations(cfg)
            cache_hit = evaluate(net, temperature_t9, clamp, fresh=False)
            refreshed = evaluate(net, temperature_t9, clamp, fresh=True)

            stale_forward = bool(cache_hit[forward_index] == baseline[forward_index])
            stale_reverse = bool(cache_hit[reverse_index] == baseline[reverse_index])
            fresh_forward_changed = bool(
                refreshed[forward_index] != baseline[forward_index]
            )
            cases.append(
                {
                    "reaction": reaction,
                    "T9": temperature_t9,
                    "clamp": clamp,
                    "q_after_apply_variations": 3.0,
                    "same_temperature_cache_hit_forward_equals_baseline": stale_forward,
                    "same_temperature_cache_hit_reverse_equals_baseline": stale_reverse,
                    "after_manual_cache_clear_forward_changed": fresh_forward_changed,
                    "refreshed_forward_relative_change": relative_difference(
                        float(refreshed[forward_index]),
                        float(baseline[forward_index]),
                    ),
                    "refreshed_reverse_relative_change": relative_difference(
                        float(refreshed[reverse_index]),
                        float(baseline[reverse_index]),
                    ),
                }
            )
    confirmed = all(
        case["same_temperature_cache_hit_forward_equals_baseline"]
        and case["same_temperature_cache_hit_reverse_equals_baseline"]
        and case["after_manual_cache_clear_forward_changed"]
        for case in cases
    )
    return {
        "cases": cases,
        "upstream_apply_variations_does_not_invalidate_fill_buffer_cache": confirmed,
        "production_requirement": (
            "invalidate _cache_T_t and _cache_clamp immediately after every "
            "apply_variations call, or construct a fresh network per draw"
        ),
    }


def load_project_guard(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("project_primat_rate_draw", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load project cache guard from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_project_wrapper_guard(
    cfg: Any,
    mt_net: Any,
    lt_net: Any,
    wrapper_class: Any,
    guard_path: Path,
    temperature_t9: float,
) -> dict[str, Any]:
    guard = load_project_guard(guard_path)
    wrapper = object.__new__(wrapper_class)
    wrapper._mt_net = mt_net
    wrapper._lt_net = lt_net
    cases: list[dict[str, Any]] = []
    for era, net in (("MT", mt_net), ("LT", lt_net)):
        for reaction in REACTIONS:
            if reaction not in net.names:
                continue
            _, forward_index, reverse_index = reaction_buffer_indices(net, reaction)
            for clamp in (False, True):
                set_draw(cfg)
                guard.apply_variations_safely(wrapper, cfg)
                baseline = evaluate(net, temperature_t9, clamp, fresh=True)

                set_draw(cfg, reaction, 3.0)
                guard.apply_variations_safely(wrapper, cfg)
                cache_was_invalidated = (
                    mt_net._cache_T_t is None
                    and mt_net._cache_clamp is None
                    and lt_net._cache_T_t is None
                    and lt_net._cache_clamp is None
                )
                guarded = evaluate(net, temperature_t9, clamp, fresh=False)
                cases.append(
                    {
                        "era": era,
                        "reaction": reaction,
                        "T9": temperature_t9,
                        "clamp": clamp,
                        "both_era_caches_invalidated_before_evaluation": (
                            cache_was_invalidated
                        ),
                        "guarded_forward_changed_from_baseline": bool(
                            guarded[forward_index] != baseline[forward_index]
                        ),
                        "guarded_reverse_changed_from_baseline": bool(
                            guarded[reverse_index] != baseline[reverse_index]
                        ),
                    }
                )
    passed = bool(cases) and all(
        case["both_era_caches_invalidated_before_evaluation"]
        and case["guarded_forward_changed_from_baseline"]
        and case["guarded_reverse_changed_from_baseline"]
        for case in cases
    )
    return {
        "guard_path": str(guard_path.name),
        "guard_sha256": sha256(guard_path),
        "uses_actual_UpdateNuclearRates_apply_variations_method": True,
        "wrapper_constructed_without_solver_compilation": True,
        "cases": cases,
        "both_MT_and_LT_network_caches_guarded": passed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--etr25-package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--project-cache-guard", required=True, type=Path)
    parser.add_argument("--expected-revision", default=EXPECTED_REVISION)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from primat.config import PRIMATConfig
    from primat.network_data import UpdateNuclearRates, load_network
    import primat.network_data as network_data_module

    package = json.loads(args.etr25_package.read_text(encoding="utf-8"))
    cfg = PRIMATConfig(
        {
            "network": "small",
            "strict_params": True,
            "show_progress": False,
            "mc_rate_rescale_cap": 30.0,
        }
    )
    net = load_network(cfg, era="LT")
    mt_net = load_network(cfg, era="MT")
    missing = sorted(set(REACTIONS) - set(net.names))
    if missing:
        raise RuntimeError(f"PRIMAT small LT network lacks R0 reactions: {missing}")

    imported_network_data_path = Path(network_data_module.__file__).resolve()
    source_root = primat_source_root(imported_network_data_path)
    revision = git_revision(source_root)
    if revision != args.expected_revision:
        raise RuntimeError(
            f"PRIMAT revision drift: expected {args.expected_revision}, got {revision}"
        )

    lt_min = cfg.T_end_MeV * cfg.MeV_to_Kelvin * 1.0e-9
    lt_max = cfg.T_nucl * 1.0e-9
    probe_grid = build_probe_grid(
        package["coordinate"]["grid"],
        [float(value) for value in net.grid],
        lt_min,
        lt_max,
    )
    temperatures = probe_grid["full_diagnostic_grid"]
    actual_lt_probes = set(probe_grid["actual_LT_probe_subset"])

    reactions = [
        audit_reaction(cfg, net, reaction, temperatures, actual_lt_probes)
        for reaction in REACTIONS
    ]
    cache = audit_consecutive_draw_cache(cfg, net, temperature_t9=0.8)
    project_guard = audit_project_wrapper_guard(
        cfg,
        mt_net,
        net,
        UpdateNuclearRates,
        args.project_cache_guard,
        temperature_t9=0.8,
    )
    cap_active = sum(
        item["summary"]["reverse_cap_active_within_tolerance_rows"]
        for item in reactions
    )
    cap_active_actual_lt_probes = sum(
        item["summary"]["reverse_cap_active_actual_LT_probe_rows"]
        for item in reactions
    )
    ratio_exclusions = sum(
        item["summary"]["reverse_ratio_excluded_rows"] for item in reactions
    )
    shift_exclusions = sum(
        item["summary"]["log_shift_excluded_rows"] for item in reactions
    )
    max_ratio_residual = max(
        item["summary"]["max_abs_reverse_over_expected_minus_one"]
        for item in reactions
    )
    max_shift_residual = max(
        item["summary"]["max_abs_log_reverse_shift_minus_log_forward_shift"]
        for item in reactions
    )
    network_data_path = source_root / "primat/network_data.py"
    config_path = source_root / "primat/config.py"

    output = {
        "schema_version": 1,
        "artifact_id": "PRIMAT-R0-REVERSE-REGRESSION-v1",
        "status": (
            "reverse_identity_passed_R0_cap_characterized_"
            "upstream_cache_invalidation_required"
        ),
        "source": {
            "repository": "https://github.com/CyrilPitrou/primat",
            "revision": revision,
            "network_data_path": str(network_data_path.relative_to(source_root)),
            "network_data_sha256": sha256(network_data_path),
            "config_path": str(config_path.relative_to(source_root)),
            "config_sha256": sha256(config_path),
            "imported_network_data_sha256": sha256(imported_network_data_path),
            "ETR25_package": str(args.etr25_package),
            "ETR25_package_sha256": sha256(args.etr25_package),
        },
        "configuration": {
            "network": "small",
            "era": "LT",
            "native_rate_grid_T9": [
                cfg.rate_grid_T9_min,
                cfg.rate_grid_T9_max,
                cfg.rate_grid_npts,
            ],
            "T9_LT_min_from_T_end": lt_min,
            "T9_LT_max_from_T_nucl": lt_max,
            "mc_rate_rescale_cap": cfg.mc_rate_rescale_cap,
            "nuclear_qed_corrections": cfg.nuclear_qed_corrections,
            "q_probes": list(Q_PROBES),
            "cap_relative_detection_tolerance": (
                CAP_RELATIVE_DETECTION_TOLERANCE
            ),
            "FP64_min_normal_for_log_identity": sys.float_info.min,
        },
        "probe_grid": probe_grid,
        "reactions": reactions,
        "consecutive_draw_cache_regression": cache,
        "project_UpdateNuclearRates_wrapper_guard_regression": project_guard,
        "acceptance": {
            "unclamped_reverse_detailed_balance_max_abs_relative_tolerance": 1.0e-12,
            "unclamped_log_shift_identity_max_abs_tolerance": 1.0e-12,
            "unclamped_reverse_detailed_balance_passed": max_ratio_residual <= 1.0e-12,
            "unclamped_log_shift_identity_passed": max_shift_residual <= 1.0e-12,
            "reverse_ratio_explicit_zero_or_underflow_exclusions": ratio_exclusions,
            "log_shift_explicit_zero_or_underflow_exclusions": shift_exclusions,
            "reverse_cap_active_within_tolerance_rows": cap_active,
            "reverse_cap_active_actual_LT_probe_rows": cap_active_actual_lt_probes,
            "R0_reverse_cap_not_detected_over_full_diagnostic_grid_within_tolerance": (
                cap_active == 0
            ),
            "R0_reverse_cap_not_detected_on_actual_LT_probe_points_within_tolerance": (
                cap_active_actual_lt_probes == 0
            ),
            "actual_solver_temperature_trajectory_evaluated": False,
            "upstream_cache_invalidation_required": cache[
                "upstream_apply_variations_does_not_invalidate_fill_buffer_cache"
            ],
            "project_wrapper_guard_passed": project_guard[
                "both_MT_and_LT_network_caches_guarded"
            ],
            "production_adapter_allowed_without_cache_guard": False,
            "production_adapter_unlocked_by_this_artifact": False,
            "scientific_prior_frozen_by_this_artifact": False,
        },
        "interpretation": {
            "reverse_cap": (
                "The load-time median/QED-derived native cap is characterized here; "
                "non-detection, if observed, is limited to discrete native-grid, "
                "midpoint and ETR25 probe points under PRIMAT native p/expsigma draws. "
                "It is not a continuous-domain proof or an ETR25 curve-injection test."
            ),
            "cache": (
                "A same-temperature call immediately following apply_variations can "
                "return the previous draw's buffer unless the caller invalidates the cache."
            ),
            "scope": (
                "This is a numerical adapter regression, not evidence that the ETR25 "
                "posterior or cross-reaction correlation structure has been recovered."
            ),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not (
        output["acceptance"]["unclamped_reverse_detailed_balance_passed"]
        and output["acceptance"]["unclamped_log_shift_identity_passed"]
    ):
        raise SystemExit("PRIMAT R0 reverse-rate identity regression failed")


if __name__ == "__main__":
    main()
