# AGENTS v0.2.0 规范分卷：执行、角色与科研治理

> 本文件是根级 `AGENTS.md` 的规范性组成部分。冲突时以根级文件为准。
> 覆盖范围：角色 A00–A12、GitHub 治理、Phase 0–9、Nature Route Gate。

---

## 5. 代理角色、签署权限与交付物

一个人可以承担多个角色，但旗舰主结果的模型开发、统计验证和物理措辞审核必须保留独立检查路径。任何代理都不得绕过预注册、数据冻结或验证签署。

### A00 — Science Lead / PI Agent

职责：

- 冻结旗舰科学问题、主参数、prior、数据组合、主统计量和停止条件；
- 区分条件响应、profile likelihood、边缘化约束、模型选择和真正观测证据；
- 审核所有物理措辞、适用域、替代解释和广泛兴趣论证；
- 主持 `FISHER-GATE-01`、`FLAGSHIP-ROUTE-GATE-01` 和最终 claim freeze；
- 决定是否关闭 Nature Astronomy、NMI 或 NCS 路线。

禁止：

- 在看到结果后更换主数据、主 prior 或主检验而不登记 deviation；
- 通过固定退化参数制造显著性；
- 将方法指标、速度或单一切片当作物理发现。

签署文件：

```text
docs/validation/SCIENCE_SIGNOFF.md
```

### A01 — Repository & Reproducibility Agent

职责：

- 初始化目录、依赖锁、CI、pre-commit、版本与许可证；
- 建立一键 bootstrap、smoke、benchmark、inference 和 figure reproduction；
- 记录操作系统、CUDA、驱动、编译器、上游 solver commit 和 patch；
- 保证所有 production 命令可在非 notebook 环境运行；
- 维护 release tag、Zenodo metadata 和 `CITATION.cff`。

完成标准：

- 全新 AutoDL 实例可在 30–60 分钟内完成环境恢复与 smoke test；
- 不依赖隐藏文件、手工复制或未提交脚本；
- `make smoke`、`make test-science`、`make reproduce-mini` 均通过。

### A02 — BBN Solver & Multi-fidelity Agent

职责：

- 为 S0–S8 建立统一 adapter；
- 匹配单位、参数、rate ID、弱反应、丰度 convention 与输出 schema；
- 建立中心值、局部导数、批量运行、失败恢复和数值精度测试；
- 将 solver numerical error、reaction network、rate compilation 与新物理实现差异分开；
- 评估 direct LINX、PRyMordial、PRIMAT/PArthENoPE 的真实推断成本；
- 对扩展宇宙学修改建立独立 regression fixtures。

统一接口建议：

```python
simulate(
    theta,
    scalar_rates,
    functional_rate_modes,
    neutron_model,
    solver_id,
    network_id,
    precision,
    seed,
) -> AbundanceRecord
```

`AbundanceRecord` 必须包含：

- abundances；
- solver status 与结构化错误码；
- runtime 与资源峰值；
- input hash；
- solver/network/rate versions；
- numerical warnings；
- optional trajectories/Jacobians。

完成标准：同一物理点的跨 solver 差异可解释、可追溯；无静默 NaN、无未登记 fallback。

### A03 — Nuclear Data & Functional Uncertainty Agent

职责：

- 维护 rate registry、核数据来源、温度/能量网格、实验系统学和相关结构；
- 实现标量 log-normal 与函数型 GP/KL/spline/EFT 模态；
- 对三个头部氘反应比较 PArthENoPE、PRIMAT、NACRE II、GP 与 EFT/ab-initio 先验；
- 计算局部敏感性、Sobol/MI、active subspace、rank inversion 与 value-of-information；
- 将中子寿命、弱反应理论修正与普通热核反应分开处理；
- 维护核数据更新雷达，尤其关注新的 LUNA、J-PARC、EFT 与层级贝叶斯结果。

完成标准：每个进入推断的核参数都有物理来源、prior/posterior、单位、相关矩阵、函数表示和验证图。

### A04 — Observations & Preregistration Agent

职责：

- 完成 `OBS-01`、`NEUTRON-01` 和主 likelihood 数据冻结；
- 登记 LBT、legacy helium、EMPRESS、D/H、Li、CMB/BAO、LVK/PTA 数据；
- 保存协方差、共享系统学、数据处理脚本和替代数据矩阵；
- 在旗舰 production 解盲前冻结主数据与主 likelihood；
- 管理 `deviation_log.md`；
- 明确 forecast 与真实观测的边界。

禁止：

