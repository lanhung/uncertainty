#!/usr/bin/env python3
"""Idempotently integrate AGENTS-ops.md into the root governance contract."""
from __future__ import annotations

from pathlib import Path

path = Path("AGENTS.md")
text = path.read_text(encoding="utf-8")
marker = "## 6. 运行控制面与长任务强制规则"

text = text.replace("> 版本：**0.2.0**", "> 版本：**0.2.1**", 1)
text = text.replace("> 本版替代：v0.1.0", "> 本版替代：v0.2.0", 1)
text = text.replace("## v0.2.0 变更摘要", "## v0.2.1 变更摘要", 1)
text = text.replace(
    "相对于 v0.1.0，本版完成以下战略修订：",
    "v0.2.1 完整保留 v0.2.0 的科学战略，并将其接入可长期运行的集群控制面；v0.2.x 系列完成以下修订：",
    1,
)
summary_anchor = "10. 新增外部复现、月度竞争审计、claim-evidence matrix、编辑预询问材料和独立红队签字。"
summary_item = "\n11. 新增外部任务 ledger、三节点控制面、长任务 heartbeat/checkpoint、独立 `ops-status` 快照分支和 dashboard；任何长任务不得只存在于 Codex/SSH 会话中。"
if summary_item.strip() not in text and summary_anchor in text:
    text = text.replace(summary_anchor, summary_anchor + summary_item, 1)

text = text.replace(
    "为避免根级 `AGENTS.md` 超长导致代码代理遗漏关键条款，v0.2.0 将执行细节拆成三个**同等强制、不可选择性忽略**的规范性分卷：",
    "为避免根级 `AGENTS.md` 超长导致代码代理遗漏关键条款，项目将执行细节拆成三个科研分卷和一个**同等强制、不可选择性忽略**的运行规范：",
    1,
)
publication_line = "3. [`docs/agents/PUBLICATION.md`](docs/agents/PUBLICATION.md)：论文路线、Milestone、首个 14 天、年度节奏、禁令、发布检查和文献清单。"
ops_line = "4. [`AGENTS-ops.md`](AGENTS-ops.md)：Vultr/AutoDL/HPC 控制面、任务 ledger、heartbeat、checkpoint、detached 运行、状态快照与密钥安全。"
if ops_line not in text and publication_line in text:
    text = text.replace(publication_line, publication_line + "\n" + ops_line, 1)
text = text.replace(
    "根级 `AGENTS.md` 与上述三个分卷共同构成项目 v0.2.0 的完整执行章程；",
    "根级 `AGENTS.md` 与上述四份规范共同构成项目 v0.2.1 的完整执行章程；",
    1,
)

if marker not in text:
    appendix = r'''

## 6. 运行控制面与长任务强制规则

### 6.1 状态源与服务器角色

- `plan/plan.yaml` 是 desired state；status server 的 SQLite ledger 是 observed state。
- `uq-control-01` 是唯一 ledger writer；worker、Codex 和人类只能经 `taskctl`/heartbeat API 更新状态。
- 推荐三节点为 `uq-control-01`、`uq-sim-01`、`uq-train-01`/`uq-verify-01`；三节点不等于三张高端 GPU。
- 自动状态快照只进入独立 `ops-status` 分支，禁止高频状态提交污染 `main`。

### 6.2 长任务合同

预计超过 60 秒的任务必须 detached、checkpointed 且由 `worker/run_with_heartbeat.py` 包装；子程序必须输出绝对进度 `PROGRESS i/N`，关键科学诊断使用 `METRIC key=value`。不得以 Codex session、SSH 前台进程或未登记 tmux 窗口作为唯一状态来源。

每个长任务必须满足：

- task ID 已存在于 plan；
- 默认依赖全部完成；
- 输出目录、checkpoint、manifest 和日志位置已确定；
- worker 断网时 heartbeat 可缓存，恢复后补发；
- 新 attempt 的 `run_id` 可以拒绝旧 worker 的迟到事件；
- 失败、block、stale 和 done 必须在 dashboard 上诚实区分；
- dashboard 百分比只代表执行进度，不代表科学置信度或 Nature 投稿概率。

### 6.3 启动与运维入口

- 控制面：`scripts/bootstrap_vultr.sh`；
- 通用 worker：`scripts/bootstrap_worker.sh`；
- AutoDL worker：`scripts/bootstrap_autodl.sh`；
- 集群 runbook：[`docs/ops/CLUSTER_RUNBOOK.md`](docs/ops/CLUSTER_RUNBOOK.md)；
- 架构决策：[`docs/decisions/ADR-0003-research-ops-control-plane.md`](docs/decisions/ADR-0003-research-ops-control-plane.md)。

任何代理在启动生产任务前必须读取 `AGENTS-ops.md`，运行 `taskctl health`、`taskctl show` 和 plan validation，并确认没有越过 Fisher Gate、数据冻结或资源上限。

---
'''
    text = text.rstrip() + appendix

path.write_text(text.rstrip() + "\n", encoding="utf-8")
