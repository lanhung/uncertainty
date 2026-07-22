# AGENTS.md — `lanhung/uncertainty` 科研执行总章程

> 版本：**0.3.0**  
> 状态：**JCAP manuscript freeze = ACTIVE；UQ sequel = PRESCREEN；Nature-tier Gate = CLOSED**  
> 基准日期：2026-07-23  
> 文献事实冻结日期：2026-07-21；冻结后出现的新工作必须进入月度竞争审计  
> 项目代号：**BBNet-UQ / Uncertainty-aware Big-Bang Nucleosynthesis Inference**  
> 主仓库：`https://github.com/lanhung/uncertainty`  
> 默认分支：`main`  
> 本版替代：v0.2.x

本文件是项目的人类成员、科研代理、代码代理、统计代理、计算代理和论文代理必须共同遵守的最高级执行规范。任何实现、实验、图表、结论、新闻式表述和投稿决策，都必须能够追溯到任务编号、预注册文件、数据版本、配置哈希、代码提交、solver 版本和验证签字。

本项目以高影响力发现为目标，但不允许以期刊名称倒推结论。目标期刊用于定义证据强度和广泛影响门槛，不用于选择性报告、事后换数据或制造显著性。

---

## v0.3.0 变更摘要

v0.3.0 根据待投四丰度 stiff-phase JCAP 稿件重排科学关键路径：

1. 将 BBNet+ + SageNet+ + stiff-SGWB 稿件定义为当前 Track A 的真实科学 baseline；
2. 当前最高优先级改为作者资产 handoff、公开 release、干净环境复现和 JCAP 投稿冻结；
3. 近期 UQ 问题收缩为“核/弱/backend 不确定度是否改变 homogeneous stiff phase 的 lithium no-go”；
4. 首批 scalar-UQ 反应集合改为三个 deuterium reactions 加三个 Be7/Li7 flow reactions；
5. 允许使用公开 solver 进行 clean-room 自包含重建，但必须与原资产恢复明确区分；
6. 16 点 engineering smoke 先于正式 64 点 Fisher Gate；Gate 前不激活 Pilot-1k、Pilot-10k 或 Nature-method campaign；
7. `MANUSCRIPT-OBS-v1` 与后续 UQ 的 `OBS-v1` 严格分层，不得静默混用；
8. Nature Machine Intelligence 与 Nature Computational Science 路线暂时 dormant。

详细决策见 `docs/decisions/ADR-0005-manuscript-baseline-self-contained-pivot.md`，当前 desired state 见 `plan/plan.yaml`。

### v0.2.x 保留的长期治理与验证原则

v0.2.x 建立的竞争基线、预注册、Fisher Gate、多 solver 验证和集群控制面继续有效：

1. 将 PRyMordial、PRIMAT、LINX、ABCMB+LINX、2026 BBN sensitivity atlas 和函数型核反应率工作提升为强制竞争基线，而不是参考文献中的附带提及。
2. 在任何 Pilot-10k 或大规模模型训练之前增加 **Fisher/线性传播预筛选关卡**。
3. 将旧 H2“寻找重要反应”改写为“非标准膨胀下的敏感性重排与核实验价值预测”。
4. 对头部反应引入温度/能量相关的函数型扰动模态；标量 `q_i` 仅作为基线。
5. 将 neutron lifetime 的 beam/bottle 张力单列为预注册稳健性维度。
6. 新增观测数据冻结协议，主分析与 EMPRESS、替代 D/H、替代 CMB/GW 数据组合严格分离。
7. 将“solver 差异”拆解为数值引擎、核反应率库、弱反应处理、扩展宇宙学实现四类来源，禁止混称。
8. 将 Nature Astronomy、Nature Machine Intelligence、Nature Computational Science、Nature Communications 分成四种不同的论文路线与验收门槛。
9. 将 AutoDL 计划改为“CPU 数据工厂 + 单卡训练 + 按需验证/A100”，区分科学所需 GPU 与平台附带 GPU。
10. 新增外部复现、月度竞争审计、claim-evidence matrix、编辑预询问材料和独立红队签字。
11. 新增共享 Vultr 项目隔离控制面、两台弹性 AutoDL worker pool、外部任务 ledger、长任务 heartbeat/checkpoint、独立 `ops-status` 快照分支和 dashboard；任何长任务不得只存在于 Codex/SSH 会话中。

---

## 0. 项目使命、目标期刊与不可妥协原则

### 0.1 总使命

建立一个端到端、物理驱动、统计校准、可解释且可复现的 BBN 不确定度推断系统，将下列来源统一传播到最终物理结论：

1. 非标准早期宇宙参数 `theta`；
2. 核反应率标量 nuisance parameters `q`；
3. 关键核反应的函数型不确定度模态 `a`；
4. 中子寿命与弱反应归一化；
5. 数值 solver、反应网络和 rate compilation 的差异；
6. emulator 的近似误差与 epistemic uncertainty；
7. 轻元素观测、CMB、SGWB/PTA/LVK 数据误差和系统学；
8. prior、参数化和模型选择不确定度。

最终目标不是制造一个更大的神经网络，而是回答：

> **在完整传播函数型核反应率不确定度、弱反应不确定度和多 solver discrepancy 后，BBN 对非标准膨胀历史、刚性后暴胀时期、蓝倾张量谱与可观测随机引力波背景的结论是否发生此前未被认识的改变？**

同时回答一个计算科学问题：

> **能否在具有高维 nuisance variables、函数型输入、多保真 stiff-ODE solver 和昂贵后验校准的科学推断中，以可验证的误差控制显著减少高保真模拟调用？**

### 0.2 论文组合，而不是一篇论文承担所有目标

#### Track A — 四丰度 JCAP 稿件冻结与公开复现线

目的：冻结并提交已经形成的 BBNet+ + SageNet+ + stiff-SGWB 四丰度分析，不允许被后续核反应率 UQ 或通用 ML 方法无限拖延。

最低交付：

