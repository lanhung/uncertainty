# AGENTS-ops.md — `lanhung/uncertainty` 长任务与共享算力运行规范

> 适用对象：Codex、其他代码代理、人类操作者、共享 Vultr 控制宿主机、按量 AutoDL/HPC worker。  
> 规范地位：本文件与根级 `AGENTS.md` 共同生效；科学条款冲突时以根级文件为准。  
> 架构决策：`docs/decisions/ADR-0004-shared-control-elastic-autodl.md`

## 1. 核心原则：进度不得困在会话里

- `plan/plan.yaml` 是 desired state；本项目 status server 的 ledger 是 observed state。
- 所有状态变化只能通过 `taskctl/taskctl.py` 或 worker heartbeat API 完成，禁止手工修改 SQLite、`tasks.json` 或 `SUMMARY.md`。
- 修改计划后先运行 `python orchestrator/reconcile.py plan/plan.yaml` 验证，再运行 `taskctl reconcile`。
- 不得创建 plan 中不存在的隐形任务。新增任务必须先进入 `plan.yaml`。
- Codex 进程可以退出、重启或并行存在；任务唯一状态不得只保存在 Codex session、SSH 终端或某个 tmux pane 中。

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

进度必须是绝对值，确保 checkpoint 恢复后看板不倒退。禁止把长任务只放在当前 Codex/SSH 前台。

## 3. 正确的物理拓扑

### 3.1 一台共享、轻量、常开的 Vultr 控制宿主机

- Vultr 是**多项目共享控制宿主机**，不是本项目独占 compute node。
- 同一台 Vultr 可以同时运行多个 Codex 进程，分别管理不同仓库。
- 每个项目必须有独立的 repo checkout、tmux/Codex session、project slug、port、systemd service、token、SQLite 目录和 status clone。
- 本项目默认：

```text
project slug: uncertainty
service:      research-ops-uncertainty.service
port:         8787
secret env:   /etc/research-ops/uncertainty.env
ledger:       /var/lib/research-ops/uncertainty/state.db
status clone: /root/uncertainty-status
```

- Vultr 负责 Codex、plan reconciliation、status server、ledger、dashboard、GitHub 操作和轻量诊断。
- Vultr 不承担 production solver、训练、SBC 或大型 MCMC；不得让一个项目的计算挤占其他项目控制面。
- 禁止把一个项目的 `RESEARCH_OPS_TOKEN` 全局写入共享宿主机 `.bashrc`。

### 3.2 两台共享、弹性、按量计费的 AutoDL 执行节点

- 两台 AutoDL 不是 uncertainty 永久专用服务器，也不永久绑定 `sim` 或 `train`。
- `solver`、`train`、`verify`、`elastic` 是任务时逻辑角色；任一物理节点可随队列、成本和 benchmark 改变角色。
- 节点可能正在运行其他项目。启动任务前必须检查 GPU、CPU、内存、磁盘、其他项目 lease 和正在运行的进程。
- 默认使用：

```text
/root/autodl-tmp/projects/uncertainty/                    # 本地高 I/O、可重建 repo/scratch
/root/autodl-fs/projects/uncertainty/                     # 该地区持久 checkpoint/manifest/artifact
/root/autodl-fs/_research-host/<physical-node>/tailscale/ # 物理节点持久 Tailscale identity
/root/autodl-tmp/_research-host/<physical-node>/tailscale/# 物理节点本地 socket/PID/log
/var/lock/research-workers/                               # 跨项目资源 lease
```

- AutoDL project env 必须显式加载：

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
```

- 共享节点默认 `AUTO_SOURCE_WORKER_ENV=0`；不得把多个项目 env 依次追加到 `.bashrc`，否则 token、endpoint 和 owner 会互相覆盖。
- AutoDL 可关机、迁移或被其他项目占用；它不是任务状态唯一来源。Vultr ledger 必须持续可用。

## 4. 管理网络、遥测网络与密钥方向

- 人类/Codex 管理 AutoDL：Vultr 通过 AutoDL 的 SSH 转发域名与端口连接。
- worker 遥测：AutoDL 通过 Tailscale 私网主动访问 Vultr 上 uncertainty 的 API；dashboard 端口不公开暴露。
- 推荐密钥关系：

```text
operator laptop -> Vultr                  personal key
Vultr -> AutoDL worker A                  node-specific key A
Vultr -> AutoDL worker B                  node-specific key B
AutoDL -> Vultr                           no reverse SSH private key
AutoDL A <-> AutoDL B                     no lateral SSH trust
AutoDL -> public GitHub repo              HTTPS read-only clone
Vultr -> GitHub                           repo-scoped credential
```

- 禁止 SSH agent forwarding、私钥复制到 worker、worker-to-worker 信任和 `StrictHostKeyChecking=no`。
- AutoDL host key 变化时必须先核验实例是否重建，再删除旧 known-host 条目。
- live endpoint、SSH 端口和节点名写入 gitignored `deploy/hosts.local.env`，不写入公开代码。

## 5. 一个物理 AutoDL 节点只能有一份 host-level Tailscale

- Vultr 是一台 Tailscale device，各项目用不同 TCP port 隔离。
- 每台 AutoDL 只有一个 host-level Tailscale identity；项目 bootstrap 必须复用同一 daemon/socket/state。
- 无 `/dev/net/tun` 时允许 userspace networking；identity/state 在 `/root/autodl-fs/_research-host/<physical-node>/tailscale`，socket/PID/log 在 `/root/autodl-tmp/_research-host/<physical-node>/tailscale`。
- Unix socket 不得放在跨实例共享的网络文件系统根目录，也不得让同地区两台物理节点复用同一路径。
- tagged/pre-authorized auth key 可用于服务器自动注册；是否 ephemeral 由节点生命周期决定。
- `TAILSCALE_AUTHKEY` 只能短时存在于内存或 mode `0600` 文件，不得进入 Git、issue、prompt、截图或 shell history。

## 6. 跨项目资源 lease

共享 AutoDL 上，research-ops ledger 管理的是**项目任务状态**，而 host-level lease 管理的是**物理资源占用**；两者必须同时满足。

默认规则：

- GPU 任务先获取 `gpu0` lease；默认不允许两个项目共享一张 GPU。
- 占满大部分 CPU 的 solver farm 先获取 `cpu-heavy` lease。
- 大规模本地盘重排先获取 `io-heavy` lease。
- lease 入口为 `scripts/with_resource_lease.sh`。
- 任务结束、失败或取消后必须释放 lease；不得删除另一个项目的 lease metadata。
- 关机前必须检查所有项目的 lease，而不只看 uncertainty dashboard。

示例：

```bash
scripts/with_resource_lease.sh \
  --resource gpu0 --project uncertainty --task P4-train -- \
  python worker/run_with_heartbeat.py ...
