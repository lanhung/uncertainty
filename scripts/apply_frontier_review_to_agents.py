#!/usr/bin/env python3
"""Idempotently align AGENTS.md with the July 2026 frontier review."""
from __future__ import annotations

from pathlib import Path


PATH = Path("AGENTS.md")

FRONTIER_BLOCK = """### v0.4.1 前沿审计约束

截至 2026-07 的系统检索已经确认：PRIMAT 原生 Monte Carlo、PRyMordial 显式反应率边缘化、LINX 可微 BBN 与联合 CMB+BBN 核反应率边缘化、63-rate sensitivity atlas、三个头部氘反应的 Gaussian-process 建模以及 TMNRE/AMNRE 类 nuisance marginalization 均已有公开基线。详细证据见 `docs/literature/FRONTIER_REVIEW_2026-07.md` 与 `ADR-0007-frontier-literature-2026-07.md`。

因此当前最高优先级是：

1. 以 ETR25 或原始核数据 posterior 为起点，保留 coherent temperature-dependent rate curves；
2. 比较 actual/posterior rate PDF、scalar log-normal approximation 与 solver legacy envelope；
3. 先复现 PRIMAT/PRyMordial/LINX 的直接不确定度功能，再实现自定义 production driver；
4. 把 fixed-point Schramm band 明确视为校准基线，候选新对象是 parameter-dependent joint abundance distribution 与 fixed `C_th` 的有效/失效图；
5. Gate 后方法比较必须包含简单 multivariate baselines、TMNRE/AMNRE、prior/posterior SBC、local calibration、multiple seeds 与 direct fallback。

不得将 Monte Carlo 理论带、scalar `q_i`、标准 BBN 显式边缘化、标准 sensitivity ranking、三个氘反应的 GP 或普通 BBN emulator 称为本项目首创。"""

OLD_SEQUENCE = """public solver + R0 rate prior
> direct Monte Carlo theoretical bands
> 16-point covariance-drift smoke
> formal 64-point Gate
> conditional learned-model / full-network expansion"""
NEW_SEQUENCE = """frontier review + ETR25 R0 actual-PDF audit
> PRIMAT / PRyMordial / LINX native uncertainty reproduction
> coherent public-solver rate prior and nuisance adapter
> direct Monte Carlo theoretical bands
> 16-point covariance / quantile / tail drift smoke
> formal 64-point novelty and method-necessity Gate
> conditional learned-model / full-network expansion"""

OLD_RATE_TEXT = "其中 `q_i` 是一个标量，表示沿已给定温度依赖误差包络的整体位移。该参数化是基线接口，不构成方法创新。"
NEW_RATE_TEXT = """其中 `q_i` 是一个标量，表示沿已给定温度依赖误差包络的整体位移。该参数化是基线接口，不构成方法创新。ETR25 的 low/median/high 来自 actual rate PDF 的百分位，而 factor uncertainty 使用 log-normal approximation；两者必须在 BBN 温区和最终 abundance/posterior 层面比较。每个 nuclear-input draw 必须生成跨温度 coherent 的 rate curve，禁止无协方差依据的独立 temperature-bin noise。"""


def main() -> None:
    text = PATH.read_text(encoding="utf-8")

    if "> 版本：**0.4.0**" in text:
        text = text.replace("> 版本：**0.4.0**", "> 版本：**0.4.1**", 1)
    elif "> 版本：**0.4.1**" not in text:
        raise RuntimeError("AGENTS.md is not the expected v0.4.x charter")

    while text.count(FRONTIER_BLOCK) > 1:
        first = text.find(FRONTIER_BLOCK)
        second = text.find(FRONTIER_BLOCK, first + len(FRONTIER_BLOCK))
        text = text[:second] + text[second + len(FRONTIER_BLOCK):]
        text = text.replace("\n\n\n", "\n\n")

    if FRONTIER_BLOCK not in text:
        marker = "详细纠偏见 `docs/decisions/ADR-0006-uncertainty-core-refocus.md`。"
        if marker not in text:
            raise RuntimeError("missing ADR-0006 insertion marker")
        text = text.replace(marker, marker + "\n\n" + FRONTIER_BLOCK, 1)

    if OLD_SEQUENCE in text:
        text = text.replace(OLD_SEQUENCE, NEW_SEQUENCE, 1)
    elif NEW_SEQUENCE not in text:
        raise RuntimeError("missing UQ execution sequence")

    if OLD_RATE_TEXT in text:
        text = text.replace(OLD_RATE_TEXT, NEW_RATE_TEXT, 1)
    elif NEW_RATE_TEXT not in text:
        raise RuntimeError("missing scalar-rate baseline paragraph")

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
