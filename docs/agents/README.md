# AGENTS v0.2.2 文档地图与维护规则

本目录保存 `lanhung/uncertainty` 的科研治理、执行、计算验证、投稿与集群运行规范。

## 规范性文件

以下五个文件共同构成当前规范性版本：

1. [`/AGENTS.md`](../../AGENTS.md)：项目使命、科学假设、竞争边界、推断基线、冻结条件与总入口；
2. [`EXECUTION.md`](EXECUTION.md)：角色 A00–A12、Phase 0–9、预注册、Fisher Gate、solver/rate matrix 与 Nature Route Gate；
3. [`COMPUTE_VALIDATION.md`](COMPUTE_VALIDATION.md)：共享 Vultr 控制宿主机、按需 AutoDL/CPU/GPU 资源、成本账本、统计校准、物理验证与独立复现标准；
4. [`PUBLICATION.md`](PUBLICATION.md)：Nature Astronomy、Nature Computational Science、Nature Machine Intelligence、Nature Communications 路线，里程碑、首个 14 天和发布检查；
5. [`/AGENTS-ops.md`](../../AGENTS-ops.md)：多项目 Vultr 控制宿主机、跨项目共享 AutoDL/HPC worker、任务 ledger、heartbeat、checkpoint、detached 运行、资源 lease、状态快照和密钥安全。

发生冲突时，以根级 `AGENTS.md` 为准。任何分卷都不得自行降低预注册、校准、独立验证、停止条件或资源 Gate。预计超过 60 秒的任务还必须遵守 `AGENTS-ops.md`；不得以未读取运行规范为理由把进度留在 Codex、SSH 或 tmux 会话中。

## 对话生成文件与公开仓库边界

完整审计见 [`docs/ops/GENERATED_ARTIFACTS_AUDIT.md`](../ops/GENERATED_ARTIFACTS_AUDIT.md)。原则如下：

- `AGENTS.full.v0.2.0.md` 和各类交付 ZIP 是可再生成快照，不作为第二套事实来源提交普通 Git 历史；
- 真实 `hosts.local.env`、个人 SSH config 片段和机器专用 bootstrap wrapper 含活动基础设施端点，只保存在操作者/Vultr 本地；
- 使用 [`scripts/render_local_topology_bundle.py`](../../scripts/render_local_topology_bundle.py) 从 gitignored inventory 生成本地文件和校验和；
- 会议逐字稿与原始项目 PDF 属于内部来源材料，未经隐私、作者与许可审查不得上传公开仓库；
- bearer token、Tailscale auth key、密码和 SSH 私钥在任何情况下都不得进入 Git、issue、prompt、日志或 bundle。

如需公开单文件快照或 ZIP，应在正式版本冻结后从 tagged revision 生成，并作为 GitHub Release/Zenodo 附件发布；仓库保留源文件、生成脚本、版本号和校验和。

## 修改流程

任何重大科学、计算或运行策略修改必须：

1. 新建或更新 `docs/decisions/ADR-*.md`；
2. 明确受影响的任务编号、数据冻结、统计阈值、资源上限和停止条件；
3. 更新根级 `AGENTS.md`、`AGENTS-ops.md` 或对应规范分卷；
4. 更新 `plan/plan.yaml` 并运行 plan validation 与 `taskctl reconcile`；
5. 在 commit/PR 中说明变更原因和验证方式；
6. 若变更发生在解盲后，必须登记到 `deviation_log.md`。

## 当前重要决策

- [`ADR-0002-ode-compute-model.md`](../decisions/ADR-0002-ode-compute-model.md)：解释为什么项目的高保真核心仍是大量 BBN ODE/反应网络求解，以及为什么执行上不应采用盲目的百维暴力采样；
- [`ADR-0003-research-ops-control-plane.md`](../decisions/ADR-0003-research-ops-control-plane.md)：规定项目 ledger、独立 `ops-status` 分支与长任务 heartbeat/checkpoint 协议；
- [`ADR-0004-shared-control-elastic-autodl.md`](../decisions/ADR-0004-shared-control-elastic-autodl.md)：规定一台共享轻量 Vultr 控制宿主机、两台跨项目弹性 AutoDL 物理 worker、host-level Tailscale、node-specific SSH key、显式项目环境和跨项目资源 lease；
- [`../ops/CLUSTER_RUNBOOK.md`](../ops/CLUSTER_RUNBOOK.md)：共享控制宿主机与两个弹性 AutoDL 节点的部署、SSH、验收、关机、恢复和科学任务启动顺序。