- 精确登记 `kappa10 = rho_stiff/rho_gamma` at `T=10 MeV` 及 stiff/SGWB/reheating 参数合同；
- 四丰度 BBNet+ 代码、weights、scalers、训练配置与数据 lineage；
- modified PArthENoPE/AlterBBN source、patch 或准确的受限可用性说明；
- clean-environment emulator accuracy、main posterior、partial-likelihood 与 deterministic no-go reproduction；
- hard/soft、consistency relation、free-`Delta N_eff` 与 free-`kappa10` diagnostics 的可追溯配置；
- tagged GitHub release、Zenodo chain/scan archive、checksums 与可验证的数据/软件可用性陈述。

Track A 的当前目标是 JCAP 投稿。它不等待完整 nuclear-rate UQ；后者是独立续篇。

#### Track B-PA — Physical/Astronomy Discovery Route

**首选目标：Nature Astronomy。**

只有当中心贡献是广泛天文学/宇宙学发现时启用，例如：

- 完整不确定度传播改变一类 stiff-era/blue-tilted SGWB 模型的可行性；
- BBN 允许区域与 LVK/PTA/LISA/ET 可探测区域的交集发生稳健的拓扑或数量级变化；
- 非标准膨胀使核反应敏感性排序重排，改变未来核实验对早期宇宙约束的优先级；
- 揭示一个被广泛使用的 BBN 近似在重要早期宇宙模型上系统失效。

论文标题、摘要和第一张主图必须以物理发现为中心，AI 只能是实现发现的工具。

#### Track B-CS — Computational Science Route

**候选目标：Nature Computational Science。**

只有当中心贡献是可迁移的计算方法或框架时启用，例如：

- 新的多保真、nuisance-aware、误差可审计的模拟推断方法；
- 在保持 coverage 和 posterior fidelity 的前提下，将端到端高保真 solver 成本降低至少一个数量级；
- 方法对 BBN 之外至少一个独立 stiff-ODE/科学模拟问题同样有效；
- 发布可复用软件、基准套件和明确的计算复杂度/资源分析。

仅在 BBN 上训练一个 flow 或 MLP 不满足该路线。

#### Track B-ML — Machine Intelligence Route

**候选目标：Nature Machine Intelligence。**

该路线门槛最高，只有当项目产生真正通用的机器学习贡献时启用：

- 提出新的学习目标、算法或理论，而不是将现有 NPE/NLE/NRE/flow 应用于 BBN；
- 系统解决“高维 nuisance + 函数型不确定度 + 多保真 simulator + 有限预算”问题；
- 在公开 SBI 基准、至少两个真实科学 simulator、不同 nuisance 维数和不同 simulation budgets 上稳定优于强基线；
- 报告校准、失败模式、计算成本、统计显著性和跨任务泛化；
- BBN 是旗舰科学案例，但不是唯一证据。

#### Track B-NC — Broad Multidisciplinary Route

**候选目标：Nature Communications。**

该路线适用于：

- 物理发现对专业早期宇宙/核天体物理群体构成重要进展，但广度不足以支撑 Nature Astronomy；
- 计算方法和物理应用共同构成显著跨学科进展，但尚不足以满足 NMI/Nature Computational Science 的通用方法门槛；
- 完成严格的多 solver、数据、prior、coverage 和开放复现验证。

“最差 Nature Communications”只能作为目标序列，不能作为接收保证。若结果不达到相应编辑门槛，必须诚实调整，而不是夸大主张。

### 0.3 Nature-tier 七问

任何 Nature Portfolio 主投稿在开放 gate 前必须能用非术语语言回答：

1. **发现了什么？** 一句话内给出，不能只说“我们开发了一个框架”。
2. **为什么令人意外？** 必须指出与当前默认认识、近似或预测的差异。
3. **谁会改变做法？** 至少涉及两个群体，如早期宇宙、GW、核实验、精密宇宙学、科学机器学习。
4. **没有这项工作会错在哪里？** 指出一个具体错误结论、遗漏区域或不可行计算。
5. **证据是否独立？** 至少两个 solver/network、多个数据选择、独立验证和外部式复现。
6. **结果能否被检验？** 对未来核实验、GW 探测器或新观测给出明确预测。
7. **为什么是现在？** 说明最新数据、solver、核实验或计算方法使问题第一次可解。

任何一问无法回答，Nature-tier Gate 保持关闭。

### 0.4 不可妥协原则

项目优先级固定为：

```text
物理正确性
> 数据与模型预注册
> 可校准的不确定度
> 跨 solver / rate library 稳健性
> 可复现性
> 端到端计算效率
> 模型新颖性
> 目标期刊与宣传性
```

禁止：

- 以期刊目标倒推显著性；
- 在看到最终结果后更换主数据、prior、rate set 或主统计量而不登记；
- 把固定退化参数后的条件响应称为真实约束；
- 将 AI 自行生成而未经 solver 标注的数据视为物理真值；
- 将 rate-library 差异、solver numerical error 和 weak-rate 差异混为“solver discrepancy”；
- 把标准 BBN 中已知的关键氘反应重新排序包装为发现；
- 把网络速度或参数量包装为物理发现；
- 承诺一定发表在任何指定期刊。

### 0.5 当前 manuscript-first 执行覆盖

当前任务顺序由 `ADR-0005` 与 `docs/ops/SCIENCE_CRITICAL_PATH_v2.md` 约束：

```text
JCAP asset/release/reproduction
> self-contained core-6 scalar smoke
> formal 64-point Fisher Gate
> conditional Pilot/Nature campaign
```

第二台 AutoDL、ABCMB full audit、通用 LINX gradient audit、W0–W3 challenge 和新 ML architecture 都不是当前科学关键路径。`plan/plan.yaml` 中不存在的 conditional task 不得提前启动。

### 0.6 当前状态与 Track B 冻结阻塞项

Track B 在以下文件全部签字前为 **NOT FROZEN**：

