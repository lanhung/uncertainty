# AGENTS v0.4.0 文档地图与维护规则

本目录保存 `lanhung/uncertainty` 的科研治理、执行、计算验证、投稿与集群运行规范。

## 规范性文件

以下文件共同构成当前长期规范：

1. [`/AGENTS.md`](../../AGENTS.md)：项目使命、科学假设、竞争边界、推断基线、冻结条件与总入口；
2. [`../science/UNCERTAINTY_SCOPE_v1.md`](../science/UNCERTAINTY_SCOPE_v1.md)：本仓库唯一主动科学问题——BBN 核反应率不确定度传播、分布学习与边缘化；
3. [`EXECUTION.md`](EXECUTION.md)：角色 A00–A12、预注册、Fisher Gate、solver/rate matrix 与 Nature Route Gate；
4. [`COMPUTE_VALIDATION.md`](COMPUTE_VALIDATION.md)：共享 Vultr、弹性 AutoDL、成本账本、统计校准、物理验证与独立复现；
5. [`PUBLICATION.md`](PUBLICATION.md)：潜在论文路线与发布检查；
6. [`/AGENTS-ops.md`](../../AGENTS-ops.md)：任务 ledger、heartbeat、checkpoint、detached 运行、资源 lease、状态快照和密钥安全。

发生冲突时，以根级 `AGENTS.md` 和 `ADR-0006` 为准。任何分卷都不得自行把 JCAP 稿件、SGWB、lithium no-go 或通用 ML benchmark 放回本项目的关键路径。

## 当前执行优先级

当前 desired state 由以下文件定义：

- [`ADR-0006-uncertainty-core-refocus.md`](../decisions/ADR-0006-uncertainty-core-refocus.md)：纠正 manuscript-first 偏移并冻结 UQ-only 主线；
- [`UNCERTAINTY_SCOPE_v1.md`](../science/UNCERTAINTY_SCOPE_v1.md)：定义生成模型、反应率分层、推断模型和验证阈值；
- [`SCIENCE_CRITICAL_PATH_v3.md`](../ops/SCIENCE_CRITICAL_PATH_v3.md)：从 R0 rate prior、直接 Monte Carlo 理论带、16 点 smoke 到 64 点正式 Gate 的执行顺序；
- [`plan/plan.yaml`](../../plan/plan.yaml)：当前唯一 desired state。

当前顺序为：

```text
自包含 solver/rate prior
-> 固定点 direct Monte Carlo bands
-> 16 点 covariance-drift smoke
-> 64 点 Fisher/response Gate
-> 条件性 emulator 与 posterior campaign
```

## 明确的非依赖项

以下工作与本仓库可能有科学背景联系，但不是 active dependency：

- 即将投稿的 JCAP stiff/SGWB 论文；
- BBNet+/SageNet+ 稿件资产发布；
- stiff-phase lithium no-go 复现；
- SGWB likelihood 与 detector forecast；
- 通用 ABCMB full audit；
- 与当前 UQ Gate 无关的 LINX gradient debugging；
- 第二台 AutoDL 的持续在线；
- Nature Machine Intelligence / Nature Computational Science benchmark campaign。

历史 `ADR-0005` 和 `SCIENCE_CRITICAL_PATH_v2` 仅用于记录已被纠正的短期决策，不得作为当前执行入口。

## 数据和资产边界

- `configs/data/abundance_OBS-v1.yaml`：未来 cosmological UQ inference 的预注册 observation registry；
- `configs/physics/nuclear_stage0_R0_v1.yaml`：当前 R0 最小核反应率 nuisance contract；
- 旧稿件配置不属于 active tree；
- 原始会议 PDF、稿件 PDF 与私有资产未经许可不进入公开仓库；
- solver、rate table、checkpoint、dataset 和 chain 均须记录 revision、license、hash、schema 与生成来源。

从零重建是允许的。若使用公开 LINX、PRyMordial、PRIMAT、PArthENoPE 或 AlterBBN 重新生成数据，必须标为 clean-room scientific implementation，并且所有监督标签必须来自批准的物理 solver。

## 修改流程

任何重大科学、计算或运行策略修改必须：

1. 新建或更新 `docs/decisions/ADR-*.md`；
2. 明确受影响的任务、数据冻结、统计阈值、资源上限和停止条件；
3. 更新根级 `AGENTS.md` 与相应分卷；
4. 更新 `plan/plan.yaml` 并运行 plan validation 与 `taskctl reconcile`；
5. 在 PR 中说明科学原因和验证方式；
6. 解盲后的变化进入 deviation log。

## 当前重要决策

- [`ADR-0002-ode-compute-model.md`](../decisions/ADR-0002-ode-compute-model.md)：高保真核心仍是 BBN ODE/反应网络，执行上不采用盲目的百维暴力采样；
- [`ADR-0003-research-ops-control-plane.md`](../decisions/ADR-0003-research-ops-control-plane.md)：ledger 与 heartbeat/checkpoint；
- [`ADR-0004-shared-control-elastic-autodl.md`](../decisions/ADR-0004-shared-control-elastic-autodl.md)：共享 Vultr 与弹性 AutoDL；
- [`ADR-0005-manuscript-baseline-self-contained-pivot.md`](../decisions/ADR-0005-manuscript-baseline-self-contained-pivot.md)：**Superseded for active priority**；
- [`ADR-0006-uncertainty-core-refocus.md`](../decisions/ADR-0006-uncertainty-core-refocus.md)：当前科学优先级；
- [`../ops/CLUSTER_RUNBOOK.md`](../ops/CLUSTER_RUNBOOK.md)：集群部署与恢复；
- [`../ops/SCIENCE_CRITICAL_PATH_v3.md`](../ops/SCIENCE_CRITICAL_PATH_v3.md)：当前科学关键路径。
