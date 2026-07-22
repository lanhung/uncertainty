# ADR-0006：重新聚焦 BBN 核反应率不确定度主问题

- **状态**：Accepted
- **日期**：2026-07-23
- **适用范围**：根级 AGENTS、任务 DAG、solver/data/model 路线、AutoDL 计算优先级、论文路线
- **替代关系**：本 ADR 在当前执行优先级上取代 `ADR-0005-manuscript-baseline-self-contained-pivot.md`；后者仅保留为历史决策记录

## 1. 纠偏原因

项目的原始目标是研究 BBN 核反应率不确定度：反应率是耦合 ODE 网络中的不确定物理系数，中心值计算只给出点预测，而完整传播应得到丰度分布并在宇宙学推断中对 rate nuisance variables 边缘化。

上一版执行计划把一篇即将投稿、但由另一条工作线负责的 JCAP stiff/SGWB 稿件放到了本仓库的最高优先级。这使项目从“核反应率不确定度与分布式推断”偏移到了“稿件资产发布、lithium no-go 与 SGWB 复现”。该优先级与仓库目的不一致，现立即纠正。

## 2. 核心决策

当前唯一主动科学主线为：

> **建立一个自包含、可验证的 BBN 核反应率不确定度传播与边缘化系统，并定量比较中心反应率、常数理论误差、显式 nuisance marginalization 与学习后的 abundance distribution。**

当前 JCAP 稿件：

- 不再是本项目的依赖；
- 不再出现在 active desired state；
- 不阻塞 solver、rate prior、Monte Carlo、emulator 或 inference 工作；
- 仅可在未来作为非标准宇宙学应用案例或外部背景引用；
- 其 release、chain、SGWB、SageNet 与投稿任务由独立项目管理。

## 3. 科学关键路径

立即采用：

```text
U0：自包含 solver/rate-prior 基线
-> U1：固定宇宙学点 Monte Carlo 理论带
-> U2：16 点 covariance-drift / non-Gaussian smoke
-> U3：正式 64 点响应与 Fisher gate
-> U4：条件 forward emulator 与 marginalized distribution model
-> U5：posterior recovery 与 direct-vs-learned comparison
-> 条件性 full-network / functional-rate / non-standard-cosmology expansion
```

任何 manuscript、SGWB、lithium no-go 或通用 ML benchmark 不得插入上述依赖链。

## 4. 从零、自包含实现

缺少私有 modified solver、checkpoint 或旧 MCMC 资产不构成阻塞。项目允许并优先采用 clean-room scientific implementation：

1. 固定公开 solver revision、license、rate tables 与环境；
2. 建立统一的 `simulate(theta, z, tau_n, solver, network, precision)` 接口；
3. 用 solver 原生 rate nuisance 或审计后的外部 rate table 产生真实标签；
4. 首先复现标准 BBN central values 与 Monte Carlo bands；
5. 再训练简洁的 conditional emulator；
6. 最后扩展到复杂分布模型、函数型 rate modes 或非标准宇宙学。

公开 LINX、PRyMordial、PRIMAT、PArthENoPE 与 AlterBBN 可在许可证允许范围内使用。不同 solver 分发的相同 rate table 不算独立核数据证据。

## 5. 反应率维度策略

不从约 100 维全网络开始。

- `R0`：`d(p,gamma)3He`、`d(d,n)3He`、`d(d,p)t`，另将 `tau_n`/weak physics 单列；
- `R1`：为四丰度加入经过 sensitivity/provenance 审计的 `3He/7Be/7Li` 关键通道；
- `R2`：约 10–20 个 core rates；
- `R3`：full-network stress。

扩维必须由缺失方差、posterior sensitivity、coverage failure 或科学终点需要触发。

## 6. 推断模型比较

强制比较：

- `U-M0`：central rates；
- `U-M1`：固定 `C_th` 的两阶段近似；
- `U-M2`：直接 Monte Carlo / 显式 nuisance marginalization；
- `U-M3`：学习 `f(theta,z)`；
- `U-M4`：学习 `p(y|theta)`；
- `U-M5/U-M6`：多 solver 与 hybrid fallback，仅在前述模型通过后启用。

项目的首篇核心结果应回答：`U-M1` 在什么区域、以多大幅度偏离 `U-M2`，以及 `U-M3/U-M4` 能否在 coverage 与 posterior fidelity 不下降的前提下降低成本。

## 7. 活动与暂停

### 活动

- public solver/runtime 基线；
- rate-prior provenance 与 nuisance interface；
- 1k/3k/10k Monte Carlo convergence；
- Schramm theoretical bands；
- covariance drift、cross-abundance correlation 与 non-Gaussianity；
- conditional emulator / density model；
- posterior recovery、SBC、OOD 与 direct fallback；
- direct versus emulator end-to-end economics。

### 暂停

- JCAP manuscript release/reproduction；
- stiff-phase lithium no-go；
- SageNet/SGWB integration；
- ABCMB full component audit；
- generic LINX gradient debugging not required by the active gate；
- Pilot-10k before the formal gate；
- Nature Machine Intelligence / Nature Computational Science campaign；
- architecture-first GAN/flow/diffusion/Transformer work。

## 8. 成功与停止条件

### 继续扩大

出现任一情况时进入正式 64 点和更高阶段：

- `C_rate(theta)` 相对 fiducial 明显漂移；
- abundance distribution 有重要 skew/tail/correlation；
- 常数 `C_th` 导致核心 posterior shift `>=0.1 sigma` 或区间变化 `>=5%`；
- direct joint marginalization 的注册总成本超出当前 worker 预算；
- learned model 在 matched fidelity 下至少减少 `10x` 高保真调用或 `5x` 端到端 wall time。

### 停止或收缩

- Monte Carlo band 在小样本下已稳定且 `C_rate(theta)` 近似常数；
- `U-M1` 与 `U-M2` 的 posterior 差异低于全部 null thresholds；
- direct solver 已能经济完成完整注册工作负载；
- learned model 未通过 coverage、posterior fidelity 或 explicit-failure gate。

Null result 仍是可报告的科学结果，不得通过更换主数据、扩大反应集合或改用新架构追逐显著性。

## 9. 仓库后果

- 根级 `AGENTS.md` 升级为 v0.4.0；
- `plan/plan.yaml` 改为 UQ-only desired state；
- manuscript-specific configs 从 active tree 移除；
- `SCIENCE_CRITICAL_PATH_v3.md` 成为当前关键路径；
- Issue #3 关闭为独立稿件项目；
- Issue #4 改写为本项目的核反应率 UQ 主任务；
- 现有运行、solver benchmark、provenance 与控制面证据保留并复用。