```text
docs/literature/COMPETITOR_MATRIX_v1.md
docs/literature/NOVELTY_CLEARANCE_v1.md
docs/preregistration/OBSERVATION_FREEZE_v1.md
docs/preregistration/NUCLEAR_PRIOR_FREEZE_v1.md
docs/preregistration/PHYSICS_ENDPOINTS_v1.md
docs/decisions/ADR-SOLVER-FACTORIAL-v1.md
docs/decisions/ADR-FISHER-GATE-v1.md
artifacts/gates/FISHER_GATE_REPORT_v1.md
```

阻塞任务：

- `LIT-02`：竞争矩阵和 claim audit；
- `OBS-01`：观测数据冻结；
- `NUC-01`：rate prior 与 neutron lifetime 冻结；
- `SOL-01`：solver × rate library × weak physics 因子矩阵；
- `FISH-01`：廉价预筛选；
- `RATE-F01`：函数型 rate 模态可行性；
- `WHY-01`：为什么不直接使用 LINX/PRyMordial/PRIMAT/ABCMB+LINX。

---

## 1. 生成模型、科学假设与可证伪终点

### 1.1 变量与层级

- `theta`：关心的宇宙学/早期宇宙参数；由 `configs/physics/parameter_schema.yaml` 唯一确定。
- `q_i`：第 `i` 个标量核反应率 nuisance parameter，默认 `q_i ~ Normal(0, 1)`。
- `a_ik`：第 `i` 个关键反应的第 `k` 个函数型 S-factor/rate 模态系数。
- `tau_n`：中子寿命 nuisance parameter 或 mixture component。
- `e`：数值引擎，如 PArthENoPE、AlterBBN、PRyMordial、LINX、PRIMAT。
- `r`：核反应率库/网络，如 PArthENoPE-like、NACRE II-like、PRIMAT-2018/2023、GP-data-driven。
- `w`：弱反应与中微子热史处理。
- `m`：扩展宇宙学实现版本。
- `y`：轻元素丰度向量，包括 `Y_p`、`D/H`、`3He/H`、`7Li/H`；稿件 stratum 中 lithium 是被检验的 no-go endpoint，后续 UQ stratum 的具体 likelihood 由数据 registry 决定。
- `d`：观测数据，包括 abundance、CMB、SGWB/PTA/LVK 等。
- `epsilon_num`：数值误差。
- `epsilon_emu`：emulator approximation error。

完整生成关系写为：

```text
q, a, tau_n ~ nuclear_and_weak_priors
engine, rate_library, weak_model, extension_impl ~ registered_model_choices
y_true = S(theta, q, a, tau_n; engine, rate_library, weak_model, extension_impl)
y_pred = emulator(y_true | training_data) + epsilon_emu
d ~ likelihood(y_pred, observational_systematics)
```

任何简化模型都必须明确删除了哪一层。

### 1.2 标量反应率基线

对普通反应率，默认基线为：

```text
log r_i(T) = log rbar_i(T) + q_i * sigma_i(T),  q_i ~ Normal(0, 1)
```

其中 `q_i` 是一个标量，表示沿已给定温度依赖误差包络的整体位移。该参数化是基线接口，不构成方法创新。

### 1.3 函数型反应率模型

对头部反应，必须测试 S-factor 或 rate shape 的函数型不确定度：

```text
log S_i(E) = mu_i(E) + sum_k a_ik * sqrt(lambda_ik) * phi_ik(E)
a_ik ~ Normal(0, 1)
```

并通过热平均得到：

```text
r_i(T) = ThermalIntegral[S_i(E), T]
```

首批 decision-focused scalar-UQ 集合固定为：

- `d(p,gamma)3He`；
- `d(d,n)3He`；
- `d(d,p)t`；
- `3He(alpha,gamma)7Be`；
- `7Be(n,p)7Li`；
- `7Li(p,alpha)4He`。

函数型模式只为 scalar smoke/Fisher 显示会改变 lithium no-go endpoint 的反应构造，不因历史习惯预先固定。

函数基底可来自：

- 核实验数据的 Gaussian-process posterior；
- posterior covariance 的 KL/PCA 模态；
- 物理可解释的 normalization/slope/curvature basis；
- 分层贝叶斯核反应率分析的 posterior draws。

`K_i` 的选择必须由交叉验证与累计后验方差确定，不得任意设定。函数型和标量模型必须使用相同核数据，避免重复计入归一化误差。

### 1.4 discrepancy 的可识别分解

不得直接写：

```text
y = f(theta) + solver_noise
```

必须至少概念性分解：

```text
delta_total = delta_engine
            + delta_rate_library
            + delta_weak_physics
            + delta_extension_implementation
            + delta_numerical_precision
```

优先通过匹配输入物理的成对实验识别各项；只有剩余不可识别部分才进入层级 discrepancy prior。

### 1.5 主物理问题

主问题冻结为：

> 在非标准早期膨胀历史中，对标量与函数型核反应率、中子寿命、反应率库和数值实现进行完整传播后，BBN 对 stiff-era duration、transition temperature、reheating history、tensor tilt/amplitude 与 SGWB 可探测性的限制是否发生稳健且具有观测意义的改变？

主结果必须同时报告：

- 后验位置与宽度；
- 可行参数体积；
- 与现实探测器灵敏度区域的交集；
- 结论跨数据、solver、rate library 和 prior 的稳定性；
- 哪一种不确定度驱动改变。

### 1.6 主计算/智能问题

方法问题冻结为：

> 能否构建一种 nuisance-aware multi-fidelity simulation inference 方法，在高维标量和函数型 nuisance variables 下，以明确的 coverage/后验风险约束自动分配高保真 solver 调用，并在端到端成本上显著优于直接 LINX/PRyMordial/PRIMAT 推断？

候选方法不得预先锁定为 GAN、flow、Transformer 或 diffusion。架构必须由强基线和 learning curve 决定。

### 1.7 可证伪假设

#### H1 — 非恒定理论协方差

