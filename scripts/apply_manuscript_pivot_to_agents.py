#!/usr/bin/env python3
"""Idempotently align the root AGENTS charter with ADR-0005."""
from __future__ import annotations

from pathlib import Path


path = Path("AGENTS.md")
text = path.read_text(encoding="utf-8")

text = text.replace(
    "> 版本：**0.2.1**  ",
    "> 版本：**0.3.0**  ",
    1,
)
text = text.replace(
    "> 状态：**Track A = ACTIVE；Track B = NOT FROZEN；Nature-tier Gate = CLOSED**  ",
    "> 状态：**JCAP manuscript freeze = ACTIVE；UQ sequel = PRESCREEN；Nature-tier Gate = CLOSED**  ",
    1,
)
text = text.replace(
    "> 基准日期：2026-07-21  ",
    "> 基准日期：2026-07-23  ",
    1,
)
text = text.replace(
    "> 本版替代：v0.2.0",
    "> 本版替代：v0.2.x",
    1,
)

old_summary = """## v0.2.1 变更摘要

v0.2.1 完整保留 v0.2.0 的科学战略，并将其接入可长期运行的集群控制面；v0.2.x 系列完成以下修订："""
new_summary = """## v0.3.0 变更摘要

v0.3.0 根据待投四丰度 stiff-phase JCAP 稿件重排科学关键路径：

1. 将 BBNet+ + SageNet+ + stiff-SGWB 稿件定义为当前 Track A 的真实科学 baseline；
2. 当前最高优先级改为作者资产 handoff、公开 release、干净环境复现和 JCAP 投稿冻结；
3. 近期 UQ 问题收缩为“核/弱/backend 不确定度是否改变 homogeneous stiff phase 的 lithium no-go”；
4. 首批 scalar-UQ 反应集合改为三个 deuterium reactions 加三个 Be7/Li7 flow reactions；
5. 允许使用公开 solver 进行 clean-room 自包含重建，但必须与原资产恢复明确区分；
6. 16 点 engineering smoke 先于正式 64 点 Fisher Gate；Gate 前不激活 Pilot-1k、Pilot-10k 或 Nature-method campaign；
7. `MANUSCRIPT-OBS-v1` 与后续 UQ 的 `OBS-v1` 严格分层，不得静默混用；
8. Nature Machine Intelligence 与 Nature Computational Science 路线暂时 dormant。

详细决策见 `docs/decisions/ADR-0005-manuscript-baseline-self-contained-pivot.md`，当前 desired state 见 `plan/plan.yaml`。

### v0.2.x 保留的长期治理与验证原则

v0.2.x 建立的竞争基线、预注册、Fisher Gate、多 solver 验证和集群控制面继续有效："""
if old_summary in text:
    text = text.replace(old_summary, new_summary, 1)

old_track_a = """#### Track A — 基础冻结与风险隔离线

目的：完成现有 BBNet/扩展 BBN 工作，建立可靠基础，不允许被 Track B 无限拖延。

最低交付：

- deterministic emulator 复现；
- hard/soft 外推策略的十维后验比较；
- 多链收敛、后验预测和可复现 release；
- `n_t` 自由与 inflationary consistency relation；
- `kappa`、`n_t`、`T_re` 的条件响应和全边缘化可辨识性；
- Schramm-style 物理切片；
- 至少两个现有 solver 的工程交叉检查。

Track A 可以形成独立论文。它是 Track B 的可验证地基，不是 Nature 级主张的替代品。"""
new_track_a = """#### Track A — 四丰度 JCAP 稿件冻结与公开复现线

目的：冻结并提交已经形成的 BBNet+ + SageNet+ + stiff-SGWB 四丰度分析，不允许被后续核反应率 UQ 或通用 ML 方法无限拖延。

最低交付：

- 精确登记 `kappa10 = rho_stiff/rho_gamma` at `T=10 MeV` 及 stiff/SGWB/reheating 参数合同；
- 四丰度 BBNet+ 代码、weights、scalers、训练配置与数据 lineage；
- modified PArthENoPE/AlterBBN source、patch 或准确的受限可用性说明；
- clean-environment emulator accuracy、main posterior、partial-likelihood 与 deterministic no-go reproduction；
- hard/soft、consistency relation、free-`Delta N_eff` 与 free-`kappa10` diagnostics 的可追溯配置；
- tagged GitHub release、Zenodo chain/scan archive、checksums 与可验证的数据/软件可用性陈述。

Track A 的当前目标是 JCAP 投稿。它不等待完整 nuclear-rate UQ；后者是独立续篇。"""
if old_track_a in text:
    text = text.replace(old_track_a, new_track_a, 1)

text = text.replace(
    "- `y`：轻元素丰度向量，至少包括 `Y_p`、`D/H`；`Li/H` 默认仅作为独立 null test。",
    "- `y`：轻元素丰度向量，包括 `Y_p`、`D/H`、`3He/H`、`7Li/H`；稿件 stratum 中 lithium 是被检验的 no-go endpoint，后续 UQ stratum 的具体 likelihood 由数据 registry 决定。",
    1,
)

old_candidates = """首批候选至少包括：

- `d(p,gamma)3He`；
- `d(d,n)3He`；
- `d(d,p)t`。

如 Li null test 需要，可追加 `3He(alpha,gamma)7Be`、`7Be(n,p)7Li` 等，但不得让 Li 路线拖慢主项目。"""
new_candidates = """首批 decision-focused scalar-UQ 集合固定为：

- `d(p,gamma)3He`；
- `d(d,n)3He`；
- `d(d,p)t`；
- `3He(alpha,gamma)7Be`；
- `7Be(n,p)7Li`；
- `7Li(p,alpha)4He`。

函数型模式只为 scalar smoke/Fisher 显示会改变 lithium no-go endpoint 的反应构造，不因历史习惯预先固定。"""
if old_candidates in text:
    text = text.replace(old_candidates, new_candidates, 1)

old_status_heading = "### 0.5 当前状态与 Track B 冻结阻塞项"
new_status_heading = """### 0.5 当前 manuscript-first 执行覆盖

当前任务顺序由 `ADR-0005` 与 `docs/ops/SCIENCE_CRITICAL_PATH_v2.md` 约束：

```text
JCAP asset/release/reproduction
> self-contained core-6 scalar smoke
> formal 64-point Fisher Gate
> conditional Pilot/Nature campaign
```

第二台 AutoDL、ABCMB full audit、通用 LINX gradient audit、W0–W3 challenge 和新 ML architecture 都不是当前科学关键路径。`plan/plan.yaml` 中不存在的 conditional task 不得提前启动。

### 0.6 当前状态与 Track B 冻结阻塞项"""
if old_status_heading in text:
    text = text.replace(old_status_heading, new_status_heading, 1)

path.write_text(text, encoding="utf-8")