- 根据显著性挑选 `Y_p`、D/H、CMB 或 GW 数据；
- 将 tension 数据未经建模直接删除；
- 将 EMPRESS 预先称为错误；
- 将未来灵敏度曲线当作现有约束。

### A05 — Simulation Dataset Agent

职责：

- 生成 pilot、production、validation、challenge 和 solver-transfer 数据；
- 使用可复现的 Sobol/LHS/prior sampling 与主动学习；
- 将标准区域、非标准后验高密度区、物理边界、nuisance tail 和 OOD 分开；
- 生成 dataset card、checksum、覆盖图、失败机制与成本账本；
- 保证每个 label 来自批准的真实 solver 或经批准的核数据 posterior 传播链。

禁止：

- 将 GAN/NF/LLM 生成而未由真实 solver 标注的样本当作真值；
- 只做随机行切分；
- 静默删除失败样本；
- 先生成百万点后再思考是否需要。

### A06 — Emulator & Distribution Model Agent

必须实现并比较：

1. `f(theta, q, a, s) -> y` 的确定性显式 nuisance 基线；
2. `p(y | theta, s)` 的边缘分布模型；
3. 低秩 rate-mode 模型；
4. 多 solver hierarchical/discrepancy 模型；
5. deep ensemble、GP、Gaussian/mixture 等简单强基线；
6. OOD detector、物理安全域和 solver fallback；
7. 仅在必要时使用 diffusion 或更复杂生成模型。

禁止：

- 以模型参数量作为科学优势；
- 将一个 nuisance parameter 错误等同于一个 flow layer；
- 只报告平均 MSE；
- 在 test/challenge set 上调参；
- 将 epistemic、aleatoric、nuclear 和 solver uncertainty 混为同一方差。

完成标准：通过第 10 节验收阈值；至少 5 个训练 seed；模型卡完整。

### A07 — SBI, Active Learning & Method Innovation Agent

职责：

- 评估 NLE/NPE/NRE、conditional flows、residual likelihood、neural operators、mixture 与 diffusion；
- 设计 nuisance-aware acquisition，平衡 posterior relevance、nuisance coverage、边界、函数模态和 solver disagreement；
- 对模拟预算做 learning curve 和停止判断；
- 若走 Route NMI，提出真正新的 objective、算法、理论或安全机制；
- 若走 Route NCS/NMI，在标准 benchmark 与非 BBN 模拟器上验证；
- 对 active learning 的选择偏差和 coverage degradation 做显式校正。

完成标准：

- 相同 solver calls 下显著降低分布误差；或
- 相同 calibration/posterior bias 下显著减少 solver calls；
- 方法优势跨 seed、跨任务、跨模拟器存在。

### A08 — Bayesian Inference Agent

职责：

- 实现 M0–M7；
- 支持多链 MCMC、nested sampling、HMC/NUTS 和必要的 likelihood-free 方法；
- 统一参数变换、prior、evidence、posterior export 和 posterior predictive；
- 对 emulator posterior 与 direct LINX/PRyMordial/solver posterior 做 recovery；
- 报告所有链、ESS、MCSE、mode coverage、divergence 和 evidence error；
- 实现 profile likelihood、information gain 与 prior-to-posterior diagnostics。

### A09 — Independent Validation & Red-Team Agent

职责：

- 独立维护不可用于训练的 `CHALLENGE-BLIND`；
- 执行 SBC、coverage、posterior predictive、OOD false-safe 与 adversarial slices；
- 运行 prior、数据、solver、rate prior、neutron model、seed 和数值精度稳健性；
- 主动寻找能推翻旗舰 claim 的反例；
- 对 Nature 三句话测试、broad-interest 与过度宣传进行敌对审稿；
- 在模型冻结后独立重跑至少一个主结果。

签署文件：

```text
docs/validation/VALIDATION_PASS.md
docs/validation/RED_TEAM_REPORT.md
```

没有双签署不得提交旗舰稿。

### A10 — Compute, AutoDL & Cost Agent

职责：

- 维护实例镜像、任务队列、CPU/GPU/存储成本与失败日志；
- 数据生成按 CPU throughput 选机，训练按 GPU/显存选机；
- 对 LINX float64、JAX ODE、HMC/NUTS profiling 决定 4090 或 A100；
- 所有长任务支持 checkpoint、resume、heartbeat、自动关机与每日备份；
- 维护端到端成本比较，而非只记录训练 GPU-hours；
- 在每个 Gate 后更新资源预测。

### A11 — Literature & Competition Agent

职责：

