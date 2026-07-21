# ADR-0002：高保真 BBN ODE 计算瓶颈与执行策略

- **状态**：Accepted
- **日期**：2026-07-21
- **适用范围**：Track A、Track B-PA、Track B-CS、Track B-ML、AutoDL/HPC 资源计划
- **关联规范**：`/AGENTS.md`、`docs/agents/EXECUTION.md`、`docs/agents/COMPUTE_VALIDATION.md`

## 1. 决策摘要

项目的高保真物理核心仍然是：在不同宇宙学参数、核反应率、不确定度函数模态、中子寿命、反应网络和数值实现下，反复求解耦合的 BBN 丰度演化方程与核反应网络。

因此，“这是一个需要大量微分方程/反应网络求解的计算密集型问题”这一判断仍然正确；但必须加上三个限定：

1. **它不是天然以 GPU 深度学习训练为主的项目**。传统 PArthENoPE、AlterBBN、PRyMordial/PRIMAT 类高保真计算通常首先受 CPU、FP64、ODE/网络积分、进程并行、内存和 I/O 限制；LINX/JAX 路线是否适合 GPU 必须由实测决定。
2. **单次求解不一定极端昂贵，完整科学任务才昂贵**。真正的成本来自 `solver calls × 参数点 × nuisance draws × solver/network baselines × 数据组合 × posterior/SBC repeats` 的乘法效应。
3. **不得把“计算密集”误解为需要盲目生成百万到亿级训练样本**。新版路线采用 Fisher 预筛选、低维敏感方向、函数型头部反应、主动学习、多保真建模和 direct-solver 验证来减少高保真调用。

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

判断：**中等计算量，不是极端 ODE 计算项目**。主要问题可能是链收敛、内存、工程复现和多 seed，而不是训练大模型。

### R1：Fisher、solver matrix 与 Pilot

包括：

- 64–128 个代表点的局部响应；
- S0–S8 中选定基线的中心值和导数；
- 标量 rate 与函数形状 proxy；
- Pilot-1k / Pilot-10k；
- 初始 active learning。

判断：**明显的高保真 ODE/反应网络工作负载，但可通过多进程和任务分片稳妥完成**。此阶段禁止预先购买大规模 GPU 集群。

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

判断：**仍然是计算密集型项目**。昂贵部分不是单个神经网络，而是高保真 solver 数据、反复统计推断和严格验证的总成本。

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
```

必须报告：

- cold/warm median、p90、p99 runtime；
- CPU-core-hours per accepted label；
- FP32/FP64 差异；
- solver failure/retry rate；
- GPU-hours 与 CPU-core-hours分开；
- 数据生成成本是否被 emulator 加速比隐藏；
- complete-posterior wall time 和 ESS/hour，而不只报告 forward latency。

## 6. 资源决策

当前默认：

- `uq-sim-01`：CPU-rich，负责 solver/Fisher/数据生成；
- `uq-train-01`：1 × RTX 4090，负责 emulator/flow/active-learning surrogate；
- `uq-verify-01`：按需 1 × RTX 4090，JAX/LINX FP64 或 NUTS 受限时按 benchmark 改用 A100。

即：**2 台常驻、2 张卡；第 3 台按需；稳妥并发 3 台、3 张卡。**

只有 `FISHER-GATE >= G1` 且 Pilot 证明高保真调用确实是瓶颈时，才临时扩展到 4–6 个独立单卡/CPU-rich 节点。当前不采用 8 卡 DDP 节点作为默认方案。

## 7. 何时说明“emulator 值得做”

至少满足一项：

- 在相同 posterior bias/coverage 下，将完整 posterior 的墙钟时间降低至少一个数量级；
- 使 1,000+ 次 SBC、完整多数据扫描或函数型 nuisance 边缘化从不可实际执行变为可执行；
- 显著减少高保真 solver calls，并由 held-out/direct recovery 证明没有遗漏狭窄物理结构；
- 支持 LINX/PRyMordial/PRIMAT 原生流程难以经济覆盖的扩展宇宙学或多 solver 层级模型。

若 direct LINX/PRyMordial 已能以合理成本完成全部目标，必须缩小或关闭“AI 方法创新”叙事，将 emulator 仅作为工程工具。

## 8. 停止条件

出现以下任一情况，应停止扩大计算：

- Fisher Gate 为 G0；
- Pilot learning curve 已饱和；
- 完整 rate marginalization 对目标参数影响稳定小于 `0.1 sigma` 且区间变化小于 `5%`；
- direct solver 已足够快，emulator 不产生端到端收益；
- 方法增益只来自降低精度或漏掉尾部/OOD 区域；
- 新发现不跨 solver、数据或 prior 稳健。

## 9. 本 ADR 对“做的事情是否变化”的回答

- **物理问题没有变**：仍然求解并传播 BBN 反应网络的不确定度，最终约束早期宇宙与 SGWB。
- **高保真计算核心没有变**：仍需大量 ODE/反应网络求解作为真值和验证。
- **实验策略发生了重要变化**：从百维盲目暴力采样，转为预筛选、降维、函数型头部不确定度、主动学习、多保真和严格校准。
- **硬件判断更精确**：这是 CPU/FP64/solver-call 与统计验证密集型项目，不等同于需要大量 GPU 训练；GPU 数量必须随 Gate 和实测扩展。