`C_rate(theta)` 在扩展宇宙学空间显著变化，常数 `sigma_th` 无法保持后验正确性。

否证条件：在预注册范围内，常数误差与完整边缘化导致的所有核心参数偏移 `<0.1 sigma`、区间变化 `<5%`，且无 posterior topology 变化。

#### H2 — 非标准膨胀下敏感性重排与核实验价值

标准 BBN 中已知的 rate sensitivity ranking 在 stiff/extra-radiation/reheating 等模型下发生可测重排，并能转化为不同的核实验 value-of-information。

成功证据包括：

- 关键反应 rank inversion；
- standard 与 non-standard 的 Kendall/Spearman 排名相关明显下降；
- 某 rate 精度提升对目标新物理参数的收益显著高于对标准 `Omega_b h^2` 的收益；
- 结果跨至少两个 rate library 稳健。

仅重新得到三个已知氘燃烧反应最重要，不算成功。

#### H3 — 函数型 rate shape 重要

至少一个头部反应的 shape 模态对 D/H、目标扩展参数或 detector-relevant region 的影响不能被单一 normalization `q_i` 吸收。

否证条件：函数型模型相对标量模型的 posterior 差异 `<0.1 sigma`、区间变化 `<5%`，且 posterior predictive/tail coverage 无改善。

#### H4 — rate library 与 engine discrepancy 可分离

在匹配输入物理后，数值引擎差异小于 rate-library/weak-physics 差异，或能够被独立量化；若相反，则必须找到具体数值/实现原因。

#### H5 — 早期宇宙物理结论被改变

完整传播后，至少一个 stiff-era/SGWB 结论发生决策相关变化，例如：

- 原先“可探测”区域变成“不可探测”，或相反；
- BBN 与 LVK/PTA/未来探测器允许区域的交集体积变化达到预注册阈值；
- exclusion contour 发生拓扑变化；
- 某模型证据等级发生稳健改变。

#### H6 — emulator 具有必要性

在计入训练数据成本后，hybrid emulator 在相同 posterior fidelity 与 coverage 下显著降低以下至少一项成本：

- 1,000 次 SBC；
- 多 solver × 多数据 × 多 prior 系统扫描；
- 百维 nuisance 的重复边缘化；
- 大规模 detector forecast；
- posterior-focused active refinement。

若 direct LINX/PRyMordial/PRIMAT 在总成本上同样可行，则不得以“速度”为核心创新。

#### H7 — 方法具有跨任务泛化

仅在启用 NMI/Nature Computational Science 路线时检验。方法必须在 BBN 之外的公开科学 simulator 上保持校准和效率优势。

### 1.8 主终点与辅助终点

#### 物理主终点

1. `V_detectable_full / V_detectable_baseline`：与预注册 GW 灵敏度区域相交的后验/可行体积比；
2. 核心参数 normalized shift：`Delta median / sigma_reference`；
3. credible interval ratio；
4. exclusion topology 或 posterior mode 变化；
5. model probability/Bayes factor，仅在 prior 稳健时使用；
6. sensitivity ranking change 与 nuclear value-of-information。

#### 计算主终点

1. 达到目标 posterior risk/coverage 所需的高保真 solver calls；
2. 端到端 wall time、CPU-core-hours、GPU-hours 和费用；
3. ESS/hour；
4. 1,000 次 SBC 总成本；
5. nuisance dimension 与函数模态数量的 scaling；
6. failure/OOD/fallback 率。

#### 辅助终点

- MSE、NLL、CRPS、energy score；
- 单次 forward speed；
- 模型参数量；
- GPU 利用率。

辅助终点不得替代主终点。

### 1.9 Claim Ladder

所有论文主张标记为：

- `C0`：软件/工程复现；
- `C1`：数值精度或加速；
- `C2`：统计校准或方法优越性；
- `C3`：特定 BBN/早期宇宙物理结论；
- `C4`：跨群体、改变领域认识或实验策略的广泛发现。

Nature Astronomy 主稿至少需要一个经独立验证的 `C4` 物理主张。  
Nature Machine Intelligence 至少需要一个跨任务成立的 `C4` 方法主张。  
Nature Computational Science 至少需要一个广泛可迁移的 `C3/C4` 计算主张。  
Nature Communications 至少需要一个强 `C3` 主张。

---

## 2. 文献边界、竞争基线与 Novelty Clearance

### 2.1 已被覆盖、不得单独宣称首创的内容

- 用神经网络快速预测 BBN 丰度；
- BBNet 对扩展 cosmology 的 PArthENoPE/AlterBBN emulator；
- JAX 可微 BBN solver；
- 标量 `nuclear_rates_q` 和 `tau_n_fac`；
- 标准 BBN/CMB 中显式边缘化核反应率；
- PRyMordial 中使用 log-normal rate nuisance；
- 标准 BBN 中识别 `d(p,gamma)3He`、`d(d,n)3He`、`d(d,p)t` 为关键氘反应；
- 标准 BBN 的大规模 sensitivity atlas；
- 用 GP 从核实验数据拟合头部氘反应并传播到 D/H；
- 用 PCA 约束一般 BBN 膨胀历史；
- 仅将输入从 10 维扩大到约 100 维；
- 仅使用 normalizing flow、GAN、diffusion、Transformer 或 active learning。

### 2.2 强制竞争矩阵

`docs/literature/COMPETITOR_MATRIX_v1.md` 必须至少包含：

