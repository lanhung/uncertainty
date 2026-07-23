# AGENTS v0.4.1 文档地图与维护规则

本目录保存 `lanhung/uncertainty` 的科研治理、执行、计算验证、投稿与集群运行规范。

## 规范性文件

以下文件共同构成当前长期规范：

1. [`/AGENTS.md`](../../AGENTS.md)：项目使命、科学假设、竞争边界、推断基线、冻结条件与总入口；
2. [`../science/UNCERTAINTY_SCOPE_v1.md`](../science/UNCERTAINTY_SCOPE_v1.md)：本仓库唯一主动科学问题——BBN 核反应率不确定度传播、分布学习与边缘化；
3. [`../literature/FRONTIER_REVIEW_2026-07.md`](../literature/FRONTIER_REVIEW_2026-07.md)：截至 2026-07 的前沿事实、重复造轮子风险、强制 baseline、claim blacklist 与最小候选贡献；
4. [`../literature/COMPETITOR_MATRIX_v1.md`](../literature/COMPETITOR_MATRIX_v1.md)：BBN solver、核反应概率产品与 nuisance-SBI 的竞争矩阵；
5. [`EXECUTION.md`](EXECUTION.md)：角色 A00–A12、预注册、Fisher Gate、solver/rate matrix 与 Nature Route Gate；
6. [`COMPUTE_VALIDATION.md`](COMPUTE_VALIDATION.md)：共享 Vultr、弹性 AutoDL、成本账本、统计校准、物理验证与独立复现；
7. [`PUBLICATION.md`](PUBLICATION.md)：潜在论文路线与发布检查；
8. [`/AGENTS-ops.md`](../../AGENTS-ops.md)：任务 ledger、heartbeat、checkpoint、detached 运行、资源 lease、状态快照和密钥安全。

发生冲突时，以根级 `AGENTS.md`、`ADR-0006`、`ADR-0007` 和 `ADR-0008` 为准。任何分卷都不得自行把 JCAP 稿件、SGWB、lithium no-go 或未经 Gate 授权的通用 ML benchmark 放回本项目关键路径，也不得把已经存在的 BBN Monte Carlo、scalar rate marginalization、standard sensitivity ranking 或 deuterium GP 包装为首创。

## 当前执行优先级

当前 desired state 由以下文件定义：

- [`ADR-0006-uncertainty-core-refocus.md`](../decisions/ADR-0006-uncertainty-core-refocus.md)：纠正 manuscript-first 偏移并冻结 UQ-only 主线；
- [`ADR-0007-frontier-literature-2026-07.md`](../decisions/ADR-0007-frontier-literature-2026-07.md)：根据 ETR25、PRIMAT native MC、PRyMordial/LINX、2026 sensitivity/GP 和 nuisance-SBI 前沿重排任务；
- [`ADR-0008-self-contained-fast-track.md`](../decisions/ADR-0008-self-contained-fast-track.md)：将 atlas/GP 精确复现从生产依赖链拆出，冻结自包含 reference-prior 与低成本里程碑；
- [`UNCERTAINTY_SCOPE_v1.md`](../science/UNCERTAINTY_SCOPE_v1.md)：定义生成模型、核 PDF、反应率分层、推断模型和验证阈值；
- [`SCIENCE_CRITICAL_PATH_v4.md`](../ops/SCIENCE_CRITICAL_PATH_v4.md)：当前自包含科学关键路径；
- [`FAST_TRACK_MILESTONES_v1.md`](../ops/FAST_TRACK_MILESTONES_v1.md)：9 点、81 点、5 点漂移和一维 posterior 的事件式执行规范；
- [`plan/plan.yaml`](../../plan/plan.yaml)：当前唯一 desired state，版本 6。

当前顺序为：

```text
ETR25/public-information reference prior
-> LINX primary + PRyMordial spot-check adapter
-> 9-point response smoke
-> 81-node direct joint abundance distribution
-> five-point omega_b_h2 covariance drift
-> U-M0/U-M1/U-M2 direct posterior grid
-> fast stop/scale decision
-> conditional 16/64-point, broader rates or learned model
```

## 外部复现与生产依赖边界

以下两项保留为冻结的外部论文审计，但不再阻塞项目自有计算：

- 2026 sensitivity-atlas exact slice reproduction；
- 2026 GP deuterium exact abundance-distribution reproduction。

其失败或阻塞证据不得被改写成通过，也不得通过放宽原阈值获得 credit。原因是公开材料缺少 generator/configuration 或 code/hyperparameters/data/draws/seed。项目允许使用新项目 ID 做 clean-room alternative，但不得称为 exact reproduction。

当前 fast path 使用 `configs/physics/nuclear_prior_R0_reference_v1.yaml`。它是公开信息条件下的 reference-prior family，不是完整实验核后验。出版级无条件主张仍需要核数据审查、科学负责人和独立验证签字。

