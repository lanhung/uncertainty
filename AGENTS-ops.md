# AGENTS-ops.md — `lanhung/uncertainty` 长任务与混合集群运行规范

> 适用对象：Codex、其他代码代理、人类操作者、共享 Vultr 控制宿主机、AutoDL/HPC worker。  
> 规范地位：本文件与根级 `AGENTS.md` 共同生效；科学条款冲突时以根级文件为准。

## 1. 核心原则：进度不得困在会话里

- `plan/plan.yaml` 是 desired state；状态服务器中的 ledger 是 observed state。
- 所有状态变化只能通过 `taskctl/taskctl.py` 或 worker heartbeat API 完成，禁止手工修改 SQLite、`tasks.json` 或 `SUMMARY.md`。
- 修改计划后先运行 `python orchestrator/reconcile.py plan/plan.yaml` 验证，再运行 `taskctl reconcile`。
- 不得创建 plan 中不存在的隐形任务。新增任务必须先进入 `plan.yaml`。
- Codex 进程可以退出、重启或并行存在；任何任务的唯一状态不得只保存在某个 Codex session 中。

## 2. 超过 60 秒的任务必须 detached + wrapped

任何预计超过 60 秒、可能因 SSH 断开而中断、或需要可见进度的任务，必须使用：

```bash
nohup python worker/run_with_heartbeat.py \
  --task <PLAN_TASK_ID> \
  --total <ABSOLUTE_TOTAL> \
  --unit <samples|chains|points|epochs|checks> \
  --resume \
  -- <ACTUAL_COMMAND> \
  > logs/<PLAN_TASK_ID>.log 2>&1 &
```

实际程序必须定期输出：

```text
PROGRESS <absolute_current>/<absolute_total>
METRIC <key>=<numeric_value>
```

要求使用绝对进度而不是单次进程内增量，确保 checkpoint 恢复后看板不会倒退。禁止把长任务只放在当前 Codex/SSH 前台会话中。

## 3. 正确的 Vultr–AutoDL 拓扑

### 3.1 共享 Vultr 控制宿主机

- Vultr 是轻量、常开、低成本的**共享控制宿主机**，不是本项目独占的三节点集群，也不承担 production solver/training。
- 同一台 Vultr 可以同时运行多个 Codex 进程，分别管理多个项目。
- 每个项目必须运行独立的 research-ops 实例。本项目默认使用：

```text
project slug: uncertainty
service:      research-ops-uncertainty.service
port:         8787
secret env:   /etc/research-ops/uncertainty.env
ledger:       /var/lib/research-ops/uncertainty/state.db
status clone: /root/uncertainty-status
```

- 不同项目不得共享 token、SQLite 文件、端口、systemd 服务名或状态分支 clone。
- Vultr 控制实例负责 Codex、plan reconciliation、status server、ledger、dashboard 和 GitHub 快照；只允许运行轻量 smoke/diagnostic，不得被 solver farm、训练或大型 MCMC 挤占。

### 3.2 按需 AutoDL worker

- `uncertainty-sim-autodl-*`：默认在 AutoDL 按需创建；按 vCPU、RAM、FP64 行为、本地 SSD 和价格选择，用于 solver、Jacobian、Fisher、Pilot 数据生成和核反应率传播。
- `uncertainty-train-autodl-*` / `uncertainty-verify-autodl-*`：默认在 AutoDL 按需创建；按训练、HMC/NUTS、SBC、显存和 FP64 benchmark 选择 4090/A100 等机器。
- AutoDL worker 是可替换、可关机的执行节点，不是常驻状态源。实例释放后，任务计划和 ledger 仍在 Vultr；checkpoint、outbox、manifest 和关键产物必须保存在 `/root/autodl-fs/uncertainty` 或批准的对象存储。
- `sim`、`train`、`verify` 是逻辑角色而非固定物理机器。早期可在一台 AutoDL 上串行合并角色；需要独立验证时必须使用独立 attempt、环境或节点。
- 三类角色不等于三台 Vultr，也不等于三张 GPU。资源采购与启停必须遵守 `docs/agents/COMPUTE_VALIDATION.md` 和 Fisher Gate。

## 4. 状态报告时机

- 手工开始：`taskctl start <id> --total N --unit U`。
- 更新绝对进度与科学指标：