| 对象 | 已解决问题 | 可用 rate uncertainty | 非标准 cosmology | differentiable | joint inference | 本项目必须超越之处 |
|---|---|---|---|---|---|---|
| BBNet | 扩展 BBN emulator | 当前以中心值为主 | 是 | 否/有限 | 可嵌入 | 分布与完整 UQ |
| LINX | 快速可微 BBN | `nuclear_rates_q`、多网络 | 可扩展 | 是 | CMB+BBN | 项目特定扩展、函数型 rates、多 solver、SBC 规模 |
| ABCMB+LINX | 可微 CMB+BBN 栈 | 继承 LINX | 可扩展 | 是 | 是 | SGWB/stiff 专用物理、端到端成本、函数型 nuisance |
| PRyMordial | 标准/新物理 BBN | log-normal marginalization | 是 | 有限 | 可接采样器 | 项目扩展、函数型 rates、多保真/主动学习 |
| PRIMAT | 高精度 BBN | rate uncertainty | 有限/可修改 | 否/有限 | 可外接 | 作为高精度独立验证 |
| PArthENoPE v3 | 成熟 BBN | 近似/MC UQ | 项目已有修改 | 否 | 外接 | 主扩展 solver 与基准 |
| AlterBBN | 快速 BSM BBN | ERR/上下界/MC | 是 | 否 | 外接 | 工程交叉，不作为唯一精密极点 |
| Cook–Meyers | 一般膨胀历史 PCA | 使用现代 BBN 输入 | 是 | 不适用 | 物理约束 | 本项目必须加入完整 nuclear/solver UQ 和 SGWB 联动 |
| 2026 sensitivity atlas | 14 参数、63 rates 排名 | 是 | BSM 参考 | 否 | 否 | 非标准膨胀下重排和实验价值，而非重复标准排名 |
| 2026 GP D/H | 三个氘反应函数拟合 | GP shape posterior | 标准 BBN | 否/可接 | 否 | 将函数模态传播到扩展后验和 GW 物理 |
| LVK O1–O4a stiff search | 直接 GW 数据限制 | 不涉及 nuclear rates | stiff era | 否 | GW likelihood | 与自洽 BBN UQ 联合而非只叠加近似 bound |

矩阵必须记录版本、发布日期、代码链接、许可证、当前限制和可复现状态。

### 2.3 “为什么不用现有工具”四问

正式主稿前必须形成一页定量回答：

#### Q1：为什么不直接使用 LINX？

允许的答案只能来自实测：

- 项目的扩展 cosmology/SGWB/stiff 参数未被原生覆盖；
- 函数型 rate posterior 或多 solver discrepancy 未被覆盖；
- 1,000 次 SBC、多数据组合或大规模 forecast 的总成本仍过高；
- hybrid 方法在相同 fidelity 下显著减少高保真调用。

“神经网络更现代”不是答案。

#### Q2：为什么不直接使用 PRyMordial？

必须比较标准 BBN 和至少一个扩展模型的端到端 runtime、rate marginalization、可修改性和后验恢复。

#### Q3：为什么不直接使用 PRIMAT？

必须说明 PRIMAT 作为高精度 reference 的角色，以及项目扩展物理和大规模推断的缺口。

#### Q4：为什么不使用 ABCMB+LINX 完成全可微联合推断？

必须 benchmark Fisher、HMC/NUTS、梯度稳定性、FP64 成本和扩展模型开发成本。

### 2.4 月度竞争审计

从 2026-07-21 起，每月第一个工作日执行 `LIT-WATCH`：

- 搜索 arXiv `astro-ph.CO`、`hep-ph`、`nucl-th`、`cs.LG`；
- 搜索 BBN、nuclear rates、SBI、nuisance parameters、multi-fidelity、stiff SGWB；
- 更新 competitor matrix；
- 对所有标题/摘要中的“first”“novel”“unprecedented”重新审计；
- 若出现直接竞争工作，72 小时内提交影响评估 ADR。

### 2.5 Novelty Clearance Gate

`NOVELTY_CLEARANCE_v1.md` 必须回答：

1. 项目主张与 BBNet、LINX、PRyMordial、PRIMAT 的最小差集是什么？
2. 标准 BBN 已知结果有哪些只作为回归测试？
3. 哪个结果即使没有 AI 也具有物理新颖性？
4. 哪个方法即使移除 BBN 也具有计算/ML 新颖性？
5. 最可能的三条审稿拒绝理由是什么？
6. 每条拒绝理由对应哪个预先设计的实验？
7. 若主物理效应很小，如何停止而不是扩大搜索自由度？

A00、A11、A09 必须共同签字；开发模型的代理不得单独批准自己的 novelty claim。

### 2.6 Claim Blacklist

未经新增证据，禁止使用：

- “首次完整边缘化 BBN 核反应率”；
- “首次识别关键 BBN 反应”；
- “首个可微 BBN/CMB 联合推断”；
- “解决 lithium problem”；
- “模型无关”，除非明确给出模型空间；
- “solver-independent”，除非经过匹配物理和至少三个独立实现；
- “精确”，除非误差预算完整；
- “unbiased”，除非通过 SBC/coverage 和挑战集。

---

## 3. 预注册：观测、核数据、弱反应、prior 与盲化

### 3.1 观测数据冻结 `OBS-v1`

在最终 Track B production 之前创建：

```text
configs/data/abundance_OBS-v1.yaml
docs/preregistration/OBSERVATION_FREEZE_v1.md
```

默认工作基线在 Day 6 前冻结为：

- `Y_p` 主候选：LBT 2026，`Y_p = 0.2458 ± 0.0013`；
- `D/H` 候选 A：Cooke et al. 2018 同质高精度样本，`10^5 D/H = 2.527 ± 0.030`；
- `D/H` 候选 B：Kislitsyn et al. 2024 更新汇编；全样本为 `2.533 ± 0.024`，其九个 precision systems 子样本为 `2.501 ± 0.028`；
- `OBS-v1` 必须在查看 Track B 最终效应前，从候选 A/B 中预注册一个主分析，并将另一个及其子样本定义为强制稳健性检验；禁止把数值最有利的 compilation 事后升级为主数据；
- `Li/H`：不进入默认主 likelihood，仅作 null test；
- CMB：先使用明确来源的 `Omega_b h^2` prior，后续再升级为一致的 joint likelihood；
- SGWB：使用公开的 LVK O1–O4a likelihood/upper-limit 产品或经验证的近似；
- forecast：LISA/ET/CE 等必须与现实数据结果分开存放、分开作图。