- 每两周更新直接竞争者与最新预印本；
- 运行可执行的公开 baseline，记录 commit/version；
- 对每个新 claim 做 novelty search；
- 维护 `competitor_matrix.csv`、能力差距与“可能被抢先”清单；
- 在每个旗舰 milestone 和投稿前进行完整 literature refresh；
- 特别追踪 PRyMordial、LINX、PRIMAT、核数据 GP/EFT、LBT、CMB+BAO+BBN、LVK/SGWB 与 nuisance-aware SBI。

完成标准：任何“first”“首次”“前所未有”措辞都有日期明确的检索记录支持。

### A12 — Flagship Manuscript & Journal Strategy Agent

职责：

- 根据证据选择 Route NA、NCS、NMI 或 NC 的单一主路线；
- 维护 claim–evidence matrix、标题、摘要、cover letter 与 presubmission inquiry；
- 对每个目标期刊写一页 journal-fit memo；
- 确保标题以物理/计算/机器学习发现为中心，而不是工具名；
- 准备代码、数据、计算资源、限制、AI 使用与开放科学声明；
- 防止将同一核心贡献不当拆分成多个稿件；
- 组织外部天文学、核物理、统计与 ML 专家预审。

完成标准：编辑可在一页内理解“以前不知道什么、现在发现什么、为什么该刊读者必须关心”。

### A13 — Cross-domain Generalization & Benchmark Agent

职责：

- 只在 Route NCS/NMI 候选开启后加入，不为制造跨域数量而勉强套用任务；
- 选择至少一个具有昂贵 simulator、结构化 nuisance 或函数型输入的非 BBN 科学问题；
- 冻结跨域 benchmark 的数据、预算、指标和强基线；
- 检查方法是否真正复用同一核心算法，而非为每个任务单独定制；
- 报告 negative transfer、domain shift、scaling 和失败边界；
- 与领域专家共同签署 benchmark 的科学有效性。

完成标准：跨域结果能证明可迁移的计算/机器学习原理；仅增加一个玩具数据集不算通过。

### A14 — External Reproduction & Artifact Agent

职责：

- 在主团队冻结代码、配置和 release candidate 后，从空环境独立执行复现；
- 不读取开发者本地缓存、未提交 notebook 或私人数据路径；
- 复现至少一张主图、一个后验表、一个 solver benchmark 和一个 failure case；
- 检查许可证、数据可访问性、checksum、随机性和硬件差异；
- 记录从 README 到完成复现的全部阻塞；
- 签署或拒绝签署 `docs/validation/EXTERNAL_REPRODUCTION.md`。

旗舰提交前，A14 不应由主模型作者兼任；条件允许时由组内未参与成员或外部合作者执行。

---

## 6. GitHub 工作流与科研治理

### 6.1 分支与提交

- 本次 v0.2.0 更新后，禁止直接推送 `main`；启用 branch protection。
- 分支命名：
  - `feat/TASK-ID-short-name`
  - `fix/TASK-ID-short-name`
  - `exp/TASK-ID-short-name`
  - `paper/TASK-ID-short-name`
  - `infra/TASK-ID-short-name`
- 使用 Conventional Commits；科研实验提交可使用 `exp:`。
- 每个 PR 只解决一个任务或一个紧密耦合任务组。
- PR 必须列出：任务 ID、科学目的、物理假设、配置、测试、数据影响、资源影响、风险、复现命令和 claim 影响。

### 6.2 代码质量

- Python 主版本统一为 3.11；例外必须有 ADR。
- `ruff`、`mypy/pyright`、`pytest`、格式检查进入 CI。
- 核心数值代码必须有类型标注、单位和 shape 说明。
- 所有随机过程显式传入 seed；禁止全局隐式 seed。
- 关键数组必须标明 shape、dtype、单位、坐标和 abundance convention。
- 默认科学验证使用 float64；训练可 mixed precision，但最终物理验证必须 float64/高精度交叉检查。
- solver adapter 必须有固定物理点 regression tests。

### 6.3 实验登记

每次可引用实验创建：

```text
docs/experiment_cards/EXP-YYYYMMDD-NNN.md
manifests/runs/EXP-YYYYMMDD-NNN.json
```

至少记录：

- Git commit 与未提交改动状态；
- config、dataset、model hashes；
- solver/network/rate versions；
- observation dataset version；
- seed；
- 硬件；
- CPU-core-hours、GPU-hours、wall time、solver calls；
- 主要指标和预注册阈值；
- 失败、异常与 deviation；
- 是否允许用于论文和哪个 claim。

### 6.4 科学决策与偏离

- 主物理问题、数据、prior、函数型 rate 表示和 journal route 由 ADR 管理。
- 任何看到 production 结果后的更改必须进入 `deviation_log.md`。
- 探索性结果可自由生成，但必须标为 `EXPLORATORY`，不能与预注册检验混写。
- 多重假设检验必须报告试验族和校正策略。

