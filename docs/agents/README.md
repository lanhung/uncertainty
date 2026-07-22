# AGENTS v0.2.x 文档地图与维护规则

本目录保存 `lanhung/uncertainty` 的科研治理、执行、计算验证、投稿与集群运行规范。

## 规范性文件

以下五个文件共同构成当前长期规范：

1. [`/AGENTS.md`](../../AGENTS.md)：项目使命、科学假设、竞争边界、推断基线、冻结条件与总入口；
2. [`EXECUTION.md`](EXECUTION.md)：角色 A00–A12、Phase 0–9、预注册、Fisher Gate、solver/rate matrix 与 Nature Route Gate；
3. [`COMPUTE_VALIDATION.md`](COMPUTE_VALIDATION.md)：共享 Vultr 控制宿主机、按需 AutoDL/CPU/GPU 资源、成本账本、统计校准、物理验证与独立复现标准；
4. [`PUBLICATION.md`](PUBLICATION.md)：Nature Astronomy、Nature Computational Science、Nature Machine Intelligence、Nature Communications 路线，里程碑和发布检查；
5. [`/AGENTS-ops.md`](../../AGENTS-ops.md)：多项目 Vultr 控制宿主机、跨项目共享 AutoDL/HPC worker、任务 ledger、heartbeat、checkpoint、detached 运行、资源 lease、状态快照和密钥安全。

发生冲突时，以根级 `AGENTS.md` 为准。任何分卷都不得自行降低预注册、校准、独立验证、停止条件或资源 Gate。预计超过 60 秒的任务还必须遵守 `AGENTS-ops.md`。

## 当前执行优先级

待投四丰度 stiff-phase JCAP 稿件提供了新的、成熟度更高的科学基线。当前 desired-state 由以下两份文件定义：

- [`ADR-0005-manuscript-baseline-self-contained-pivot.md`](../decisions/ADR-0005-manuscript-baseline-self-contained-pivot.md)：采用稿件作为 Track A baseline，允许作者资产 handoff 或 clean-room 自包含重建，并把近期 Track B 收缩为 nuclear-UQ 对 lithium no-go 的稳健性检验；
- [`SCIENCE_CRITICAL_PATH_v2.md`](../ops/SCIENCE_CRITICAL_PATH_v2.md)：72 小时资产/物理合同、七天复现、投稿 release 和 16 点 scalar-UQ smoke 的执行顺序。

`plan/plan.yaml` 是当前唯一 desired state。旧的 ABCMB full audit、通用 LINX gradient audit、W0–W3 challenge、Pilot-1k/Pilot-10k 和通用 Nature-method campaign 已从 active plan 移除；它们仍保留在 Git 历史中，仅在新的 Gate 决定后恢复。

## 数据层边界

- `configs/data/manuscript_abundance_v1.yaml`：只用于精确复现待投 JCAP 稿件；
- `configs/data/abundance_OBS-v1.yaml`：用于后续 nuclear-UQ 工作的预注册主数据与 stress tests；
- 两个 registry 不得互相静默替换。

## 对话生成文件与公开仓库边界

完整审计见 [`docs/ops/GENERATED_ARTIFACTS_AUDIT.md`](../ops/GENERATED_ARTIFACTS_AUDIT.md)。原则如下：

- 各类交付 ZIP 是可再生成快照，不作为第二套事实来源提交普通 Git 历史；
- 真实 `hosts.local.env`、个人 SSH config 和机器专用 wrapper 只保存在操作者/Vultr 本地；
- 会议逐字稿与原始项目 PDF 属于内部来源材料，未经隐私、作者与许可审查不得上传公开仓库；
- bearer token、Tailscale auth key、密码和 SSH 私钥不得进入 Git、issue、prompt、日志或 bundle。

论文相关的源代码、weights、scalers、chains 和 scan tables 应通过可审计 handoff、GitHub Release 或 Zenodo 进入公开发布；不得因为它们来自作者本人就绕过 hash、license、schema 和环境检查。

## 修改流程

任何重大科学、计算或运行策略修改必须：

1. 新建或更新 `docs/decisions/ADR-*.md`；
2. 明确受影响的任务编号、数据冻结、统计阈值、资源上限和停止条件；
3. 更新根级 `AGENTS.md`、`AGENTS-ops.md` 或对应规范分卷；
4. 更新 `plan/plan.yaml` 并运行 plan validation 与 `taskctl reconcile`；
5. 在 commit/PR 中说明变更原因和验证方式；
6. 若变更发生在解盲后，必须登记到 deviation log。

## 当前重要决策

- [`ADR-0002-ode-compute-model.md`](../decisions/ADR-0002-ode-compute-model.md)：高保真核心仍是 BBN ODE/反应网络，执行上不采用盲目的百维暴力采样；
- [`ADR-0003-research-ops-control-plane.md`](../decisions/ADR-0003-research-ops-control-plane.md)：项目 ledger、独立 `ops-status` 分支与 heartbeat/checkpoint；
- [`ADR-0004-shared-control-elastic-autodl.md`](../decisions/ADR-0004-shared-control-elastic-autodl.md)：共享 Vultr 与弹性 AutoDL worker pool；
- [`ADR-0005-manuscript-baseline-self-contained-pivot.md`](../decisions/ADR-0005-manuscript-baseline-self-contained-pivot.md)：稿件 baseline、自包含重建、core-6 scalar UQ 与 manuscript-first priority；
- [`../ops/CLUSTER_RUNBOOK.md`](../ops/CLUSTER_RUNBOOK.md)：集群部署与恢复；
- [`../ops/SCIENCE_CRITICAL_PATH_v2.md`](../ops/SCIENCE_CRITICAL_PATH_v2.md)：当前科学关键路径。
