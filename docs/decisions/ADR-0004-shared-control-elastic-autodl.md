# ADR-0004：共享 Vultr 控制宿主机与弹性 AutoDL 算力池

- **状态**：Accepted
- **日期**：2026-07-21
- **适用范围**：research-ops、Codex、多项目隔离、AutoDL 生命周期、SSH、Tailscale、数据与资源调度
- **替代/澄清**：澄清任何把三类角色理解为三台长期专用服务器的描述
- **关联规范**：`AGENTS-ops.md`、`docs/ops/CLUSTER_RUNBOOK.md`、`docs/agents/COMPUTE_VALIDATION.md`

## 1. 决策摘要

本项目采用下列物理部署，而不是三台长期专用机器：

```text
一台轻量、常开的共享 Vultr 控制宿主机
  ├── uncertainty 的 Codex/session、status service、ledger、dashboard
  ├── 其他项目的 Codex/session 和各自独立 control-plane instance
  └── 不承担 production solver、训练或大规模 MCMC

两台按量计费、可关机、可被其他项目复用的 AutoDL 执行节点
  ├── 任一节点可在不同时间承担 solver / train / verify
  ├── 角色由当前任务、资源 lease 和 benchmark 决定
  └── 不作为项目状态唯一来源
```

`sim`、`train`、`verify` 是**逻辑工作负载标签**，不是物理服务器的永久身份。

## 2. 为什么采用这一结构

1. Vultr 适合常驻的轻量控制、多个 Codex 进程、状态服务和 GitHub 操作，但没有必要长期承担昂贵科学计算。
2. AutoDL 按量计费，能够以较低成本获得较强 CPU、内存和 GPU；关机或切换项目时，Vultr ledger 仍保存任务状态。
3. 两台 AutoDL 可能同时服务其他项目，因此必须避免：
   - 一个项目的 token 被另一个项目的 shell 自动覆盖；
   - 两个项目同时占用同一 GPU；
   - 每个项目各启动一份 Tailscale daemon；
   - 把不可再生结果只留在本地临时盘；
   - 通过 worker-to-worker SSH 建立不必要的横向访问。
4. 该结构把控制成本、计算成本和数据成本分开，使资源可以按 Fisher Gate 和实际队列扩缩。

## 3. 控制宿主机隔离合同

共享 Vultr 上，每个项目必须拥有独立的：

- repository checkout；
- Codex/tmux session；
- project slug；
- TCP port；
- systemd service；
- bearer token；
- SQLite state directory；
- status-branch clone；
- GitHub credential或 repo-scoped deploy key。

本项目默认：

```text
slug:         uncertainty
port:         8787
service:      research-ops-uncertainty.service
env:          /etc/research-ops/uncertainty.env
state:        /var/lib/research-ops/uncertainty/
status clone: /root/uncertainty-status/
```

不得把 `RESEARCH_OPS_TOKEN` 全局写入共享宿主机的 `.bashrc`。进入项目 shell 时显式加载对应 env。

## 4. AutoDL 节点隔离合同

### 4.1 目录

共享 AutoDL 节点使用：

```text
/root/autodl-tmp/projects/<project>/       # 高 I/O、本地、可重建代码和 scratch
/root/autodl-fs/projects/<project>/        # 该地区持久 checkpoint、manifest、artifact
/root/autodl-fs/_research-host/tailscale/  # 物理节点唯一 Tailscale 状态
/var/lock/research-workers/                # 跨项目资源 lease
```