```bash
python taskctl/taskctl.py progress <id> --current N \
  --metric r_hat=1.008 --metric ess_bulk=1340
```

- 需要负责人决定：`taskctl block <id> --reason "..."`。
- 失败：`taskctl fail <id> --reason "..."`，不得保持虚假的 running。
- 完成：wrapper 自动报告；手工任务使用 `taskctl done <id>`。
- 产生图、表、报告或 checkpoint manifest：先提交到 GitHub，再执行 `taskctl artifact <id> <repo-relative-path>`。
- 结束工作会话前执行 `taskctl snapshot`；正常运行时服务器每约 3 分钟自动快照。

## 5. 依赖、重试和并发

- 默认不得绕过未完成依赖；只有经过 ADR/负责人批准的诊断任务可以 `taskctl start --force`。
- 同一 task 同时只能有一个 active `run_id`。新 attempt 启动后，旧 AutoDL worker 的延迟 heartbeat 不得覆盖新状态。
- 每个 production shard 必须幂等、可恢复、有 checksum；重跑不得静默覆盖正式产物。
- 同一任务的并行 shard 应拥有独立 shard ID 和输出目录，但汇总到同一个 plan task 的绝对计数。
- worker 网络中断时任务继续，heartbeat 写入本地 outbox；恢复后自动补发。永久性 4xx（错误 token、未知任务、依赖未完成）必须在昂贵命令启动前终止。
- AutoDL 关机前必须确认任务为 `done`、`blocked`、`failed` 或具有已验证 checkpoint 的可恢复状态；不得让 dashboard 长期保留虚假 `running`。

## 6. checkpoint、临时盘与数据安全

- 至少每 15–30 分钟 checkpoint；AutoDL 关键数据写入 `/root/autodl-fs/uncertainty` 或批准的对象存储。
- `/root/autodl-tmp/uncertainty` 只用于高 I/O scratch；任何不可再生结果不得只存在于临时盘。
- AutoDL 释放前必须同步 checkpoint、manifest、日志摘要和 checksum，并在 ledger 中记录恢复入口。
- Vultr 只持有项目代码、控制状态、小型摘要和必要备份，不作为大规模科学数据仓库。
- 原始大数据不进入普通 Git；进入 manifest、校验和与对象存储。
- `RESEARCH_OPS_TOKEN` 和 `TAILSCALE_AUTHKEY` 只能保存在 mode `0600` 的环境文件或短时内存中，不得进入 Git、日志、截图、issue、prompt 或命令历史。
- live dashboard 默认只通过 Tailscale 访问；公开 `ops-status` Pages 只能显示允许公开的任务标题、指标和 artifact 路径。

## 7. 科学真实性不因自动化而降低

- 高保真训练标签只能来自批准的 BBN solver 或核数据 posterior 传播。
- 生成模型可以提出 acquisition points、学习条件分布或执行低保真近似，但不得自行制造物理标签。
- dashboard 的百分比是执行进度，不是发现概率、论文完成度或科学置信度。
- `stale` 表示 heartbeat 断开，不等于物理任务失败；必须检查 AutoDL 实例、日志和 checkpoint 后再决定 resume/fail。
- 所有 Nature-tier 结论仍受预注册、Fisher Gate、跨 solver、SBC、coverage、OOD 和独立复现约束。

## 8. Git、快照与多项目隔离

- 科学代码、配置、ADR 和结果进入 `main` 或正常 PR 分支。
- 自动状态快照只进入本项目独立 `ops-status` 分支的 `state/` 与 `docs/`，禁止每 3 分钟污染 `main`。
- `state/tasks.json`、`state/SUMMARY.md` 和静态 dashboard 是生成产物；不允许手工编辑。
- 本项目 status server 是本项目快照分支的唯一 writer。其他项目必须使用它们自己的仓库、状态分支和 clone。
- 若发生非快进冲突，停止自动 push 并在看板/日志中明确报错，不得 force-push 覆盖。

## 9. 每次接手任务的最小检查

```bash
python taskctl/taskctl.py health
python taskctl/taskctl.py show
python orchestrator/reconcile.py plan/plan.yaml
git status --short
```

随后确认：当前 Codex/终端指向 `uncertainty` 的端口和 token；任务 ID 存在；依赖已完成；AutoDL 节点角色正确；配置与数据已冻结；持久目录和 checkpoint 可写；资源上限未越过 Gate。
