#!/usr/bin/env python3
"""Remove duplicated frontier text and over-specific pending ETR25 metadata."""
from __future__ import annotations

from pathlib import Path


AGENTS = Path("AGENTS.md")
R0 = Path("configs/physics/nuclear_stage0_R0_v1.yaml")

RATE_SUFFIX = (
    "ETR25 的 low/median/high 来自 actual rate PDF 的百分位，而 factor uncertainty 使用 "
    "log-normal approximation；两者必须在 BBN 温区和最终 abundance/posterior 层面比较。"
    "每个 nuclear-input draw 必须生成跨温度 coherent 的 rate curve，禁止无协方差依据的"
    "独立 temperature-bin noise。"
)

OLD_CLASSIFICATION = "ETR25_rate_type: Bayesian_rate_adopted_with_registered_modifications"
NEW_CLASSIFICATION = "ETR25_rate_type: pending_exact_ETR25_source_classification"


def main() -> None:
    agents = AGENTS.read_text(encoding="utf-8")
    while RATE_SUFFIX + RATE_SUFFIX in agents:
        agents = agents.replace(RATE_SUFFIX + RATE_SUFFIX, RATE_SUFFIX)
    agents = agents.replace("\n\n\n### v0.2.x", "\n\n### v0.2.x")
    if agents.count(RATE_SUFFIX) != 1:
        raise RuntimeError(f"expected one ETR25 scalar-rate paragraph, found {agents.count(RATE_SUFFIX)}")
    if agents.count("### v0.4.1 前沿审计约束") != 1:
        raise RuntimeError("frontier block is not unique")
    AGENTS.write_text(agents, encoding="utf-8")

    r0 = R0.read_text(encoding="utf-8")
    if OLD_CLASSIFICATION in r0:
        r0 = r0.replace(OLD_CLASSIFICATION, NEW_CLASSIFICATION)
    if r0.count(NEW_CLASSIFICATION) != 3:
        raise RuntimeError(
            "expected three pending ETR25 source classifications, "
            f"found {r0.count(NEW_CLASSIFICATION)}"
        )
    if OLD_CLASSIFICATION in r0:
        raise RuntimeError("over-specific ETR25 classification remains")
    R0.write_text(r0, encoding="utf-8")


if __name__ == "__main__":
    main()