项目环境文件不得统一追加到 `.bashrc`。每个任务 shell 显式：

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
```

### 4.2 逻辑角色

同一台 AutoDL 可以在不同时段被登记为：

- `solver`：CPU/FP64、Jacobian、Fisher、数据生成；
- `train`：emulator/flow 训练；
- `verify`：独立 MCMC、SBC、direct recovery；
- `elastic`：尚未固定，由具体任务获取资源 lease 后决定。

任务开始前必须记录 node、role、capabilities、其他项目占用和 lease。

### 4.3 资源 lease

默认：

- GPU 任务必须独占 `gpu0` lease；
- 大规模 CPU solver farm 必须获取 `cpu-heavy` lease；
- 高吞吐数据重排可获取 `io-heavy` lease；
- 未经 profiling 不允许两个项目共享同一 GPU；
- lease 只说明执行资源占用，不替代 research-ops task state。

入口：`scripts/with_resource_lease.sh`。

## 5. 网络与 SSH 决策

采用两条分离的通道：

1. **管理通道**：共享 Vultr 通过 AutoDL 提供的 SSH 转发域名和端口登录两台 worker。
2. **遥测通道**：AutoDL worker 通过 Tailscale 私网主动访问 Vultr 上本项目的 status API。

密钥关系：

- 操作者电脑 → Vultr：操作者个人 SSH key；
- Vultr → AutoDL A：独立 node-specific key；
- Vultr → AutoDL B：另一把独立 node-specific key；
- AutoDL → Vultr：不创建反向 SSH 私钥；
- AutoDL A ↔ AutoDL B：不创建 worker-to-worker SSH 信任；
- AutoDL → GitHub：公开仓库默认 HTTPS 只读 clone；
- Vultr → GitHub：repo-scoped credential，用于代码与 status branch。

独立 worker key 允许某个 AutoDL 实例重建时单独撤销，不影响另一台。禁止 SSH agent forwarding 和 worker 间横向密钥复制。

## 6. Tailscale 决策

- Vultr 作为一台 host-level Tailscale device；各项目通过不同端口隔离。
- 每台 AutoDL 只有一个 host-level Tailscale identity，不因项目数量启动多份 daemon。
- AutoDL 容器没有 `/dev/net/tun` 时使用 userspace networking；socket、state 和 proxy 位于 host-level 持久目录。
- AutoDL 节点可使用 tagged、pre-authorized auth key；是否 ephemeral 由实例生命周期决定。
- auth key 不进入 Git、issue、prompt、命令历史或长期明文脚本。

## 7. 数据平面决策

两台 AutoDL 位于不同地区时，`/root/autodl-fs` 不得被假定为共享文件系统。

- 代码、小型配置、manifest、checksum：GitHub；
- 每个地区的本地持久 checkpoint：各自 `/root/autodl-fs/projects/uncertainty`；
- 跨地区大数据：批准的对象存储/rclone 数据层；
- Vultr：仅保存 ledger、小型报告和恢复索引，不中转大规模训练数据；
- worker-to-worker `scp/rsync` 不是默认数据总线。

任何数据 shard 必须不可变、带 checksum、solver/config hash 和可重建命令。

## 8. 生命周期

```text
控制面常开
→ 查看所有项目和节点 lease
→ 为 uncertainty 选择空闲 AutoDL
→ 显式加载 uncertainty env
→ 获取资源 lease
→ detached + heartbeat + checkpoint 运行
→ 同步持久 artifact/manifest
→ 释放 lease
→ 任务标记 done/blocked/resumable
→ 若无其他项目占用，关闭 AutoDL
```

关机决策属于**物理节点级**决策，必须检查所有项目，而不能只看 uncertainty dashboard。

## 9. 后果

### 正面

- Vultr 成本稳定且控制面始终在线；
- AutoDL 利用率可跨项目提高；
- 逻辑角色可随科学阶段变化；
- 单项目失败或 token 泄漏不必停止所有控制服务；
- worker 可释放而不丢失任务状态。

### 代价

- 需要显式项目环境激活；
- 需要节点级 resource lease；
- 两地区数据需要对象存储而非假定共享 FS；
- SSH host key 在 AutoDL 实例重建后必须重新核验；
- 独立验证必须防止复用同一 artifact/环境造成伪独立。

## 10. 复审触发器

出现以下情况重新评审：

- Vultr 同时项目数使 CPU/RAM/端口管理成为瓶颈；
- AutoDL 更换到同地区、可共享同一文件存储；
- 引入正式作业调度器（Slurm/Kubernetes/HTCondor）；
- 使用对象存储或数据 registry 的方案发生变化；
- 需要非 root worker、多用户权限边界或合作者访问；
- 安全审计要求改用 GitHub App、短期 SSH 证书或 Vault。
