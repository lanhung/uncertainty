#!/usr/bin/env python3
"""Idempotently refocus the root charter on BBN nuclear-rate uncertainty."""
from __future__ import annotations

from pathlib import Path


PATH = Path("AGENTS.md")


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    i = text.find(start)
    if i < 0:
        raise RuntimeError(f"missing start marker: {start}")
    j = text.find(end, i + len(start))
    if j < 0:
        raise RuntimeError(f"missing end marker: {end}")
    return text[:i] + replacement.rstrip() + "\n\n" + text[j:]


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one occurrence, found {count}: {old[:80]}")
    return text.replace(old, new, 1)


def main() -> None:
    text = PATH.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "> 版本：**0.3.0**  \n> 状态：**JCAP manuscript freeze = ACTIVE；UQ sequel = PRESCREEN；Nature-tier Gate = CLOSED**  \n> 基准日期：2026-07-23  ",
        "> 版本：**0.4.0**  \n> 状态：**BBN nuclear-rate UQ = ACTIVE；non-standard applications = CONDITIONAL；Nature-tier Gate = CLOSED**  \n> 基准日期：2026-07-23  ",
    )
    text = replace_once(text, "> 本版替代：v0.2.x", "> 本版替代：v0.3.0；ADR-0005 的 manuscript-first 优先级已被 ADR-0006 取代")

    text = replace_between(
        text,
        "## v0.3.0 变更摘要",
        "### v0.2.x 保留的长期治理与验证原则",
        """## v0.4.0 变更摘要

v0.4.0 纠正了把独立 JCAP 稿件放入本仓库关键路径的范围偏移，并重新冻结原始科学目标：

1. 本仓库唯一主动主线是 BBN 核反应率不确定度传播、丰度分布学习与 nuisance marginalization；
2. 即将投稿的 JCAP stiff/SGWB 稿件、SageNet、lithium no-go 与稿件资产发布均为本项目非依赖项；
3. 允许完全使用公开 solver 和 rate data 从零构建 self-contained clean-room pipeline，不等待私有旧资产；
4. 第一阶段从三个 deuterium rates 与独立 weak nuisance 开始，先测量 Monte Carlo 理论带、相关性和收敛；
5. 先生成 fixed-point direct theoretical bands，再做 16 点 covariance-drift smoke 和正式 64 点 Gate；
6. 强制比较 central-rate、constant-sigma、direct marginalization、conditional forward emulator 与 learned marginal distribution；
7. Pilot-1k/Pilot-10k、full-network、函数型 rates、非标准宇宙学与 Nature campaign 均须由 Gate 授权；
8. 当前执行入口为 `ADR-0006`、`docs/science/UNCERTAINTY_SCOPE_v1.md`、`SCIENCE_CRITICAL_PATH_v3.md` 和 `plan/plan.yaml`。

详细纠偏见 `docs/decisions/ADR-0006-uncertainty-core-refocus.md`。""",
    )

    text = replace_once(
        text,
        "> **在完整传播函数型核反应率不确定度、弱反应不确定度和多 solver discrepancy 后，BBN 对非标准膨胀历史、刚性后暴胀时期、蓝倾张量谱与可观测随机引力波背景的结论是否发生此前未被认识的改变？**",
        "> **给定宇宙学参数后，核反应率与弱反应 nuisance variables 通过 BBN ODE 网络诱导的完整丰度分布是什么；常数理论误差近似何时会使丰度区间或宇宙学后验发生可测偏差？**",
    )
    text = replace_once(
        text,
        "> **能否在具有高维 nuisance variables、函数型输入、多保真 stiff-ODE solver 和昂贵后验校准的科学推断中，以可验证的误差控制显著减少高保真模拟调用？**",
        "> **能否用经过 coverage、posterior recovery 和 direct-solver fallback 验证的条件模型或分布模型，显著降低高维核反应率边缘化所需的高保真 BBN 求解次数？**",
    )

    text = replace_between(
        text,
        "#### Track A — 四丰度 JCAP 稿件冻结与公开复现线",
        "#### Track B-PA — Physical/Astronomy Discovery Route",
        """#### Track UQ-A — 自包含核反应率不确定度基线

目的：直接解决本仓库的核心问题，不依赖任何独立稿件、SGWB 管线或私有旧 checkpoint。

最低交付：

- 至少三个固定 revision 的公开 BBN solver/reference path；
- 三个 R0 deuterium rates 的中心曲线、误差模型、covariance 状态与 solver mapping；
- neutron lifetime/weak uncertainty 的独立处理；
- 固定标准 BBN 点的 1,000-draw direct Monte Carlo abundance distribution；
- Monte Carlo band convergence 与 Schramm-style 68%/95% theoretical bands；
- 16 点 `C_rate(theta)` 漂移和 non-Gaussian/correlation smoke；
- 正式 64 点 response/Fisher Gate；
- `U-M0` central、`U-M1` constant `C_th` 与 `U-M2` direct marginalization 的定量比较。

Track UQ-A 可以完全从公开 LINX、PRyMordial、PRIMAT、PArthENoPE 或 AlterBBN 重新实现。第一篇核心论文是否需要 emulator，由 direct workload 和 Gate 结果决定，而不是预先假设。""",
    )

    text = replace_between(
        text,
        "### 0.5 当前 manuscript-first 执行覆盖",
        "### 0.6 当前状态与 Track B 冻结阻塞项",
        """### 0.5 当前 UQ-only 执行覆盖

当前任务顺序由 `ADR-0006` 与 `docs/ops/SCIENCE_CRITICAL_PATH_v3.md` 约束：

```text
public solver + R0 rate prior
> direct Monte Carlo theoretical bands
> 16-point covariance-drift smoke
> formal 64-point Gate
> conditional learned-model / full-network expansion
```

以下内容不是当前科学关键路径：独立 JCAP 稿件、SageNet/SGWB、stiff lithium no-go、第二台 AutoDL、ABCMB full audit、通用 LINX gradient audit、W0–W3 challenge、Pilot-10k 和新 ML architecture。`plan/plan.yaml` 中不存在的 conditional task 不得提前启动。""",
    )

    text = replace_once(
        text,
        "- `y`：轻元素丰度向量，包括 `Y_p`、`D/H`、`3He/H`、`7Li/H`；稿件 stratum 中 lithium 是被检验的 no-go endpoint，后续 UQ stratum 的具体 likelihood 由数据 registry 决定。",
        "- `y`：轻元素丰度向量；R0 的主输出为 `Y_p` 与 `D/H`，R1 在 solver/prior 验证后加入 `3He/H` 与 `7Li/H`。",
    )

    text = replace_between(
        text,
        "首批 decision-focused scalar-UQ 集合固定为：",
        "函数基底可来自：",
        """反应率 nuisance 采用分阶段集合：

- `R0`：`d(p,gamma)3He`、`d(d,n)3He`、`d(d,p)t`，并将 `tau_n`/weak physics 单列；
- `R1`：为四丰度加入经过 provenance 与 sensitivity 审计的 `3He/7Be/7Li` 通道；
- `R2`：约 10–20 个 core rates；
- `R3`：full-network stress。

扩维只能由缺失方差、posterior sensitivity、coverage failure 或正式科学终点触发。函数型 rate modes 只在 scalar Gate 显示 `theta` 依赖、tail failure 或 shape sensitivity 后构造。

函数基底可来自：""",
    )

    text = replace_between(
        text,
        "### 1.5 主物理问题",
        "### 1.6 主计算/智能问题",
        """### 1.5 主物理问题

主问题冻结为：

> 对注册的核反应率和弱反应先验，直接 BBN solver 所诱导的 `p(y|theta)` 是否随 `theta` 显著变化、具有重要相关性或非高斯尾部；传统固定 `sigma_th`/`C_th` 近似会在什么区域扭曲 abundance bands 或宇宙学 posterior？

主结果必须报告：

- abundance mean、quantile、covariance、skew/tail 与跨元素 correlation；
- Monte Carlo sample-size convergence；
- `C_rate(theta)` 相对 fiducial 的漂移；
- central、post-hoc 与 direct marginalization 的 posterior 差异；
- 哪些 rate/weak/solver 因素驱动差异；
- 结论跨至少两个 rate compilation 或 solver path 的稳定性。

非标准膨胀、stiff era、SGWB 与 reheating 是 Gate 之后的可选 application，不是本阶段主问题。""",
    )

    text = replace_between(
        text,
        "### 1.6 主计算/智能问题",
        "### 1.7 可证伪假设",
        """### 1.6 主计算/智能问题

方法问题冻结为：

> 在计入训练数据、失败处理和校准成本后，`f(theta,z)` 或 `p(y|theta)` 学习模型能否在 abundance-distribution coverage 与 cosmological posterior fidelity 不下降的前提下，减少 direct nuisance marginalization 的高保真 solver calls 和端到端 wall time？

候选方法不得预先锁定为 GAN、flow、Transformer 或 diffusion。首先比较 deterministic conditional MLP、heteroscedastic/ensemble baseline 与简单 parametric distribution；只有直接数据证明复杂 density model 必要时才升级。""",
    )

    text = replace_between(
        text,
        "#### H2 — 非标准膨胀下敏感性重排与核实验价值",
        "#### H3 — 函数型 rate shape 重要",
        """#### H2 — 丰度分布结构与有效维度

核反应率扰动产生的 abundance distribution 可能具有跨元素相关性、非高斯尾部和随 `theta` 变化的低维 active subspace；这些结构不能由逐元素、固定且独立的 `sigma_th` 完整表示。

成功证据包括：

- `C_rate(theta)` 明显漂移；
- 相关丰度的联合 quantile/coverage 与独立高斯近似显著不同；
- 少数 rate combinations 解释大部分 posterior-relevant variance；
- 在相同 `theta` 下，learned/distributional model 恢复 direct Monte Carlo tails。

仅重新得到标准 BBN 中已知的三个关键氘反应，不算新发现。""",
    )

    text = replace_between(
        text,
        "#### 物理主终点",
        "#### 计算主终点",
        """#### 物理/统计主终点

1. `p(y|theta)` 的 central tendency、68%/95% quantiles、covariance 与 cross-abundance correlation；
2. `C_rate(theta)` 相对 fiducial covariance 的漂移；
3. `U-M1` 相对 `U-M2` 的 normalized posterior shift；
4. credible-interval ratio 与 posterior topology/mode change；
5. posterior predictive 与 simulation-based coverage；
6. rate/weak/solver variance decomposition；
7. Stage R0/R1/R2 的 residual variance 与停止条件。

#### 计算主终点""",
    )

    text = replace_once(
        text,
        "#### 4.1.1 强制基线矩阵",
        "#### 4.1.1 强制基线矩阵\n\n当前 UQ0/R0 的 active paths 使用可公开重建的 solver/reference；任何项目修改版 PArthENoPE/AlterBBN 都是可选验证资产，不得阻塞 direct Monte Carlo theoretical-band 工作。",
    )

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