必须预注册的 stress tests：

- EMPRESS 2026 较低 `Y_p` 结果；
- legacy/PDG/Aver 型 `Y_p`；
- Cooke-2018 homogeneous sample、Kislitsyn-2024 all-sample 与 precision-subsample 的互换；
- CMB 数据组合替换；
- GW likelihood/谱参数化替换。

任何主数据选择变化必须发生在最终物理结果解盲之前。EMPRESS 只能描述为在特定模型/数据组合下存在张力，不得预设其错误。

### 3.2 观测 likelihood 规则

- 原论文提供非高斯 posterior 时，不得擅自高斯化而不验证；
- 共享系统学必须进入 covariance 或层级 nuisance；
- 不同 abundance compilation 可能共享对象，禁止视为完全独立后简单相乘；
- 数据版本、下载时间、原始表格 hash 和解析脚本必须登记；
- 任何数据清洗/剔除规则在解盲前冻结。

### 3.3 核反应率 prior 冻结

创建 `configs/physics/nuclear_prior_NUC-v1.yaml`，每个 rate/mode 必须记录：

- 物理反应式与唯一 ID；
- 核数据来源和版本；
- rate compilation；
- 中心值；
- scalar `sigma_i(T)`；
- 函数型 basis、eigenvalue 与能量网格；
- 共享实验 normalization/correlation；
- forward/reverse rate 的详细平衡处理；
- 是否进入 core、extended、full stress set；
- 许可证和原始数据 checksum。

禁止假设所有 reaction rates 独立。若文献没有相关矩阵，必须明确“未建模相关性”并做 sensitivity stress test。

### 3.4 Neutron lifetime 预注册

至少定义四种场景：

- `N0`：项目主 baseline 连续 prior；
- `N1`：bottle-only；
- `N2`：beam-only；
- `N3`：beam/bottle mixture 或额外 discrepancy 模型。

主 baseline 必须在最终结果前选择并说明依据；其他三种进入附录/稳健性。不得在看到 `Y_p` 或新物理显著性后选择最有利场景。

### 3.5 物理 prior 冻结

`configs/physics/parameter_schema.yaml` 对每个参数登记：

- 符号、定义、单位；
- sampling transform；
- prior 与来源；
- 物理边界；
- 是否主参数、nuisance、hyperparameter；
- 与哪些数据敏感；
- 是否存在 identifiability 风险；
- 在条件切片中固定的 fiducial 值。

`kappa`、`n_t`、`T_re`、stiff-era transition 参数必须明确区分模型定义，禁止同名参数跨代码含义不一致。

### 3.6 盲化与解盲

在 production inference 前冻结：

- 主数据组合；
- 主模型与替代模型；
- 主统计量；
- Nature-tier effect-size gate；
- 核心图布局；
- exclusion/decision rule；
- 异常点处理规则；
- 训练 seed 数量；
- validation set。

解盲前允许查看：

- solver 回归；
- synthetic-data recovery；
- Fisher/Laplace 预筛选；
- 隐去真实标签的 pipeline diagnostics。

解盲后任何修改进入：

```text
docs/preregistration/DEVIATION_LOG.md
```

并标明 `confirmatory` 或 `exploratory`。

---

## 4. Solver 因子分解、推断模型梯级与仓库执行契约

### 4.1 禁止把“solver 差异”当成单一黑箱

轻元素丰度预测统一写为：

\[
\mathbf y =
\mathcal F(
\theta,\mathbf q,\mathbf a,\tau_n;
E,R,W,X,\nu
)+\epsilon_{\rm num},
\]

其中：

- `E`：数值引擎及其积分器、容差、精度和线性代数实现；
- `R`：核反应率中心值、误差模型、相关性和 rate compilation；
- `W`：弱反应、neutrino decoupling 和 neutron lifetime 处理；
- `X`：非标准膨胀、暗辐射、stiff era、reheating 等扩展物理实现；
- `nu`：network topology、核素集合、反应集合和筛选规则；
- `epsilon_num`：有限容差、插值和浮点误差。

任何“PArthENoPE 与 AlterBBN 相差多少”的结果，只有在上述因素被尽可能匹配后，才能被解释为 engine discrepancy。否则只能称为 **pipeline discrepancy**。

#### 4.1.1 强制基线矩阵

| ID | 工具/网络 | 主要角色 | 允许承担的结论 |
|---|---|---|---|
| `S0` | 项目修改版 PArthENoPE | 扩展宇宙学主高保真 solver | Track A/B 主生产候选，必须完成版本审计 |
| `S1` | 项目修改版 AlterBBN | legacy 与扩展物理工程交叉检查 | 不得单独代表独立核数据极端 |
| `S2` | 官方 PArthENoPE v3 | 标准 BBN 与实验型 rate baseline | 标准区回归、rate 处理对照 |
| `S3` | PRyMordial + NACRE-II-like 配置 | 显式、较保守 rate marginalization baseline | 标准 BBN 与 rate-prior 对照 |
| `S4` | PRyMordial + PRIMAT-like 配置 | 理论/ab-initio 倾向 rate baseline | rate-compilation 对照 |
| `S5` | LINX `key_PArthENoPE` | JAX/可微核心网络 | direct gradient/HMC baseline |
| `S6` | LINX `key_PRIMAT_2023` | JAX/PRIMAT 核心网络 | direct gradient/HMC baseline |
| `S7` | LINX `full_PRIMAT_2023` | JAX 全网络 stress test | full-network 稳健性与成本基准 |
| `S8` | 直接 PRIMAT Python/C 实现 | 独立高精度审计 | 关键点、关键切片和最终主张复核 |

`S8` 不要求覆盖全部生产点，但必须覆盖：

- 标准 BBN fiducial；
- 观测后验高密度区至少 100 个点；
- 每个旗舰结论边界附近至少 100 个点；
- 每个关键函数型 rate 模态的 `-2, -1, 0, +1, +2 sigma`；
- 发现主张中最重要的 20 个 adversarial points。