### 6.5 Issue 标签

至少创建：

```text
physics
nuclear-data
solver
observations
preregistration
data
model
sbi
inference
validation
compute
literature
paper
nature-gate
blocker
```

---

## 7. 分阶段科研任务清单

### Phase 0 — 仓库、环境与最小复现

#### R0.1 初始化仓库骨架

- 创建第 4 节目录；
- 添加 README、LICENSE、CITATION、CHANGELOG、贡献规范；
- 配置 branch protection、CI 与 issue templates；
- 将现有代码全部迁入仓库，去除绝对路径和隐藏依赖。

**DoD**：仓库可安装；`make help`、`make smoke`、`make reproduce-mini` 可执行。

#### R0.2 环境锁定

- 固定 Python、JAX/PyTorch、NumPy/SciPy、sampler 与编译器版本；
- 写 AutoDL bootstrap；
- 分离 CPU solver 与 GPU train 环境；
- 记录 PArthENoPE、AlterBBN、LINX、PRyMordial 和 PRIMAT 依赖。

**DoD**：两台新实例的依赖解析和固定测试点结果一致。

#### R0.3 CI 与科学回归

- 单元测试；
- 小型 solver fixture；
- 固定参数点 abundance regression；
- rate `q=0, ±1` regression；
- 模型 forward/backward smoke；
- 10–100 step inference smoke；
- figure generation smoke。

**DoD**：未通过 CI 的 PR 不可合并。

---

### Phase 0.5 — 竞争边界、数据与旗舰路线预注册

#### L0.5.1 直接竞争者复现

至少完成：

- BBNet 最小复现；
- LINX 标准 BBN 与 `nuclear_rates_q` 示例；
- PRyMordial rate marginalization 示例；
- PRIMAT 或 LINX-PRIMAT 网络中心值比较；
- 2026 sensitivity atlas 的一个公开切片；
- 2026 GP D/H 的方法与先验结构笔记。

输出：`competitor_matrix.csv` 和可运行 baseline scripts。

#### L0.5.2 Why-not memo

创建 `ADR-WHY-NOT-001.md`，定量回答：

- direct solver 能否完成目标任务；
- 现有工具缺少哪些非标准物理、函数型 rate 或重复推断能力；
- emulator/新方法的总成本优势预期；
- 哪些任务若直接工具足够快，就不应开发新模型。

#### O0.5.3 观测数据冻结

- 建立 LBT、legacy helium、EMPRESS、D/H、Li、CMB/BAO、LVK 数据矩阵；
- 冻结主数据与替代数据；
- 记录 covariance、systematics 与获取日期；
- 主数据冻结必须发生在 Track B production 结果解盲之前。

#### N0.5.4 中子寿命冻结

- 定义 N0–N3；
- 记录 beam/bottle 与 J-PARC 现状；
- 决定主 baseline 与 robustness models。

#### J0.5.5 旗舰路线预登记

此阶段不选择最终期刊，只定义三个候选成功条件：

- `SUCCESS-NA-v1`；
- `SUCCESS-NCS-v1`；
- `SUCCESS-NMI-v1`。

**DoD**：所有 Track B blocker 有负责人、截止条件和输出文件。

---

### Phase 1 — 当前 BBNet 工作冻结与 Track A 交付

#### B1.1 导入并审计现有代码

- 将散落代码迁入仓库；
- 去除硬编码路径；
- 建立统一 config；
- 登记现有模型、数据和图来源；
- 检查训练数据泄漏与 normalization convention。

**DoD**：当前已报告结果可由单一命令重现。

#### B1.2 复现 deterministic emulator

至少报告：

- 相对与绝对误差；
- 以观测误差归一化的 emulator error；
- 1%、50%、95%、99.9% 分位；
- 参数空间热图；
- PArthENoPE 与 AlterBBN 分别结果；
- posterior shift；
- OOD 与失败率。

#### B1.3 hard/soft 十维后验比较

不得只比较 abundance。必须比较：

- 每个物理参数的 posterior median/credible interval；
- joint corner plot；
- sliced Wasserstein、energy distance 或 MMD；
- credible-region overlap；
- posterior predictive abundances；
- 被规则拒绝的 posterior mass；
- 归一化偏移 `Delta mu / sigma`。

#### B1.4 MCMC 收敛重做

- 至少 4 条独立链；
- 不以固定 20 万步定义收敛；
- split `R-hat < 1.01`；
- bulk/tail ESS 每个参数 `>1000`；
- MCSE `<0.02 * posterior_sd`；
- 报告 warmup、接受率、自相关、divergence；
- checkpoint/resume。