```

## 7. 状态报告、依赖与重试

- 手工开始：`taskctl start <id> --total N --unit U`。
- 更新绝对进度与科学指标：

```bash
python taskctl/taskctl.py progress <id> --current N \
  --metric r_hat=1.008 --metric ess_bulk=1340
```

- 需要负责人决定：`taskctl block <id> --reason "..."`。
- 失败：`taskctl fail <id> --reason "..."`，不得保持虚假 running。
- 完成：wrapper 自动报告；手工任务使用 `taskctl done <id>`。
- 产生图、表、报告或 checkpoint manifest：先提交/登记产物，再执行 `taskctl artifact`。
- 默认不得绕过未完成依赖；只有经过 ADR/负责人批准的诊断任务可以 `--force`。
- 同一 task 只能有一个 active `run_id`；新 attempt 必须拒绝旧 worker 的延迟 heartbeat。
- worker 断网时任务继续，heartbeat 写本地 outbox；永久 4xx 必须在昂贵命令启动前终止。

## 8. checkpoint、磁盘与跨地区数据

- 至少每 15–30 分钟 checkpoint。
- 高 I/O 临时文件进入 `/root/autodl-tmp/projects/uncertainty`；不可再生结果不得只存在于临时盘。
- 持久 checkpoint、manifest、日志摘要和 checksum 进入本地区 `/root/autodl-fs/projects/uncertainty` 或批准对象存储。
- 两台 AutoDL 位于不同地区时，禁止假设它们的 `/root/autodl-fs` 互相可见。
- 跨地区大数据默认走对象存储/rclone 数据层；Vultr 不作为 TB/GB 级数据中转仓库。
- worker-to-worker `scp/rsync` 不是默认数据总线，也不为此创建横向 SSH 密钥。
- 每个 shard 必须不可变、有 checksum、solver/config hash、随机种子和恢复命令。

## 9. 科学真实性不因自动化而降低

- 高保真训练标签只能来自批准的 BBN solver 或核数据 posterior 传播。
- 生成模型可以提出 acquisition points、学习条件分布或执行低保真近似，但不得自行制造物理标签。
- dashboard 百分比只是执行进度，不是发现概率、论文完成度或科学置信度。
- `stale` 表示 heartbeat 中断，不等于物理任务失败；先检查 AutoDL 实例、lease、日志和 checkpoint。
- 所有 Nature-tier 结论仍受预注册、Fisher Gate、跨 solver、SBC、coverage、OOD 和独立复现约束。

## 10. Git、快照与多项目隔离

- 科学代码、配置、ADR 和结果进入 `main` 或正常 PR 分支。
- 自动状态快照只进入本项目 `ops-status` 分支，禁止高频污染 `main`。
- `state/tasks.json`、`state/SUMMARY.md` 和静态 dashboard 是生成产物；不允许手工编辑。
- 本项目 status server 是本项目快照分支唯一 writer；其他项目使用自己的仓库、状态分支和 clone。
- 非快进冲突时停止自动 push 并报警，不得 force-push 覆盖原因不明的远端变化。

## 11. 每次接手任务的最小检查

Vultr 项目 shell：

```bash
set -a; source /etc/research-ops/uncertainty.env; set +a
cd /root/uncertainty
python taskctl/taskctl.py health
python taskctl/taskctl.py show
python orchestrator/reconcile.py plan/plan.yaml
git status --short
```

AutoDL 项目 shell：

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
cd /root/autodl-tmp/projects/uncertainty/repo
bash scripts/autodl_node_status.sh
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

随后确认：任务 ID 和依赖有效；当前 shell 指向 uncertainty 的 endpoint/token；物理节点没有其他项目冲突；资源 lease 可获得；配置与数据已冻结；checkpoint 和持久目录可写；没有越过 Fisher Gate 或资源上限。
