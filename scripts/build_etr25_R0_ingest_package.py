#!/usr/bin/env python3
"""Build the pinned ETR25 R0 table package from official IOP ASCII products."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


EXPECTED_PAPER_TEX_SHA256 = "cc670aed6f80c25c9517b9098fae9255fe403ad78cd41b13d74b382daa9fe7b9"
EXPECTED_SOURCE_TAR_SHA256 = "33c1702537d44bf2ca253832dfecbb18a3ada4fd2078af81e28fd1effae50e5b"
IOP_URL_PREFIX = "https://iopscience.iop.org/0067-0049/283/1/17/suppdata/"
IOP_URL_SUFFIX = "?doi=10.3847/1538-4365/ae2bdc"
TABLES = {
    "dp_gamma_he3": {
        "table_number": 6,
        "label": "tab:dpg",
        "ascii_filename": "apjsae2bdct6_ascii.txt",
        "ascii_size_bytes": 3471,
        "ascii_sha256": ("9297c83ec659432998047023b7253ef91ba5ecaca159a90bc7feda5fbe1ebba4"),
        "equation": "D(p,gamma)3He",
        "classification": "Bayesian_rate_adopted_from_Moscoso_2021",
        "primary_rate_reference": "Moscoso_et_al_2021",
        "primary_rate_reference_doi": "10.3847/1538-4357/ac1db0",
        "high_temperature_reference": "Coc_et_al_2015",
        "high_temperature_start_T9": 5.0,
    },
    "dd_n_he3": {
        "table_number": 7,
        "label": "tab:ddn",
        "ascii_filename": "apjsae2bdct7_ascii.txt",
        "ascii_size_bytes": 3471,
        "ascii_sha256": ("30445d5e13518aeec0220b9b5e422ee1cb14d41310c0ac1c639294e8ed00b9bd"),
        "equation": "D(d,n)3He",
        "classification": ("modified_Bayesian_recalculation_relative_to_Gomez_Inesta_2017"),
        "primary_rate_reference": "Gomez_Inesta_et_al_2017",
        "primary_rate_reference_doi": "10.3847/1538-4357/aa9025",
        "high_temperature_reference": "Coc_et_al_2015",
        "high_temperature_start_T9": 2.5,
    },
    "dd_p_t": {
        "table_number": 8,
        "label": "tab:ddp",
        "ascii_filename": "apjsae2bdct8_ascii.txt",
        "ascii_size_bytes": 3469,
        "ascii_sha256": ("87d0312c4b807cb2069d59dc8519d92014bb12303e9c7931e175801b16e73682"),
        "equation": "D(d,p)3H",
        "classification": ("modified_Bayesian_recalculation_relative_to_Gomez_Inesta_2017"),
        "primary_rate_reference": "Gomez_Inesta_et_al_2017",
        "primary_rate_reference_doi": "10.3847/1538-4357/aa9025",
        "high_temperature_reference": "Coc_et_al_2015",
        "high_temperature_start_T9": 2.5,
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def parse_value(raw: str) -> tuple[float, bool]:
    text = raw.strip()
    parenthesized = text.startswith("(") and text.endswith(")")
    text = text.strip("()").strip()
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"expected a finite positive table value, got {raw!r}")
    return value, parenthesized


def row_from_fields(fields: list[str], *, source: str, line_number: int) -> dict[str, Any]:
    if len(fields) != 5:
        raise ValueError(f"{source} line {line_number}: expected 5 fields, got {len(fields)}")
    parsed = [parse_value(value) for value in fields]
    values = [value for value, _ in parsed]
    parenthesized = [flag for _, flag in parsed]
    if parenthesized[0]:
        raise ValueError(f"{source} line {line_number}: T9 must not be parenthesized")
    if any(parenthesized[1:]) and not all(parenthesized[1:]):
        raise ValueError(f"{source} line {line_number}: incomplete matched-rate marking")
    low, median, high, factor_uncertainty = values[1:]
    if not low <= median <= high:
        raise ValueError(f"{source} T9={values[0]}: expected low <= median <= high")
    if factor_uncertainty < 1:
        raise ValueError(f"{source} T9={values[0]}: factor uncertainty below one")
    return {
        "T9": values[0],
        "low_p16": low,
        "median_p50": median,
        "high_p84": high,
        "factor_uncertainty_lognormal": factor_uncertainty,
        "high_temperature_matched_rate": any(parenthesized[1:]),
    }


def validate_rows(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    rows.sort(key=lambda row: row["T9"])
    if len(rows) != 60:
        raise ValueError(f"{source}: expected 60 temperature rows, found {len(rows)}")
    if len({row["T9"] for row in rows}) != len(rows):
        raise ValueError(f"{source}: duplicate T9 values")
    return rows


def parse_iop_ascii(path: Path, table_number: int) -> tuple[list[dict[str, Any]], str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != f"Table {table_number}":
        raise ValueError(f"{path}: missing Table {table_number} header")

    rows: list[dict[str, Any]] = []
    note = ""
    for line_number, line in enumerate(lines, 1):
        if line.startswith("Note."):
            note = line
            break
        fields = line.rstrip("\t").split("\t")
        if len(fields) != 10:
            continue
        try:
            float(fields[0])
        except ValueError:
            continue
        rows.append(row_from_fields(fields[:5], source=path.name, line_number=line_number))
        rows.append(row_from_fields(fields[5:], source=path.name, line_number=line_number))
    if not note:
        raise ValueError(f"{path}: missing source Note")
    return validate_rows(rows, path.name), note


def extract_tex_table(source: str, label: str) -> list[dict[str, Any]]:
    label_marker = rf"\label{{{label}}}"
    label_start = source.find(label_marker)
    if label_start < 0:
        raise ValueError(f"missing ETR25 table label {label}")
    table_end = source.find(r"\end{deluxetable*}", label_start)
    if table_end < 0:
        raise ValueError(f"missing end marker for ETR25 table {label}")
    block = source[label_start:table_end]
    data_start = block.find(r"\startdata")
    data_end = block.find(r"\enddata", data_start)
    if data_start < 0 or data_end < 0:
        raise ValueError(f"missing data markers for ETR25 table {label}")

    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        block[data_start + len(r"\startdata") : data_end].splitlines(), 1
    ):
        if "&" not in line:
            continue
        fields = [field.strip() for field in line.split("&")]
        if len(fields) != 10:
            raise ValueError(
                f"{label} data line {line_number}: expected 10 fields, got {len(fields)}"
            )
        fields[-1] = re.sub(r"\\\\\s*$", "", fields[-1]).strip()
        rows.append(row_from_fields(fields[:5], source=label, line_number=line_number))
        rows.append(row_from_fields(fields[5:], source=label, line_number=line_number))
    return validate_rows(rows, label)


def build(iop_table_dir: Path, arxiv_source_root: Path) -> dict[str, Any]:
    paper_tex = arxiv_source_root / "paper.tex"
    actual_tex_sha256 = sha256(paper_tex)
    if actual_tex_sha256 != EXPECTED_PAPER_TEX_SHA256:
        raise ValueError(
            f"paper.tex SHA256 mismatch: {actual_tex_sha256} != {EXPECTED_PAPER_TEX_SHA256}"
        )
    tex_source = paper_tex.read_text(encoding="utf-8")

    reactions: dict[str, Any] = {}
    common_grid: list[float] | None = None
    for reaction_id, specification in TABLES.items():
        ascii_path = iop_table_dir / specification["ascii_filename"]
        actual_ascii_sha256 = sha256(ascii_path)
        if actual_ascii_sha256 != specification["ascii_sha256"]:
            raise ValueError(
                f"{ascii_path.name} SHA256 mismatch: {actual_ascii_sha256} != "
                f"{specification['ascii_sha256']}"
            )
        if ascii_path.stat().st_size != specification["ascii_size_bytes"]:
            raise ValueError(f"{ascii_path.name}: byte length mismatch")

        rows, note = parse_iop_ascii(ascii_path, specification["table_number"])
        tex_rows = extract_tex_table(tex_source, specification["label"])
        if rows != tex_rows:
            raise ValueError(f"{reaction_id}: IOP ASCII and pinned arXiv TeX rows differ")
        matched_t9 = [row["T9"] for row in rows if row["high_temperature_matched_rate"]]
        if not matched_t9 or min(matched_t9) != specification["high_temperature_start_T9"]:
            raise ValueError(f"{reaction_id}: unexpected high-temperature match boundary")
        grid = [row["T9"] for row in rows]
        if common_grid is None:
            common_grid = grid
        elif grid != common_grid:
            raise ValueError(f"{reaction_id}: R0 tables do not share one T9 grid")

        reactions[reaction_id] = {
            **specification,
            "ascii_url": (f"{IOP_URL_PREFIX}{specification['ascii_filename']}{IOP_URL_SUFFIX}"),
            "ascii_sha256_verified": actual_ascii_sha256,
            "ascii_note": note,
            "arxiv_tex_crosscheck": "exact_numeric_and_parenthesis_match",
            "units": "cm^3 mol^-1 s^-1",
            "coordinate": "T9_GK",
            "percentile_semantics": {
                "low": 16,
                "median": 50,
                "high": 84,
                "source": "actual_rate_probability_density",
            },
            "factor_uncertainty_semantics": {
                "coverage_percent": 68,
                "model": "lognormal_approximation",
                "sigma_log": "ln(factor_uncertainty_lognormal)",
                "not_derived_directly_from_actual_percentiles": True,
            },
            "rows_sha256": payload_sha256(rows),
            "rows": rows,
        }

    assert common_grid is not None
    return {
        "schema_version": 1,
        "package_id": "ETR25-R0-TABLES-v1",
        "status": (
            "official_percentile_tables_ingested_posterior_draws_not_in_identified_public_release"
        ),
        "production_use": ("prohibited_pending_rate_pdf_audit_and_coherent_draw_model"),
        "paper": {
            "title": ("The 2025 Evaluation of Experimental Thermonuclear Reaction Rates"),
            "authors_short": "Iliadis et al.",
            "arxiv_id": "2601.20059v1",
            "arxiv_submitted_utc": "2026-01-27",
            "journal": "Astrophysical Journal Supplement Series 283, 17 (2026)",
            "doi": "10.3847/1538-4365/ae2bdc",
            "license": "CC-BY-4.0",
            "source_tar_url": "https://arxiv.org/e-print/2601.20059",
            "source_tar_sha256": EXPECTED_SOURCE_TAR_SHA256,
            "paper_tex_path": "paper.tex",
            "paper_tex_sha256": actual_tex_sha256,
        },
        "machine_readable_source": {
            "publisher": "IOP Publishing",
            "role": "primary_exact_table_byte_source",
            "article_url": ("https://iopscience.iop.org/article/10.3847/1538-4365/ae2bdc"),
            "license": "CC-BY-4.0",
            "pinning_contract": "full_url_plus_size_plus_sha256",
            "server_etag_last_modified_content_type": "not_supplied",
        },
        "official_archives": {
            "ETR25_Zenodo": {
                "record_id": 17610211,
                "doi": "10.5281/zenodo.17610211",
                "concept_doi": "10.5281/zenodo.17610210",
                "version": "vETR25",
                "license": "CC0-1.0",
                "files": {
                    "RatesMC_Input_Files.zip": {
                        "size": 189139,
                        "md5": "ac3b9fafb288839a7e90e2c1aaa3cfab",
                        "sha256": (
                            "b629cdb6579a66e94bb7f60cbc9dd240cfb6ce14875cfcea4448aeec73a20146"
                        ),
                    },
                    "RatesMC_Output_Files.zip": {
                        "size": 106875,
                        "md5": "9914cc2621e2bdd6d0a444421e00e214",
                        "sha256": (
                            "fe15751352aa6fae65fbe19cbc9d5ffc2db108bf62309b23b80055ee36c3fcf6"
                        ),
                    },
                    "TALYS_Input_Files.zip": {
                        "size": 47759,
                        "md5": "ba905caa4cc91c5dc4dd5def1395c09a",
                        "sha256": (
                            "c97f451deebaef2b59ff23ca73b98c66c067eebc6880c11d94d6d843e342755e"
                        ),
                    },
                },
                "R0_Bayesian_inputs_or_outputs_in_archives": False,
            },
            "RatesMC_Zenodo": {
                "record_id": 17516449,
                "doi": "10.5281/zenodo.17516449",
                "concept_doi": "10.5281/zenodo.17516448",
                "version": "v2.3",
                "license_metadata": "GPL-3.0",
                "source_headers_license": "GPL-3.0-or-later",
                "source_archive_md5": "8bde9acc3003ca4484ce83c364047be8",
            },
        },
        "official_repositories": {
            "RatesMC": {
                "url": "https://github.com/rlongland/RatesMC",
                "revision": "3649f24baa9be9e8d398d6fc5ca77e83a1107592",
                "tag": "v2.3",
                "license": "GPL-3.0-or-later",
            },
            "ETR25_evaluation_inputs": {
                "url": ("https://github.com/TUNL-Reaction-Rates-Group/2025-rates-evaluation"),
                "data_revision": ("45e79da431767be5efac137755c645347172afc5"),
                "current_revision_audited": ("3f6feda6e045056c0aa078311dcc0a2969c5565b"),
                "tag_vETR25_revision": ("23763a0436495095c035ffa3b9b26407d3c03900"),
                "tag_vETR25_contains_data": False,
                "repository_license": "not_declared",
                "Zenodo_archive_license": "CC0-1.0",
                "R0_Bayesian_inputs_present": False,
            },
        },
        "source_boundary": {
            "R0_rate_type": ("Bayesian_exception_not_RatesMC_50000_sample_rate"),
            "actual_percentiles_available": True,
            "lognormal_factor_uncertainty_available": True,
            "full_actual_density_or_posterior_samples_available": False,
            "coherent_actual_temperature_draws_reconstructible": False,
            "scalar_lognormal_coherent_approximation_available": True,
            "scalar_lognormal_equation": (
                "rate_j(T)=median_j(T)*factor_uncertainty_j(T)^p_j, "
                "p_j~Normal(0,1), one p_j fixed across T per network run"
            ),
            "cross_temperature_covariance": ("not_published_in_identified_release"),
            "cross_reaction_covariance": ("not_published_in_identified_release"),
            "missing_covariance_is_independence_evidence": False,
        },
        "coordinate": {
            "name": "T9",
            "definition": "T / 1e9 K",
            "units": "GK",
            "grid": common_grid,
            "points": len(common_grid),
            "minimum": min(common_grid),
            "maximum": max(common_grid),
        },
        "reactions": reactions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iop-table-dir", type=Path, required=True)
    parser.add_argument("--arxiv-source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (
        json.dumps(
            build(args.iop_table_dir, args.arxiv_source_root),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