#### B1.5 `n_t`、`T_re` 与 `kappa`

至少运行：

- `n_t=-r/8`；
- `n_t` free；
- `T_re` 固定与自由的预定义组合；
- `kappa` 条件切片；
- full marginal posterior；
- profile likelihood、Fisher 与 information gain。

固定参数图只能说明条件响应，不得称为真实约束。

#### B1.6 Schramm-style 图与 Li 零检验

- `Omega_b h^2` 横轴标准图；
- `kappa` 或目标扩展参数横轴条件切片；
- 明确固定参数；
- 分开画 observational、nuclear、solver 和 emulator bands；
- Li 默认只做 null test。

#### B1.7 Track A 冻结

出口：

- 所有链收敛；
- 多 seed/初始化稳定；
- 图表可复现；
- draft 完整；
- code/data release candidate；
- 不再因 Track B 架构反复修改主结果。

---

### Phase 2 — Solver、rate registry 与函数型核不确定度

#### S2.1 Solver matrix

- 为 S0–S8 建立 adapter 或最小比较入口；
- 对中心值、温度演化和局部导数统一 convention；
- 至少在 20 个标准点和 20 个非标准点比较；
- 分解 network、rate source 和 numerical implementation。

#### R2.2 Rate registry

创建 `configs/rates/reaction_rates.yaml`，包含：

- rate ID 与反应式；
- solver 内部编号；
- 中心 rate 与 uncertainty 来源；
- `sigma(T)` 或 posterior samples；
- 相关矩阵/共享归一化；
- 影响元素；
- 是否 core、functional 或 stress-only；
- 数据与代码许可证。

#### R2.3 函数型 rate representation

对三个头部氘反应：

- 收集实验 S-factor 数据或公开 posterior；
- 实现 GP/KL 或 spline modes；
- 比较 normalization-only、shape modes 和 posterior draws；
- 测试 `K=1,2,3,5`；
- 对 basis 截断误差做验证；
- 记录 EFT/ab-initio 与实验先验差异。

#### S2.4 中心值与局部扰动回归

- `q=0`；
- 每个 core rate `q_i=±1,±2`；
- 每个 function mode `a_ik=±1`；
- 检查有限差分稳定性；
- 比较 LINX autodiff；
- 记录非线性与 solver failure 区域。

#### C2.5 性能与直接推断基准

对每个批准 solver 测量：

- 冷/热启动；
- batch 100/1000；
- 单/多进程；
- I/O 占比；
- 内存峰值；
- float32/float64；
- gradient cost；
- direct posterior 的 ESS/hour。

禁止在该基准前购买长期大规模算力。

---

### Phase 2.5 — Fisher / 线性传播 Gate

#### G2.5.1 响应矩阵

在至少 64、建议 128 个代表性 `theta` 点计算：

```text
J_q(theta)
J_a(theta)
J_theta(theta)
C_rate(theta)
C_shape(theta)
C_solver(theta)
```

覆盖标准 BBN、stiff-era、后验高密度区、边界、退化与 OOD 临界区。

#### G2.5.2 近似后验影响

估算：

- posterior center shift；
- interval change；
- degeneracy rotation；
- exclusion topology；
- scalar vs functional rate 差异；
- solver discrepancy floor；
- 目标参数的 rate value-of-information。

#### G2.5.3 Gate 规则

- `G0`：全部 `<0.1 sigma` 且 `<5%`，无拓扑变化 → 关闭 NA 发现路线；
- `G1`：`0.1–0.3 sigma` 或 `5–15%` → 定向 Pilot；
- `G2`：`>0.3 sigma`、`>15%`、明显非线性、rank inversion 或拓扑变化 → 完整推进；
- `G3`：跨 solver 定性变化或直接影响真实 GW/BBN 解释 → 最高优先级与外部 red-team。

小规模 Pilot-1k 可用于接口验证；未经 Gate 不得生成大于 Pilot-10k 的 Track B 数据。

---

### Phase 3 — Pilot、敏感性重排与主动设计

#### D3.1 Pilot-1k 与 Pilot-10k

顺序：

1. Pilot-1k：接口、失败率、局部非线性；
2. Gate 通过后 Pilot-10k；
3. `theta` 覆盖标准与非标准区域；
4. scalar rates 使用标准 prior；
5. functional modes 包含尾部 challenge；
6. 至少两个 solver/network；
7. 独立 block holdout。

#### D3.2 标准 BBN sensitivity atlas 复现