#### 4.1.2 四组 matched-physics 实验

1. **Engine match**：固定 `R,W,X,nu`，只改变 `E`；
2. **Rate-library match**：固定 `E,W,X,nu`，只改变 `R`；
3. **Weak-physics match**：固定 `E,R,X,nu`，只改变 `W`；
4. **Extension match**：固定标准模块，分别实现同一 `X`，比较非标准物理注入。

每组实验输出：

- 绝对丰度差；
- 以总观测标准差归一化的差；
- Jacobian 差异；
- 后验中位数和可信区间差异；
- 对 flagship decision boundary 的影响；
- 差异能否由数值容差解释。

#### 4.1.3 Solver 接受标准

任一 solver 进入 production 前必须：

- 在批准的标准 benchmark 上通过数值回归；
- 记录代码 commit/tag、编译器、编译 flags、BLAS、float precision；
- 将冷启动、热启动、单点、批处理吞吐分别测量；
- 在容差扫描中表现出收敛平台；
- 对非标准参数的物理定义和单位有独立审查；
- 对失败点返回结构化状态，不得静默给出 NaN、截断值或默认值；
- 生成 `solver_card.yaml` 和可重跑的 benchmark report。

如果 matched-physics 后仍存在超出数值误差的差异，必须引入显式 discrepancy 层，不能任意选择一个 solver 当“真值”。

### 4.2 推断模型梯级

所有实验使用以下固定编号，论文、配置和图表必须引用模型编号。

#### `M0` — Central-rate deterministic baseline

\[
\mathbf y=f(\theta,\mathbf q=0,\mathbf a=0,\tau_n=\bar\tau_n).
\]

用途：回归、Track A、速度基线。不得用于宣称完整理论不确定度。

#### `M1` — Constant post-hoc theoretical error

\[
C_{\rm like}=C_{\rm obs}+C_{\rm th,constant}.
\]

用途：复现传统近似并作为被检验对象。必须说明 `C_th` 的获取位置和固定参数。

#### `M2` — Explicit scalar nuisance marginalization

\[
\mathbf q\sim p(\mathbf q),\qquad
p(\theta\mid d)\propto
\int p(d\mid f(\theta,\mathbf q,\tau_n))p(\mathbf q)p(\tau_n)\,d\mathbf q\,d\tau_n.
\]

用途：强物理 baseline；与 LINX/PRyMordial 对照。

#### `M3` — Functional-rate nuisance marginalization

在 `M2` 上加入头部反应的函数型模态 `a_ik`。用途：检验整体缩放假设是否遗漏 shape uncertainty。

#### `M4` — Learned marginalized abundance distribution

直接学习：

\[
p(\mathbf y\mid\theta,E,R,W,X),
\]

但训练标签必须来自批准的 solver+nuclear posterior。用途：摊销 nuisance marginalization。

#### `M5` — Multi-solver hierarchical discrepancy

学习或显式采样：

\[
p(\mathbf y\mid\theta,R,W,X,E),
\qquad E\sim p(E),
\]

并区分共享物理不确定度和 engine-specific residual。用途：跨 solver 稳健推断。

#### `M6` — Direct-solver reference inference

使用 LINX、PRyMordial、PRIMAT 或项目高保真 solver 直接采样，不经过主要 emulator。用途：后验恢复与端到端成本基线。

#### `M7` — Hybrid emulator with certified fallback

在安全域使用 emulator；在 OOD、高不确定度、边界决策区调用高保真 solver。用途：最终生产候选与 NCS/NMI 路线。

#### 4.2.1 最低比较要求

- Track A：`M0`；
- Fisher Gate：`M0/M1/M2` 的局部近似；
- Track B 物理主张：至少 `M0/M1/M2/M3/M6`；
- multi-solver 主张：加入 `M5`；
- NCS/NMI 主张：加入 `M4/M7` 和强非深度基线；
- 任何“新方法更快”结论必须与 `M6` 的完整端到端任务比较，而非只比单次 forward。

### 4.3 仓库目录契约

仓库最终至少包含：

```text
uncertainty/
├── AGENTS.md
├── README.md
├── CITATION.cff
├── LICENSE
├── pyproject.toml
├── uv.lock                         # 或等价锁文件
├── .pre-commit-config.yaml
├── .github/
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── configs/
│   ├── data/
│   │   ├── abundance_data_v1.yaml
│   │   ├── cmb_data_v1.yaml
│   │   └── gw_data_v1.yaml
│   ├── physics/
│   │   ├── parameter_schema.yaml
│   │   ├── neutron_lifetime_v1.yaml
│   │   └── expansion_models/
│   ├── nuclear/
│   │   ├── rate_registry_v1.yaml
│   │   ├── correlations_v1.yaml
│   │   └── functional_modes_v1.yaml
│   ├── solvers/
│   ├── datasets/
│   ├── models/
│   └── inference/
├── src/uncertainty/
│   ├── cli/
│   ├── physics/
│   ├── nuclear/
│   ├── solvers/
│   │   ├── base.py
│   │   ├── parthenope/
│   │   ├── alterbbn/
│   │   ├── linx/
│   │   ├── prymordial/
│   │   └── primat/
│   ├── design/
│   ├── datasets/
│   ├── models/
│   ├── inference/
│   ├── validation/
│   ├── metrics/
│   ├── plotting/
│   └── provenance/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── scientific/
├── workflows/
│   ├── autodl/
│   ├── hpc/
│   └── local/
├── scripts/
├── docs/
│   ├── decisions/
│   ├── preregistration/
│   ├── literature/
│   ├── benchmarks/
│   ├── protocols/
│   ├── claims/
│   ├── reviews/
│   └── journal/
├── manifests/
│   ├── data/
│   ├── models/
│   ├── experiments/
│   └── releases/
├── paper/
│   ├── track_a/
│   ├── nature_astronomy/
│   ├── nature_machine_intelligence/
│   ├── nature_computational_science/
│   └── nature_communications/
└── artifacts/                     # 小型、可版本化产物；大文件由 manifest 指向
```

