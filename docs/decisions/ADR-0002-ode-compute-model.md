# ADR-0002：高保真 BBN ODE 计算瓶颈与执行策略

- **状态**：Accepted，资源拓扑于 2026-07-21 修订
- **日期**：2026-07-21
- **适用范围**：Track A、Track B-PA、Track B-CS、Track B-ML、AutoDL/HPC 资源计划
- **关联规范**：`/AGENTS.md`、`/AGENTS-ops.md`、`docs/agents/EXECUTION.md`、`docs/agents/COMPUTE_VALIDATION.md`

## 1. 决策摘要

项目的高保真物理核心仍然是：在不同宇宙学参数、核反应率、不确定度函数模态、中子寿命、反应网络和数值实现下，反复求解耦合的 BBN 丰度演化方程与核反应网络。

因此，“这是一个需要大量微分方程/反应网络求解的计算密集型问题”这一判断仍然正确；但必须加上三个限定：

1. **它不是天然以 GPU 深度学习训练为主的项目**。传统 PArthENoPE、AlterBBN、PRyMordial/PRIMAT 类高保真计算通常首先受 CPU、FP64、ODE/网络积分、进程并行、内存和 I/O 限制；LINX/JAX 路线是否适合 GPU 必须由实测决定。
2. **单次求解不一定极端昂贵，完整科学任务才昂贵**。真正的成本来自 `solver calls × 参数点 × nuisance draws × solver/network baselines × 数据组合 × posterior/SBC repeats` 的乘法效应。
3. **不得把“计算密集”误解为需要盲目生成百万到亿级训练样本**。新版路线采用 Fisher 预筛选、低维敏感方向、函数型头部反应、主动学习、多保真建模和 direct-solver 验证来减少高保真调用。

控制与计算资源必须解耦：轻量 Vultr 只作为多项目共享控制宿主机；本项目的 solver 与训练/验证能力通常在 AutoDL 按需开启，任务完成并持久化后关闭。

## 2. 不变的科学任务

旗舰任务不变，仍是回答：

> 在完整传播核反应率、中子寿命、函数型核数据误差、solver/rate-library discrepancy 和观测误差后，BBN 对非标准膨胀历史、刚性后暴胀时期、蓝倾张量谱和可观测 SGWB 的结论是否发生此前未被认识的变化？

物理真值仍由批准的高保真 solver/核数据后验产生。机器学习只能承担：

- 高保真映射的摊销近似；
- nuisance marginalization 的条件分布学习；
- 主动选择新的 solver 查询点；
- 多保真融合；
- OOD 检测和安全 fallback；
- 大规模 posterior、SBC、forecast 与 value-of-information 的计算加速。

未经 solver 标注或核数据后验约束的生成样本不得作为物理标签。

## 3. 改变的执行方式

旧式理解：

```text
在约 10 个宇宙学参数 + 约 100 个反应率上做大规模均匀/拉丁超立方采样
→ 每个点直接求解
→ 用全部结果训练大网络
```

该路线被否决。新的标准顺序是：

```text
竞争基线与数据冻结
→ 代表点局部 Jacobian / Fisher 传播
→ G0/G1/G2/G3 Gate
→ 核心反应与 active subspace
→ 头部反应函数型模态
→ Pilot-1k
→ Pilot-10k
→ 主动学习 / 多保真采样
→ emulator / conditional likelihood
→ direct-solver recovery
→ 完整联合推断与独立验证
```

全网络、全 nuisance 运行属于后期 stress test，而不是第一阶段数据生成方案。

## 4. 三个计算强度区间

### R0：Track A 与环境复现

包括：

- 现有 BBNet 推理；
- hard/soft posterior；
- 4 条或更多 MCMC 链；
- 已有模型的回归与画图。

判断：**中等计算量，不是极端 ODE 计算项目**。主要问题可能是链收敛、内存、工程复现和多 seed，而不是训练大模型。可在单台按需 AutoDL 上完成大部分任务，控制状态持续保存在 Vultr。

### R1：Fisher、solver matrix 与 Pilot

包括：

- 64–128 个代表点的局部响应；
- S0–S8 中选定基线的中心值和导数；
- 标量 rate 与函数形状 proxy；
- Pilot-1k / Pilot-10k；
- 初始 active learning。

判断：**明显的高保真 ODE/反应网络工作负载，但可通过 AutoDL CPU-rich 实例、多进程和任务分片稳妥完成**。此阶段禁止预先购买大规模 GPU 集群。`sim` 节点按任务开启；必要时并行开启 `train` 节点。

### R2：Nature-tier flagship campaign

包括：

- 多 solver × 多 rate library；
- 标量与函数型核反应率不确定度；
- 大规模联合边缘化；
- 多数据组合、多个 prior 与多个物理模型；
- 1,000–5,000 次 SBC；
- 5 个或更多训练 seed；
- OOD challenge、direct recovery、外部复现；
- 核实验 value-of-information 与 GW forecast。