标准 BBN 排名只作为验证：

- 复现已知三个氘反应；
- 复现 `tau_n` 对 `Y_p` 的影响；
- 比较两套 rate compilation；
- 与 2026 sensitivity atlas 的公开结果定量对齐。

未通过则不得宣称非标准敏感性新发现。

#### D3.3 非标准膨胀下敏感性重排

至少比较：

- local derivatives；
- Sobol first/total；
- mutual information；
- Jacobian SVD/active subspace；
- posterior-weighted sensitivity；
- rank stability bootstrap。

报告：

- rank inversion；
- 有效维数随 `theta` 的变化；
- solver/network 稳健性；
- 哪些 rate 控制新物理而非标准 `Omega_b h^2`；
- 是否出现新的 rate–cosmology degeneracy。

#### D3.4 数据规模 learning curve

```text
1k -> 10k -> 30k -> 100k -> 200k -> 500k -> 1M（只在有证据时）
```

每档报告：点误差、NLL/CRPS、coverage、posterior recovery、OOD 和边际收益。

#### D3.5 主动学习

建议 acquisition：

```text
score = a * epistemic_uncertainty
      + b * posterior_relevance
      + c * boundary_and_tail_coverage
      + d * solver_disagreement
      + e * functional_mode_coverage
      + f * expected_information_gain
```

每轮新增样本必须由真实 solver 标注。记录被选择分布，必要时做 importance correction。

#### D3.6 数据切分

必须包含：

- IID test；
- 物理边界；
- 未见非标准切片；
- nuisance/function tail；
- solver-transfer；
- posterior-focused；
- adversarial/challenge；
- blind paper set。

---

### Phase 4 — Emulator、分布模型与方法路线

#### E4.1 显式 nuisance emulator

学习：

```text
f(theta, q, a, solver_id, network_id) -> y
```

作为最透明的联合采样基线。必须支持 derivatives 或至少稳定 finite differences。

#### E4.2 边缘分布 emulator

学习 `p(y | theta, solver/network)`，候选：

- conditional normalizing flow；
- mixture density network；
- residual neural likelihood；
- quantile/coupled copula；
- diffusion 仅在其他模型不能描述尾部时使用。

必须生成相关的 `Y_p`、D/H、Li/H 分布，而非独立误差棒。

#### E4.3 低秩与自适应有效维数

- `z = W(theta)^T [q,a]`；
- 比较固定 2/4/8/12 modes；
- 测试随 `theta` 自适应 mode basis；
- 检查被丢弃方向对 posterior 的影响；
- 对每个 mode 给出核反应组成和物理解释。

#### E4.4 多 solver discrepancy

比较：

- 每 solver 独立模型；
- solver ID 条件模型；
- shared trunk + solver heads；
- hierarchical discrepancy GP/process；
- Bayesian model averaging；
- conservative envelope。

不能将 solver 差异简单混为 aleatoric noise。

#### E4.5 Epistemic、OOD 与安全 fallback

至少比较：

- deep ensemble；
- latent/input distance；
- density score；
- conformal residual；
- physical boundary rules；
- cross-solver disagreement。

部署策略：

```text
safe in-domain -> emulator
uncertain / OOD -> high-fidelity solver
invalid physics -> reject with structured reason
```

#### E4.6 Route NCS/NMI 的跨问题验证

仅当选择 NCS/NMI 候选路线时必须执行：

- 至少 3 个标准 SBI/UQ benchmark；
- 至少 1 个非 BBN 真实科学模拟器，优先选择 stiff ODE、reaction network、recombination 或其他高维 nuisance 问题；
- 同一代码接口与评估指标；
- 与 SNPE/SNLE/NRE、active-learning 和 multi-fidelity 强基线比较；
- 报告 failure cases，不得只选有利任务。

---

### Phase 5 — 验证、校准与独立复现

#### V5.1 点预测验收

主 in-domain test：

- 99.9% 样本 emulator error `<0.1 * sigma_obs,total`；
- 最大误差目标 `<0.25 * sigma_obs,total`；
- posterior median 偏移 `<0.1 sigma`；
- 68%/95% 区间宽度变化 `<2%`，除非来自被建模的不确定度；
- functional-mode tail 与 boundary 单独报告。

#### V5.2 分布预测验收

报告：

- NLL；
- CRPS；
- energy score；
- 1D/2D coverage；
- PIT/rank；
- abundance covariance recovery；
- tail quantile error；
- calibration conditional on `theta`、solver 和 OOD distance。

目标：

- nominal 68% coverage 在 `[65%,71%]`；
- nominal 95% coverage 在 `[93%,97%]`；
- challenge set 单独报告。