## 明确的非依赖项与非首创项

以下工作与本仓库可能有背景联系，但不是 active dependency：

- 即将投稿的 JCAP stiff/SGWB 论文；
- BBNet+/SageNet+ 稿件资产发布；
- stiff-phase lithium no-go 复现；
- SGWB likelihood 与 detector forecast；
- 通用 ABCMB full audit；
- 与当前 UQ Gate 无关的 LINX gradient debugging；
- 第二台 AutoDL 的持续在线；
- Nature Machine Intelligence / Nature Computational Science benchmark campaign。

以下结果是 baseline，不得称为本项目首创：

- BBN nuclear-rate Monte Carlo 与 Schramm theoretical bands；
- log-normal scalar rate nuisance；
- PRyMordial explicit marginalization；
- LINX differentiable/joint CMB+BBN rate marginalization；
- 三个 deuterium reactions 的标准敏感性与 GP 建模；
- standard-BBN 63-rate sensitivity atlas；
- 普通 deterministic BBN emulator；
- generic flow/TMNRE/AMNRE nuisance marginalization。

历史 `ADR-0005`、`SCIENCE_CRITICAL_PATH_v2` 和 `SCIENCE_CRITICAL_PATH_v3` 仅用于记录已被纠正的短期决策，不得作为当前执行入口。

## 数据和资产边界

- `configs/data/abundance_OBS-v1.yaml`：cosmological UQ inference 的预注册 observation registry；
- `configs/physics/nuclear_stage0_R0_v1.yaml`：R0 核反应率 actual/posterior 与 scalar-lognormal nuisance contract；
- `configs/physics/nuclear_prior_R0_reference_v1.yaml`：当前可执行的自包含 reference-prior family；
- `configs/literature/frontier_sources_2026-07.yaml`：当前前沿 source registry；
- ETR25、RatesMC、solver、rate table、posterior sample、dataset 和 chain 均须记录 revision、license、hash、schema 与生成来源；
- 同一 nuclear-input draw 必须产生 coherent temperature-dependent rate curve；
- 旧稿件配置不属于 active tree；
- 原始会议 PDF、稿件 PDF 与私有资产未经许可不进入公开仓库。

从零重建是允许的。若使用公开 LINX、PRyMordial、PRIMAT、PArthENoPE 或 AlterBBN 重新生成数据，必须标为 clean-room scientific implementation，并且所有监督标签必须来自批准的物理 solver。

## 修改流程

任何重大科学、计算或运行策略修改必须：

1. 新建或更新 `docs/decisions/ADR-*.md`；
2. 明确受影响的任务、数据冻结、统计阈值、资源上限和停止条件；
3. 更新根级 `AGENTS.md` 或在不冲突时登记新的优先级 ADR；
4. 更新 `plan/plan.yaml` 并运行 plan validation 与 `taskctl reconcile`；
5. 在 PR 中说明科学原因和验证方式；
6. 解盲后的变化进入 deviation log；
7. 每月刷新前沿检索，并在新竞争工作改变 claim boundary 时立即重开 novelty review。

## 当前重要决策

- [`ADR-0002-ode-compute-model.md`](../decisions/ADR-0002-ode-compute-model.md)：高保真核心仍是 BBN ODE/反应网络，执行上不采用盲目的百维暴力采样；
- [`ADR-0003-research-ops-control-plane.md`](../decisions/ADR-0003-research-ops-control-plane.md)：ledger 与 heartbeat/checkpoint；
- [`ADR-0004-shared-control-elastic-autodl.md`](../decisions/ADR-0004-shared-control-elastic-autodl.md)：共享 Vultr 与弹性 AutoDL；
- [`ADR-0005-manuscript-baseline-self-contained-pivot.md`](../decisions/ADR-0005-manuscript-baseline-self-contained-pivot.md)：**Superseded for active priority**；
- [`ADR-0006-uncertainty-core-refocus.md`](../decisions/ADR-0006-uncertainty-core-refocus.md)：UQ-only 科学优先级；
- [`ADR-0007-frontier-literature-2026-07.md`](../decisions/ADR-0007-frontier-literature-2026-07.md)：当前前沿、核 PDF 与强制 baseline 决策；
- [`ADR-0008-self-contained-fast-track.md`](../decisions/ADR-0008-self-contained-fast-track.md)：自包含 reference-prior、外部复现解耦和快速里程碑；
- [`../ops/CLUSTER_RUNBOOK.md`](../ops/CLUSTER_RUNBOOK.md)：集群部署与恢复；
- [`../ops/SCIENCE_CRITICAL_PATH_v4.md`](../ops/SCIENCE_CRITICAL_PATH_v4.md)：当前科学关键路径。