判断：**仍然是计算密集型项目**。昂贵部分不是单个神经网络，而是高保真 solver 数据、反复统计推断和严格验证的总成本。此时可以临时扩展多个 AutoDL/HPC worker，但不能把临时峰值写成常驻配置。

## 5. 成本模型

每个阶段必须用实测而不是印象更新：

```text
T_sim = N_solver_calls * median_time_per_call / (N_workers * efficiency)
```

完整端到端成本必须进一步计算：

```text
C_total = C_solver_generation
        + C_training
        + C_direct_reference_inference
        + C_SBC_and_coverage
        + C_multi_solver_robustness
        + C_failed_runs_and_retries
        + C_storage_and_transfer
        + C_shared_control_overhead
```

必须报告：

- cold/warm median、p90、p99 runtime；
- CPU-core-hours per accepted label；
- FP32/FP64 差异；
- solver failure/retry rate；
- GPU-hours 与 CPU-core-hours 分开；
- 每种 AutoDL 实例的实际开机时间与费用；
- 数据生成成本是否被 emulator 加速比隐藏；
- complete-posterior wall time 和 ESS/hour，而不只报告 forward latency；
- Vultr 控制成本作为多项目共享 overhead 单列。

## 6. 资源决策

### 6.1 共享控制宿主机

- 一台轻量 Vultr 常开，运行多个项目的 Codex 和隔离控制服务；
- 本项目实例为 `research-ops-uncertainty.service`，默认端口 8787；
- ledger 位于 `/var/lib/research-ops/uncertainty`；
- 控制宿主机不承担 production solver、训练或大型 MCMC。

### 6.2 按需 AutoDL worker

- `uncertainty-sim-autodl-*`：CPU/RAM/FP64 优先，负责 solver/Fisher/数据生成；
- `uncertainty-train-autodl-*`：通常 1 × RTX 4090，负责 emulator/flow/active-learning surrogate、MCMC/SBC；
- `uncertainty-verify-autodl-*`：仅在独立验证窗口开启，JAX/LINX FP64 或 NUTS 受限时按 benchmark 改用 A100。

即：

- 空闲时 AutoDL worker 可以为 0；
- 常规活跃时通常开启 1–2 台 AutoDL；
- 独立验证时临时增加第 3 台；
- 预算受限或早期任务可在 1 台 AutoDL 上串行切换 sim/train 角色，但不能据此声称独立验证。

只有 `FISHER-GATE >= G1` 且 Pilot 证明高保真调用确实是瓶颈时，才临时扩展到 4–6 个独立 AutoDL/HPC worker。当前不采用 8 卡 DDP 节点作为默认方案。

## 7. 何时说明“emulator 值得做”

至少满足一项：

- 在相同 posterior bias/coverage 下，将完整 posterior 的墙钟时间降低至少一个数量级；
- 使 1,000+ 次 SBC、完整多数据扫描或函数型 nuisance 边缘化从不可实际执行变为可执行；
- 显著减少高保真 solver calls，并由 held-out/direct recovery 证明没有遗漏狭窄物理结构；
- 支持 LINX/PRyMordial/PRIMAT 原生流程难以经济覆盖的扩展宇宙学或多 solver 层级模型。

若 direct LINX/PRyMordial 已能以合理成本完成全部目标，必须缩小或关闭“AI 方法创新”叙事，将 emulator 仅作为工程工具。

## 8. 停止条件

出现以下任一情况，应停止扩大计算或关闭不必要的 AutoDL worker：

- Fisher Gate 为 G0；
- Pilot learning curve 已饱和；
- 完整 rate marginalization 对目标参数影响稳定小于 `0.1 sigma` 且区间变化小于 `5%`；
- direct solver 已足够快，emulator 不产生端到端收益；
- 方法增益只来自降低精度或漏掉尾部/OOD 区域；
- 新发现不跨 solver、数据或 prior 稳健；
- worker 空闲但仍持续计费；
- checkpoint/manifest 尚未安全持久化时禁止释放实例，但持久化完成后不得无理由长期占用。

## 9. 本 ADR 对“做的事情是否变化”的回答

- **物理问题没有变**：仍然求解并传播 BBN 反应网络的不确定度，最终约束早期宇宙与 SGWB。
- **高保真计算核心没有变**：仍需大量 ODE/反应网络求解作为真值和验证。
- **实验策略发生了重要变化**：从百维盲目暴力采样，转为预筛选、降维、函数型头部不确定度、主动学习、多保真和严格校准。
- **硬件判断更精确**：这是 CPU/FP64/solver-call 与统计验证密集型项目，不等同于需要大量 GPU 训练；计算节点通常在 AutoDL 按需租用，Vultr 只承担共享控制面。