#### V5.3 Simulation-Based Calibration

- 至少 1,000 replicates；
- 旗舰最终版本建议 2,000–5,000；
- rank histogram、z-score、coverage vs location；
- 多 seed variability；
- active-learning selection bias 检查；
- 直接与 emulator 两条路径抽查。

#### V5.4 直接 posterior recovery

在降维问题上运行 direct LINX/PRyMordial/批准 solver 参考后验，比较：

- marginal/joint posterior；
- energy/Wasserstein distance；
- evidence；
- posterior predictive；
- runtime、ESS 与总成本；
- scalar vs functional rate；
- solver/network 替换。

#### V5.5 OOD false-safe

核心安全指标：

- 危险 OOD 错判安全概率 `<10^-3`；
- fallback 不产生静默错误；
- OOD 规则不显著裁剪真实 posterior mass；
- challenge false-safe 有置信区间。

#### V5.6 独立重现

- 使用不同代码入口或不同成员；
- 从冻结 release 重建环境；
- 独立重跑至少一个主 posterior、一个主图和一个 sensitivity ranking；
- 对主 claim 给出 sign-off 或 fail report。

---

### Phase 6 — 完整宇宙学推断

#### I6.1 标准 BBN 复现

至少复现：

- `Omega_b h^2`；
- `N_eff`；
- core rate nuisance；
- 至少两套 rate network；
- LBT 与替代 `Y_p`；
- 主 D/H compilation；
- 已发表联合结果的合理区间。

未通过标准复现，不得进入扩展模型旗舰结论。

#### I6.2 扩展参数模型

schema 必须明确：

- 基础 cosmology；
- tensor/SGWB 参数；
- stiff/reheating 参数；
- 项目中的 `kappa`；
- scalar/function rate nuisance；
- neutron lifetime；
- solver discrepancy hyperparameters；
- model transition smoothness。

#### I6.3 数据组合

逐级运行：

1. BBN only；
2. BBN + CMB prior；
3. consistent BBN + CMB joint likelihood；
4. BBN + CMB + BAO；
5. BBN + SGWB integral bound；
6. BBN + CMB/BAO + LVK/PTA likelihood 或公开限制；
7. future ET/LISA/其他 forecast，单独标识。

#### I6.4 结果分解

每个结论报告：

- observational contribution；
- scalar nuclear rate；
- function shape；
- neutron lifetime；
- solver/network discrepancy；
- emulator approximation；
- prior/model assumption；
- data selection。

#### I6.5 模型比较

- 预注册 Bayes factor/likelihood ratio；
- 对 prior sensitivity 做 robustness；
- 报告 information gain；
- 避免将 Bayesian evidence 与 frequentist significance 混用；
- 若模型不可辨识，明确报告而非制造上限。

---

### Phase 7 — 旗舰物理发现任务

#### P7.1 非标准膨胀下 reaction-rank inversion

主问题：

> 反应率在标准 BBN 中的已知重要性，是否在 stiff/extra-radiation/reheating 区域发生可解释的重排？

输出：

- rank map over `theta`；
- effective dimension map；
- solver-stable modes；
- 物理冻结温度与反应窗口解释；
- 统计置信度与 bootstrap stability；
- 与标准 sensitivity atlas 的明确差异。

#### P7.2 核实验 value-of-information

计算：

- 某反应 uncertainty 缩小 2 倍/5 倍后目标参数改善；
- function-shape 某能区测量改善的后验收益；
- 哪个实验最能区分 rate compilation/solver；
- 哪个实验最能改变 GW/早期宇宙结论；
- 边际收益与实验目标精度曲线。

结果必须具体到反应、能区、精度目标和目标宇宙学参数。

#### P7.3 刚性时期、重加热与蓝倾 SGWB

核心输出：

- full-UQ exclusion/allowed region；
- 与 M0/M1/M2/M3/M5 的差异；
- 映射到 LVK/PTA/ET/LISA 频段；
- BBN integrated energy-density bound 的自洽传播；
- transition smoothness 与模型依赖；
- 当前真实数据与 future forecast 分离；
- 是否出现定性结论翻转。

#### P7.4 理论系统学下限

识别：

- 核数据 floor；
- neutron lifetime floor；
- solver/network floor；
- observational floor；
- emulator floor。

回答：下一代 `Y_p`、D/H、CMB 或 GW 数据到来后，哪个理论环节首先限制科学收益？

#### P7.5 D/H tension 与 rate representation

对比：

- PArthENoPE polynomial；
- PRIMAT/ab-initio；
- GP data-driven；
- EFT-informed；
- scalar vs functional uncertainty。