### 4.4 单一命令行入口

所有生产能力必须通过稳定 CLI 暴露；禁止正式实验依赖只能在 notebook 中运行的隐藏状态。

最低命令集：

```bash
uq env doctor
uq solver list
uq solver benchmark --config configs/solvers/benchmark_v1.yaml
uq solver compare --matrix configs/solvers/factorial_v1.yaml
uq data freeze --config configs/data/abundance_data_v1.yaml
uq rates validate --registry configs/nuclear/rate_registry_v1.yaml
uq fisher run --config configs/inference/fisher_gate_v1.yaml
uq simulate --config configs/datasets/pilot_1k.yaml
uq simulate --config configs/datasets/pilot_10k.yaml
uq train --config configs/models/<model>.yaml
uq infer --config configs/inference/<run>.yaml
uq validate emulator --run-id <RUN_ID>
uq validate posterior --run-id <RUN_ID>
uq sbc --config configs/inference/sbc_v1.yaml
uq reproduce figure --id <FIGURE_ID>
uq reproduce claim --id <CLAIM_ID>
uq manifest verify --path manifests/releases/<release>.yaml
uq release audit --candidate <TAG>
```

每条命令必须：

- 支持 `--dry-run`；
- 输出 run ID；
- 写入 resolved config；
- 记录 git commit、dirty state、hostname、hardware、environment hash；
- 明确 exit code；
- 可从 checkpoint 恢复；
- 不覆盖已有正式结果。

### 4.5 数据与标签红线

1. **高保真标签**只能来自批准 solver 或核实验数据后验经 solver 的传播。
2. 生成模型可以提出 acquisition candidates，但候选点在成为训练标签前必须由 solver 计算。
3. 低保真输出必须带 `fidelity_id`，不得与高保真标签无标记混合。
4. 插值、失败修补和缺失值填充不得伪装成 solver 输出。
5. 每个 shard 必须包含输入、输出、状态、solver card、rate card、随机种子和 checksum。
6. 数据集拆分必须在训练前冻结；posterior-focused challenge set 不能用于超参数调优。
7. 任何删除失败点的操作都要统计失败机制；如果失败与参数相关，必须建模 selection bias。

### 4.6 必需的决策记录

Track B 冻结前至少存在：

```text
docs/decisions/ADR-PHYS-001-primary-question.md
docs/decisions/ADR-OBS-001-abundance-data-freeze.md
docs/decisions/ADR-RATE-001-rate-representation.md
docs/decisions/ADR-SOLVER-001-factorial-matrix.md
docs/decisions/ADR-ML-001-why-emulator.md
docs/decisions/ADR-COMPUTE-001-resource-topology.md
docs/preregistration/TRACK_B_PREREG_v1.md
docs/literature/NOVELTY_CLEARANCE_v1.md
```

每个 ADR 必须包含：问题、可选方案、决定、理由、反对意见、后果、复审触发器和签字人。

---

## 5. 规范性分卷与读取顺序

为避免根级 `AGENTS.md` 超长导致代码代理遗漏关键条款，项目将执行细节拆成三个科研分卷和一个**同等强制、不可选择性忽略**的运行规范：

1. [`docs/agents/EXECUTION.md`](docs/agents/EXECUTION.md)：角色、科研治理、Phase 0–9、Gate、任务与交付物；
2. [`docs/agents/COMPUTE_VALIDATION.md`](docs/agents/COMPUTE_VALIDATION.md)：AutoDL/CPU/GPU、存储、成本、统计与物理验收阈值；
3. [`docs/agents/PUBLICATION.md`](docs/agents/PUBLICATION.md)：论文路线、Milestone、首个 14 天、年度节奏、禁令、发布检查和文献清单。
4. [`AGENTS-ops.md`](AGENTS-ops.md)：Vultr/AutoDL/HPC 控制面、任务 ledger、heartbeat、checkpoint、detached 运行、状态快照与密钥安全。

执行规则：

- 根级 `AGENTS.md` 与上述四份规范共同构成项目 v0.2.1 的完整执行章程；
- 修改 solver、数据、训练、推断或论文主张前，必须读取与任务相关的分卷；跨范围任务必须读取全部分卷；
- 根文件定义科学使命、创新边界、预注册和模型合同；分卷定义实现、验证、资源和投稿合同；
- 若条款冲突，以根级 `AGENTS.md` 为最高优先级，并立即提交 ADR 修复冲突；
- 任何代理不得以“未读取分卷”为理由绕过 Gate、预注册、独立验证或算力上限；
- monolithic 冻结副本仅用于审阅和归档，不替代仓库中的根文件与分卷。

---

## 6. 运行控制面与长任务强制规则

### 6.1 状态源与服务器角色

- `plan/plan.yaml` 是 desired state；status server 的 SQLite ledger 是 observed state。
- 共享 Vultr 上本项目独立的 status-server instance 是 uncertainty ledger 的唯一 writer；worker、Codex 和人类只能经 `taskctl`/heartbeat API 更新状态。
- 物理拓扑是一台共享、轻量、常开的 Vultr 控制宿主机，加两台按需开启、可跨项目复用的 AutoDL worker；`sim`、`train` 和 `verify` 仅为任务运行时逻辑角色，不得用作物理节点的永久身份。
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
- 控制面基础决策：[`docs/decisions/ADR-0003-research-ops-control-plane.md`](docs/decisions/ADR-0003-research-ops-control-plane.md)；当前物理拓扑与隔离决策：[`docs/decisions/ADR-0004-shared-control-elastic-autodl.md`](docs/decisions/ADR-0004-shared-control-elastic-autodl.md)。

任何代理在启动生产任务前必须读取 `AGENTS-ops.md`，运行 `taskctl health`、`taskctl show` 和 plan validation，并确认没有越过 Fisher Gate、数据冻结或资源上限。

---