目标不是追求 tension，而是判断其对扩展宇宙学结论是否稳健。

#### P7.6 锂问题

- 不以解决 Li problem 为默认目标；
- 分离 BBN、恒星耗损、观测系统学和新物理；
- rate 扫描只做零检验；
- 若无可行区域，报告模型类和适用范围；
- 不用 Li 驱动主旗舰 claim，除非获得独立天体物理系统学模型支持。

---

### Phase 8 — 旗舰计算/机器学习发现任务

#### C8.1 端到端成本突破

必须证明至少一个任务从“不可实际执行”变为“可实际执行”：

- 1,000–5,000 次 SBC；
- 多 solver × 多数据 × 多 prior 系统扫描；
- 100+ nuisance 的重复联合推断；
- function-valued nuisance；
- 实时 solver fallback；
- 大规模实验 value-of-information 优化。

#### C8.2 通用框架

统一接口必须支持：

- expensive simulator；
- scalar/function nuisance；
- multiple fidelities/solvers；
- active learning；
- calibrated posterior；
- OOD fallback；
- cost ledger；
- reproducible benchmark。

#### M8.3 NMI 算法创新 Gate

只有满足以下之一才可继续 NMI：

- 新 nuisance-aware objective；
- 新 acquisition with calibration guarantee/analysis；
- 新 model-discrepancy marginalization；
- 新 function-valued nuisance representation；
- 新 safe amortized inference/fallback theory；
- 对 negative interference 的新机制解释与解决。

仅有架构组合、调参或 BBN 单应用不通过。

#### M8.4 跨任务 benchmark

至少：

- 3 个标准 SBI/UQ 任务；
- 1 个非 BBN 科学模拟器；
- 1 个 BBN flagship；
- 强基线、相同预算、公平超参；
- calibration、posterior bias、sample efficiency、OOD 与 total cost；
- 失败任务与适用条件。

---

### Phase 9 — Nature 路线 Go/No-Go 与投稿冻结

#### 9.1 所有旗舰路线共同基础条件

必须全部满足：

- 代码和主要数据可公开；
- 至少两个独立 solver/network；
- scalar 与 functional rate 比较；
- convergence、SBC、coverage、OOD 验证；
- 主结论跨至少 5 个训练 seed；
- 主结论跨关键 abundance 数据选择；
- neutron lifetime robustness；
- emulator bias 远小于总误差；
- 结果不由 prior boundary、固定参数或单一 solver 驱动；
- 主统计量在解盲前冻结；
- direct solver spot-check/recovery；
- external or independent red-team；
- claim–evidence matrix 完整。

#### 9.2 Route NA Gate

至少满足两项，其中一项必须是物理结论：

- 后验偏移 `>=0.5 sigma` 且跨 solver/data 稳健；
- 约束宽度或允许体积改变 factor `>=1.5`，并改变物理解释；
- 一个活跃的 early-Universe/GW 模型区域发生定性允许/排除变化；
- 发现可被核实验或真实/近期 GW 观测直接检验的新关系；
- 识别新的理论 systematics floor，改变未来观测优先级；
- 结果对 BBN、GW、早期宇宙至少两个社区具有直接意义。

标题和摘要必须在不提 AI 模型名时仍然成立。

#### 9.3 Route NCS Gate

必须全部满足：

- 通用计算问题清晰；
- 端到端成本改善显著，目标为数量级或足以解锁新任务；
- 在相同 calibration/posterior bias 下比较；
- 至少一个非 BBN 科学验证或强通用性证明；
- 开放 benchmark、软件、数据规范与 scaling study；
- 产生新的科学洞见，而非纯工程速度。

#### 9.4 Route NMI Gate

必须全部满足：

- 真正新的 ML 方法或原理；
- 理论、机制或严格实验分析；
- 多 benchmark、多领域强基线胜出；
- OOD、calibration、安全与 failure modes 完整；
- BBN 应用产生高质量科学结果；
- 方法对 SBI/ML 社区具有独立价值。

#### 9.5 Route NC Gate

至少满足：

- 完整 rate + solver + observation UQ；
- 对专业领域形成重要推进；
- 结果明显超越现有工具或公开分析；
- 开放、可复现、独立验证；
- 未达到 NA/NCS/NMI 广度的原因被诚实说明。

#### 9.6 No-Go 输出

若未通过任何 Nature Gate：

- Track A 正常投稿；
- Track B 转为 PRD/JCAP/Communications Physics 或方法资源论文；
- 报告稳健性边界、负结果、开放工具或未来实验需求；
- 不通过包装更换期刊叙事。

---
