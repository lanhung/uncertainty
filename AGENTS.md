# AGENTS.md — `lanhung/uncertainty` 科研执行总章程

> 版本：0.1.0  
> 基准日期：2026-07-21  
> 项目代号：**BBNet-UQ / Uncertainty-aware Big-Bang Nucleosynthesis Inference**  
> 主仓库：`https://github.com/lanhung/uncertainty`  
> 默认分支：`main`

本文件是本项目所有人类成员、代码代理、科研代理与自动化任务的最高级执行规范。任何实现、实验、图表、结论和论文文字都必须能追溯到本文件中的任务编号、配置、数据版本和代码提交。

---

## 0. 项目使命、论文目标与现实定位

### 0.1 总使命

建立一个端到端、可验证、可复现的 BBN 不确定度推断系统，将：

1. 非标准早期宇宙参数 `theta`；
2. 核反应率和中子寿命等 nuisance parameters `q`；
3. BBN solver 的模型差异；
4. 神经网络 emulator 的近似误差；
5. 天文观测误差；

统一传播到轻元素丰度、宇宙学参数后验和随机引力波背景/刚性时期等物理结论中。

### 0.2 两条并行论文线

#### Track A — 稳健交付线（现实目标：PRD / JCAP）

完成并冻结当前 BBNet 相关工作：

- 确定性 emulator 的复现；
- hard/soft 外推定义的严格比较；
- 十维物理参数后验比较，而不是只比较丰度输出；
- 多链收敛、后验预测检验；
- `n_t` 自由与 inflationary consistency relation 两种情形；
- `kappa`、`n_t`、`T_re` 的可辨识性分析；
- Schramm-style 物理切片图；
- 可审计代码、数据清单和复现实验。

Track A 不得因 Track B 的高风险探索而延误。

#### Track B — 高影响力发现线（目标候选：PRL / Nature Astronomy / Nature Communications / Communications Physics）

只有在出现下列至少一种结果时，才进入高影响力投稿：

- 完整核反应率边缘化使某个非标准早期宇宙参数的约束或证据发生统计显著改变；
- 传统常数理论误差或固定中心反应率方法在扩展宇宙学中产生可量化偏差，并改变已有物理结论；
- 识别出跨 solver 稳健、物理可解释的少数核反应率主模态，并给出明确的核实验优先级；
- 联合 BBN、CMB、SGWB/PTA/LIGO/未来探测器后，首次稳健排除或支持一类刚性时期/蓝倾张量谱模型；
- 发现 solver/network discrepancy 足以影响当前精密宇宙学结论，并给出经过验证的解决方案。

仅有“网络更快”“网络层更多”“输入维度从 10 变成 110”“使用 GAN/NF/Transformer”不构成高影响力物理发现。

### 0.3 不可承诺事项

- 不承诺一定获得 PRL 或 Nature 子刊接收。
- 不在没有统计证据时使用“发现”“解决锂问题”“排除整个模型”等措辞。
- 不把模型训练成功等同于物理结论成立。
- 不以期刊目标倒推或选择性报告结果。

---

## 1. 科学问题、假设与可证伪标准

### 1.1 变量定义

- `theta`：关心的宇宙学/早期宇宙参数。最终列表必须由 `configs/physics/parameter_schema.yaml` 唯一确定。
- `q_i`：第 `i` 个核反应率 nuisance parameter，标准约定为 `q_i ~ Normal(0, 1)`。
- `tau_n`：中子寿命 nuisance parameter。
- `s`：solver/network 标识，例如 PArthENoPE、AlterBBN、LINX/PRIMAT-compatible network。
- `y`：轻元素丰度向量，至少包括 `Y_p` 和 `D/H`；`Li/H` 只能作为独立敏感性/零检验，除非观测系统学被显式建模。
- `x_obs`：天文观测数据。

核反应率的默认统计形式为：

```text
log r_i(T) = log rbar_i(T) + q_i * sigma_i(T)
```

任何偏离该形式的 rate prior 必须注明物理来源、相关结构和温度依赖。

### 1.2 核心科学假设

- **H1 — 分布学习假设**：条件模型能够在给定 `theta` 时准确复现由 `q` 引起的 `p(y | theta)`，而不仅是丰度均值。
- **H2 — 低维主模态假设**：影响 `Y_p`、`D/H` 和扩展宇宙学后验的有效核反应率方向远少于原始 rate 数量。
- **H3 — 非恒定理论误差假设**：`sigma_th` 随 `theta` 显著变化，固定常数误差在扩展参数空间会造成后验偏差或信息损失。
- **H4 — 物理影响假设**：完整边缘化会对至少一个扩展参数（例如刚性时期、蓝倾张量谱、重加热相关参数或项目中的 `kappa`）产生不可忽略的约束变化。
- **H5 — 跨 solver 稳健性假设**：在匹配反应网络与输入物理后，主要物理结论在至少两个独立 solver 上保持稳定；剩余差异可以被 model discrepancy 描述。

### 1.3 零假设与停止条件

- **N1**：完整边缘化与常数 `sigma_th` 对最终后验影响小于 `0.1` 个后验标准差。
- **N2**：核反应率不确定度远小于观测系统学或 solver discrepancy，无法改变目标物理结论。
- **N3**：`kappa` 在允许 `n_t`、`T_re` 等主导参数自由变化后不可辨识，后验主要由 prior 决定。
- **N4**：所谓高影响力信号不跨 solver、数据集或 prior 稳健。

若 N1–N4 成立，应停止“发现”叙事，转为方法学/稳健性论文，不得通过固定参数制造显著性。

---

## 2. 文献边界与创新红线

### 2.1 已被覆盖的工作

以下内容不得单独宣称为首创：

- 使用神经网络高速预测 BBN 丰度；
- 使用 PArthENoPE 与 AlterBBN 生成 BBNet 训练数据；
- 使用 JAX 可微 BBN solver；
- 在标准 BBN/CMB 分析中将关键核反应率作为 nuisance parameters 并联合边缘化；
- 仅证明核反应率不确定度不是常数；
- 仅使用 normalizing flow 做快速后验采样；
- 仅做约 100 维输入的神经网络回归。

### 2.2 推荐创新组合

优先级从高到低：

1. **非标准早期宇宙 + 完整核不确定度 + 多数据联合推断 + 新物理结论**；
2. **可解释核反应率主模态 + 核实验优先级 + 扩展宇宙学影响**；
3. **多 solver 分层贝叶斯模型 + solver discrepancy + 后验稳健性**；
4. **主动学习驱动的高保真 solver 采样 + 严格 coverage + 开放基准数据集**；
5. 仅方法加速，但必须明显超越直接使用 LINX/PRyMordial 的成本与能力。

### 2.3 审稿人必问问题

每个里程碑都必须准备回答：

- 为什么不能直接使用 LINX？
- 为什么不能只显式采样 12 个关键反应？
- 神经网络节省的是哪一部分成本，数据生成成本是否被隐藏？
- emulator error 与 nuclear-rate uncertainty 是否混淆？
- rate prior 是否具有温度相关性和跨反应相关性？
- 结论是否依赖某一个 solver/network？
- 结论是否依赖某一个 abundance 数据选择？
- `Li/H` 是否被恒星耗损等系统学主导？
- 固定参数后的 `kappa` 效应是否只是条件切片，而非可推断约束？
- posterior 是否通过 simulation-based calibration 和 coverage 检验？
- 高影响力结论是否在盲化前定义了阈值？

---

## 3. 推断层级与必须比较的基线

所有核心物理结果必须同时报告以下模型：

- **M0 — Central-rate baseline**：固定所有核反应率在中心值。
- **M1 — Constant-theory-error baseline**：在 likelihood 中加入常数 `sigma_th`。
- **M2 — Full rate marginalization**：联合或显式边缘化关键 `q_i` 与 `tau_n`。
- **M3 — Conditional distribution emulator**：直接学习 `p(y | theta)`，将 `q` 边缘化于模拟分布中。
- **M4 — Multi-solver discrepancy model**：加入 solver/network 层级变量或 discrepancy term。

论文中的任何“改进”必须明确相对于哪一个基线。

---

## 4. 仓库结构与所有权

目标结构：

```text
uncertainty/
├── AGENTS.md
├── README.md
├── LICENSE
├── CITATION.cff
├── pyproject.toml
├── uv.lock                      # 或 conda-lock；只能保留一种主锁定方案
├── Makefile
├── .pre-commit-config.yaml
├── .github/
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── configs/
│   ├── physics/
│   ├── solver/
│   ├── data/
│   ├── model/
│   ├── inference/
│   └── autodl/
├── src/uncertainty/
│   ├── physics/
│   ├── solvers/
│   ├── rates/
│   ├── data/
│   ├── models/
│   ├── inference/
│   ├── diagnostics/
│   ├── plotting/
│   └── cli/
├── external/                    # 仅 submodule/patch/安装脚本，不复制无来源代码
├── scripts/
│   ├── bootstrap/
│   ├── data_generation/
│   ├── training/
│   ├── inference/
│   ├── validation/
│   └── release/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── scientific/
├── notebooks/                  # 只做探索，不作为最终生产入口
├── docs/
│   ├── decisions/
│   ├── literature/
│   ├── experiment_cards/
│   ├── dataset_cards/
│   ├── compute/
│   └── paper/
├── artifacts/                  # 仅小型、可审计结果；大文件不直接进 Git
├── manifests/
│   ├── datasets/
│   ├── models/
│   └── runs/
└── paper/
    ├── track_a/
    └── track_b/
```

### 4.1 大文件规则

- 代码、配置、数据生成器、校验和、数据清单必须进入 GitHub。
- 原始大数据不得直接提交普通 Git 历史。
- 大数据使用 DVC/对象存储/Zenodo；仓库中保留 checksum、schema、生成命令和 DOI。
- 最终模型权重通过 GitHub Release 或 Zenodo 发布，并在 `manifests/models/` 记录 SHA256。
- 任何结果图必须能由仓库命令从已登记数据重新生成。

---

## 5. 代理角色、权限与交付物

### A00 — Science Lead / PI Agent

职责：

- 冻结物理问题、参数定义、prior 和数据组合；
- 判断条件切片与真正边缘化约束的区别；
- 审核所有物理措辞；
- 维护 `docs/decisions/ADR-physics-*.md`；
- 主持高影响力 go/no-go gate。

禁止：

- 在看到结果后更换主检验而不登记；
- 通过固定退化参数制造显著性；
- 把 emulator 精度指标当成物理发现。

完成标准：每个主结论都有预先登记的统计量、阈值、替代解释和稳健性检验。

### A01 — Repository & Reproducibility Agent

职责：

- 初始化目录、依赖锁、CI、pre-commit、版本信息；
- 建立一键复现实验入口；
- 保证从空环境执行 `make smoke` 成功；
- 记录操作系统、CUDA、驱动、编译器、solver commit。

完成标准：全新 AutoDL 实例 30 分钟内完成环境恢复和 smoke test；不依赖手工修改隐藏文件。

### A02 — BBN Solver Agent

职责：

- 为 PArthENoPE、AlterBBN、LINX/其他批准 solver 建立统一 adapter；
- 统一输入参数、单位、核反应率扰动接口和输出 schema；
- 隔离 solver I/O，避免每样本启动进程和文本写盘；
- 建立中心值、单反应扰动、批量运行和失败恢复测试；
- 保存上游版本、补丁和许可证信息。

完成标准：同一参数点可在每个 solver 上重复得到确定性结果；失败样本有结构化错误码；无静默 NaN。

### A03 — Nuclear Uncertainty Agent

职责：

- 建立 `rate_id -> physical reaction -> prior -> temperature dependence -> source` 注册表；
- 区分中心值差异、实验 rate uncertainty、network choice 与 solver numerical error；
- 支持独立高斯、相关高斯、经验后验样本三种 prior；
- 计算 local sensitivity、Sobol/MI、Jacobian SVD/active subspace；
- 给出 12-rate 核心集和 full-network stress set。

完成标准：每一个进入推断的 rate 参数都有来源、单位、温度网格、先验和敏感性证据。

### A04 — Dataset Agent

职责：

- 生成 pilot、production、validation 和 challenge 数据；
- 采用可复现的 Sobol/LHS/先验采样和主动学习策略；
- 将物理边界、退化区、后验高密度区与 OOD 区分开；
- 生成 dataset card、checksum、失败率、覆盖图与运行成本。

禁止：

- 将 GAN/NF 生成的未经过 solver 计算的样本当作物理真值；
- 仅随机拆分相邻样本导致数据泄漏；
- 删除失败样本而不分析失败机制。

完成标准：每条 label 均来自批准的真实 solver；所有样本可由 seed 与 config 重建。

### A05 — Emulator Agent

必须实现并比较：

1. 确定性基线 `f(theta, q) -> y`；
2. 条件概率模型 `p(y | theta)`；
3. 低秩核反应率 latent-mode 模型；
4. 深度 ensemble 或其他 epistemic uncertainty 基线；
5. 简单高斯/多项式/Gaussian Process 基线，在可行子空间内比较。

禁止：

- 以模型参数量作为科学优越性证据；
- 将每个 nuisance parameter 错误地映射为一个 flow layer；
- 只报告平均 MSE；
- 在测试集上调超参数。

完成标准：达到第 10 节验收阈值，并在至少 5 个独立训练 seed 上稳定。

### A06 — SBI / Active Learning Agent

职责：

- 评估 NLE/NPE/NRE、conditional flow、diffusion/mixture density 等路线；
- 优先使用能自动边缘化 nuisance parameters 的模拟设计；
- 主动学习 acquisition 同时考虑 posterior relevance、预测不确定度、边界覆盖和 nuisance coverage；
- 对模拟预算做 learning curve，而非先生成 100 万点再评估。

完成标准：相对固定设计，在相同 solver 调用数下显著降低分布误差，且不牺牲 coverage。

### A07 — Bayesian Inference Agent

职责：

- 实现 M0–M4 likelihood；
- 支持多链 MCMC、nested sampling，以及可行时的 HMC/NUTS；
- 统一先验、参数变换、evidence 与后验导出格式；
- 对 emulator posterior 与 direct-solver/LINX posterior 做 recovery；
- 输出后验样本而不仅是 corner plot。

完成标准：所有报告参数满足收敛与 MCSE 阈值；重复运行可重现；evidence 误差被报告。

### A08 — Validation & Red-Team Agent

职责：

- 独立维护不可供训练使用的 challenge set；
- 执行 SBC、coverage、posterior predictive checks、OOD false-safe 检验；
- 运行 prior、数据、solver、网络、seed 和数值精度稳健性分析；
- 主动寻找能推翻主结论的反例。

完成标准：验证代码与模型开发代码解耦；最终结果需由该代理签署 `VALIDATION_PASS.md`。

### A09 — AutoDL / Compute Agent

职责：

- 维护实例镜像、机器清单、任务队列、成本与失败日志；
- 数据生成优先按 CPU 吞吐选机，训练按 GPU/显存选机；
- 每个长任务支持 checkpoint、resume 和自动关机；
- 每日至少一次将 manifests/checkpoints 同步到可靠存储。

完成标准：单台实例故障不导致不可恢复的数据或超过 24 小时的科研损失。

### A10 — Paper & Release Agent

职责：

- 建立 claim-evidence matrix；
- 每个图对应生成脚本、config、commit、dataset hash；
- 维护 Track A/Track B 两套摘要与目标期刊论证；
- 准备数据可用性、代码可用性、计算资源与限制声明。

完成标准：论文中每个数值和图均可追溯；公开 release 可独立复现主结论。

---

## 6. GitHub 工作流

### 6.1 分支与提交

- 初始 bootstrap 后禁止直接推送 `main`。
- 分支命名：
  - `feat/TASK-ID-short-name`
  - `fix/TASK-ID-short-name`
  - `exp/TASK-ID-short-name`
  - `paper/TASK-ID-short-name`
- 使用 Conventional Commits。
- 每个 PR 只解决一个任务或一个紧密耦合的任务组。
- PR 必须列出：目的、物理假设、配置、测试、数据影响、资源影响、风险、复现命令。

### 6.2 代码质量

- Python 主版本统一为 3.11，除非 solver 强制要求其他版本；例外需 ADR。
- `ruff`、`mypy/pyright`、`pytest`、格式检查必须进入 CI。
- 核心数值代码必须有类型标注和单位说明。
- 所有随机过程显式传入 seed；禁止依赖全局隐式 seed。
- 关键数组必须标明 shape、dtype、单位和坐标顺序。
- 默认科学计算使用 float64；训练可使用 mixed precision，但最终物理验证必须 float64/高精度交叉检查。

### 6.3 实验登记

每次可引用实验创建：

```text
docs/experiment_cards/EXP-YYYYMMDD-NNN.md
manifests/runs/EXP-YYYYMMDD-NNN.json
```

最少记录：

- Git commit；
- 未提交改动状态；
- config hashes；
- 数据集 hashes；
- solver versions；
- seed；
- 硬件；
- wall time / GPU-hours / CPU-core-hours；
- 主要指标；
- 失败与异常；
- 是否允许用于论文。

---

## 7. 分阶段科研任务清单

## Phase 0 — 仓库与环境引导

### R0.1 初始化仓库骨架

- 创建第 4 节目录；
- 添加 README、LICENSE、CITATION、贡献规范；
- 配置 branch protection；
- 建立任务 labels：`physics`、`solver`、`data`、`model`、`inference`、`validation`、`compute`、`paper`、`blocker`。

**DoD**：空仓库变成可安装 Python 包；`make help` 和 `make smoke` 可执行。

### R0.2 环境锁定

- 固定 Python、JAX/PyTorch、NumPy/SciPy、sampler、编译器版本；
- 写 AutoDL bootstrap 脚本；
- 分离 CPU solver 环境与 GPU train 环境，必要时用两个 lock 文件。

**DoD**：两台新实例的依赖解析结果一致。

### R0.3 CI 与科学回归测试

- 单元测试；
- 小型 solver fixture；
- 固定参数点的 abundance regression；
- 模型 forward/backward smoke；
- 10–100 step inference smoke。

**DoD**：PR 未通过 CI 不可合并。

---

## Phase 1 — 当前 BBNet 工作冻结与 Track A 交付

### B1.1 导入并审计现有代码

- 将散落代码迁入仓库；
- 去除硬编码绝对路径；
- 建立统一 config；
- 记录现有模型、数据和图的来源。

**DoD**：当前已报告的 BBNet 结果可由单一命令重现。

### B1.2 复现 deterministic emulator 指标

至少报告：

- 相对误差与绝对误差；
- 以观测误差归一化的 emulator error；
- 1%、50%、95%、99.9% 分位；
- 参数空间热图；
- PArthENoPE 与 AlterBBN 分别结果；
- 推断后验偏移。

### B1.3 hard/soft 外推策略的十维后验比较

不得只比较丰度输出分布。必须比较：

- 每个物理参数的 posterior median/credible interval；
- joint corner/triangle plot；
- sliced Wasserstein / energy distance / MMD；
- 后验重叠与 credible-region overlap；
- posterior predictive abundance；
- 被 hard/soft 规则拒绝的样本位置。

**DoD**：结论同时满足统计距离和物理参数偏移阈值。

### B1.4 重做 MCMC 收敛

- 至少 4 条独立链；
- 不以固定 20 万步作为收敛定义；
- split `R-hat < 1.01`；
- bulk ESS 与 tail ESS 每个报告参数均 `> 1000`；
- MCSE `< 0.02 * posterior_sd`；
- 报告 warmup、autocorrelation、接受率、divergence；
- checkpoint 可续跑。

### B1.5 `n_t` 一致性关系与自由模型

至少运行：

- `n_t = -r/8`；
- `n_t` 自由；
- 其他基础参数固定/自由的预先定义组合；
- `kappa` 条件切片与全边缘化后验；
- identifiability/Fisher/profile likelihood。

**规则**：固定参数图只能说明条件响应，不能直接称为观测约束。

### B1.6 Schramm-style 图与锂零检验

- 以 `Omega_b h^2` 为横轴的标准图；
- 以 `kappa` 或目标扩展参数为横轴的条件切片；
- 明确固定参数；
- 叠加观测带、nuclear uncertainty band、solver discrepancy band；
- Li 只作为 null test，主结论优先依赖 D/H 与 `Y_p`。

### B1.7 Track A 冻结

**出口标准**：

- 所有链收敛；
- 结果在至少两个 seed/初始化方案稳定；
- 图表可复现；
- 写出完整 draft；
- 不再因 Track B 架构实验反复修改 Track A 主结果。

---

## Phase 2 — 核反应率不确定度接口

### U2.1 统一 solver adapter

接口建议：

```python
simulate(theta, q, solver_id, network_id, precision, seed) -> AbundanceRecord
```

输出必须含：

- abundances；
- solver status；
- runtime；
- input hash；
- solver/network/version；
- numerical warnings；
- optional trajectories。

### U2.2 rate registry

创建 `configs/physics/reaction_rates.yaml`：

- rate ID；
- 反应式；
- solver 内部编号；
- 中心 rate 来源；
- uncertainty 来源；
- `sigma(T)`；
- 相关矩阵/共享归一化误差；
- 影响元素；
- 是否进入 core-12；
- 是否进入 full stress test。

### U2.3 中心值与单反应扰动回归

- `q_i = 0` 回归；
- 每个 core rate 的 `q_i = ±1, ±2`；
- 检查单调性只作为诊断，不强制所有物理响应单调；
- 比较 solver 对同一物理 rate 的映射。

### U2.4 性能基准

对每个 solver 测量：

- 冷启动；
- 热启动；
- 批量 100/1000 点；
- 单进程与多进程；
- I/O 占比；
- 内存峰值；
- 失败率。

禁止在未完成此基准前购买长期大规模算力。

---

## Phase 3 — 数据设计与敏感性降维

### D3.1 Pilot-10k

生成 10,000 个真实 solver 样本：

- `theta` 覆盖训练 prior；
- core-12 `q` 使用标准高斯；
- 包括 `±2σ/±3σ` tail challenge；
- 至少两个 solver/network；
- 独立的 block holdout。

### D3.2 敏感性分析

至少比较：

- finite-difference Jacobian；
- automatic differentiation（LINX 可行时）；
- Sobol first/total indices；
- mutual information；
- Jacobian SVD / active subspace；
- posterior-weighted sensitivity。

输出：

- 每个丰度的关键 rates；
- 每个目标宇宙学参数后验的关键 rates；
- 低维 latent mode 数量与解释方差；
- 核实验优先级候选。

### D3.3 数据规模 learning curve

依次训练：

```text
10k -> 30k -> 100k -> 200k -> 500k -> 1M（仅在有证据时）
```

每档报告误差、coverage、posterior recovery 与新增 solver 调用的边际收益。

### D3.4 主动学习

每轮 acquisition 由四部分组成：

```text
score = a * epistemic_uncertainty
      + b * posterior_relevance
      + c * boundary_or_tail_coverage
      + d * solver_disagreement
```

每轮新增样本必须由真实 solver 标注。

### D3.5 数据切分

必须包含：

- IID test；
- 边界 test；
- 未见物理切片 test；
- nuisance tail test；
- solver-transfer test；
- posterior-focused test；
- adversarial/challenge test。

随机行切分不能作为唯一测试。

---

## Phase 4 — Emulator 与分布模型

### E4.1 确定性显式 nuisance emulator

学习 `f(theta, q) -> y`，作为可解释和直接联合采样基线。

### E4.2 边缘分布 emulator

学习 `p(y | theta)`，候选：

- conditional normalizing flow；
- mixture density network；
- conditional diffusion（仅在 flow 不足时）；
- quantile model。

必须能够生成 correlated `Y_p`、`D/H`、`Li/H` 样本，而不是独立输出边际误差条。

### E4.3 低秩 latent-mode 模型

- 从 sensitivity/Jacobian 得到 `z = W^T q`；
- 比较 2、4、8、12 维 latent modes；
- 检查被丢弃方向对 posterior 的影响；
- 报告每个 mode 的主要核反应组成。

### E4.4 Epistemic uncertainty 与 OOD

至少比较：

- deep ensemble；
- input/latent distance；
- density score；
- conformal residual 或 calibration layer；
- 物理边界规则。

部署策略必须是：

```text
safe in-domain -> emulator
uncertain / OOD -> solver fallback
invalid physics -> reject with reason
```

### E4.5 多 solver 建模

比较：

- 每 solver 独立模型；
- solver ID 条件模型；
- hierarchical shared trunk + solver heads；
- discrepancy correction。

不能把 solver 差异简单混为 aleatoric noise。

---

## Phase 5 — 验证与统计校准

### V5.1 点预测验收

在主 in-domain test 上：

- 99.9% 样本的 emulator 误差 `< 0.1 * sigma_total_observational`；
- 最大误差目标 `< 0.25 * sigma_total_observational`；
- 推断后验 median 偏移 `< 0.1` posterior sigma；
- 68%/95% 区间宽度变化 `< 2%`，除非差异来自所建模的核不确定度。

若达不到，扩大数据或缩小有效域，不得只报告平均值。

### V5.2 分布预测验收

报告：

- NLL；
- CRPS；
- energy score；
- 1D/2D coverage；
- probability integral transform；
- abundance covariance recovery；
- tail quantile error。

目标 coverage：

- nominal 68% 的经验 coverage 在 `[65%, 71%]`；
- nominal 95% 在 `[93%, 97%]`；
- challenge set 单独报告，不允许被总体平均掩盖。

### V5.3 Simulation-Based Calibration

- 至少 1,000 个 SBC replicates；
- 参数 rank histogram；
- posterior z-score；
- coverage vs parameter location；
- 训练 seed 间 variability。

### V5.4 直接 solver 后验恢复

在降维问题上运行 direct solver/LINX 参考后验；比较：

- marginal posterior；
- joint distances；
- evidence；
- posterior predictive；
- runtime 和有效样本数。

### V5.5 OOD false-safe

主安全指标不是 AUROC，而是：

- 将危险 OOD 错判为安全的概率 `< 10^-3`；
- OOD 样本经 fallback 后不产生静默错误；
- 外推规则不显著裁剪真实 posterior mass。

---

## Phase 6 — 完整宇宙学推断

### I6.1 标准 BBN 复现

先复现公开标准结果：

- `Omega_b h^2`；
- `N_eff`；
- core reaction nuisance parameters；
- 至少两个 rate network。

未通过标准复现，不得进入扩展模型结论。

### I6.2 扩展参数模型

参数 schema 必须明确：

- 基础 cosmology；
- tensor/SGWB 参数；
- stiff/reheating 参数；
- 项目中的 `kappa`；
- 反应率 nuisance；
- neutron lifetime；
- solver discrepancy hyperparameters。

所有参数需登记 prior、变换、单位、物理边界和数据敏感性。

### I6.3 数据组合

逐级运行：

1. BBN only；
2. BBN + CMB prior；
3. consistent joint BBN + CMB；
4. BBN + SGWB integral bound；
5. BBN + PTA/LIGO/其他实际可用 likelihood；
6. future detector forecasts 与真实数据分析分开。

### I6.4 结果分解

每个物理结论报告：

- 观测数据贡献；
- 核 rate uncertainty 贡献；
- solver discrepancy 贡献；
- emulator approximation 贡献；
- prior contribution；
- model assumption contribution。

---

## Phase 7 — 高影响力物理问题

### P7.1 `kappa` 可辨识性

- 条件响应；
- profile likelihood；
- full marginal posterior；
- `n_t`/`T_re` 退化；
- consistency relation vs free `n_t`；
- prior-to-posterior information gain。

若 information gain 接近零，结论应为“当前数据不可辨识”，不得称为精确约束。

### P7.2 刚性时期与蓝倾张量谱

核心问题：在完整核不确定度与 solver discrepancy 下，BBN 对刚性时期、重加热温度、张量谱和 SGWB 的限制是否改变？

输出：

- rate-marginalized exclusion region；
- 与 fixed-rate/constant-error 的差异；
- 与 PTA/LIGO/未来 ET/LISA 频段的映射；
- BBN energy-density bound 的自洽传播；
- model dependence 与 transition smoothness。

### P7.3 核反应率主模态与实验优先级

目标不是只给 sensitivity ranking，而是计算：

- 若某 rate uncertainty 缩小 2 倍/5 倍，目标宇宙学参数后验改善多少；
- 哪个实验最能区分 solver/network；
- 哪组 rates 控制非标准宇宙学而非标准 `Omega_b h^2`；
- value-of-information 排名。

### P7.4 锂问题

- 不以“通过调 rate 解决锂问题”为默认假设；
- 分离 BBN 产生量、恒星耗损、观测系统学和新物理；
- 核 rate 扫描只做零检验；
- 如无可行区域，明确报告排除范围和适用模型类。

---

## Phase 8 — 高影响力 Go/No-Go Gate

只有满足以下全部基础条件和至少一项科学条件，才准备 PRL/Nature 子刊版本。

### 基础条件

- 代码和主要数据可公开；
- 至少两个 solver/network；
- 完整 convergence、SBC、coverage、OOD 验证；
- 主结论跨 5 个训练 seed；
- 主结论跨关键 abundance 数据选择；
- emulator bias 远小于总误差；
- 结果不是由 prior 边界或固定参数驱动；
- 盲化前已定义主统计量。

### 科学条件（至少一项）

- 新参数偏移或 exclusion 变化 `>= 0.5 sigma` 且具有物理解释；
- 约束宽度改善/恶化达到 factor `>= 1.5–2`，并改变文献结论；
- Bayes factor 达到预登记的强证据阈值，且跨 solver 稳健；
- 排除一个此前可行、具有广泛兴趣的模型区域；
- 发现可被未来核实验或 GW 探测明确检验的新关系；
- 方法对一个广泛类别的科学推断有显著影响，而不只是本项目单一模型。

### No-Go 输出

若未满足，目标期刊调整为 PRD/JCAP/Communications Physics，并将结果表述为：

- 稳健性边界；
- 方法与开放工具；
- 负结果；
- 对未来实验的需求。

---

## 8. AutoDL 资源计划

## 8.1 现在立即启用的稳妥配置

推荐同时保有 **3 台实例、每台 1 张 GPU，共 3 张卡**：

### Node A — `uq-data-01`

- 1 × RTX 4090 24GB；
- 16–32 vCPU；
- 64–128GB RAM；
- 200GB 以上本地 SSD；
- 用途：solver 编译、批量数据生成、rate sensitivity、CPU 多进程。

说明：该节点的主要瓶颈是 CPU/RAM，不是 GPU。选主机时优先看每卡分配的 CPU 和内存。

### Node B — `uq-train-01`

- 1 × RTX 4090 24GB；
- 8–16 vCPU；
- 64GB RAM；
- 200GB 本地 SSD；
- 用途：BBNet、conditional flow、ensemble、active-learning surrogate。

### Node C — `uq-validate-01`

- 1 × RTX 4090 24GB；
- 16 vCPU 以上；
- 64GB RAM；
- 用途：独立 MCMC/nested sampling、SBC、challenge set、复现实验。

**明确结论**：现阶段不建议一开始租 8 卡机，也不建议把模型训练做成复杂多卡分布式。当前模型规模小，数据生成和统计验证比单次训练更可能成为瓶颈；4090 多卡通信也不是最佳选择。

## 8.2 预算受限的最低配置

- 2 台实例；
- 2 × 4090；
- 一台 data+validation，一台 training；
- 缺点：solver 生产与独立验证会互相抢资源，失败恢复慢。

不建议长期只用 1 台，因为会失去独立复现节点且数据生成、训练、推断互相阻塞。

## 8.3 峰值扩展

当 Pilot-10k 证明模型和数据设计有效后，可临时增加：

- 2–3 台单卡 4090 数据节点；
- 峰值总计 4–6 台机器 / 4–6 张卡；
- 主要用于并行 solver shard 和多 seed 训练；
- 任务完成立即关机/释放。

## 8.4 A100 使用条件

只在以下情况租 1 张 A100 40/80GB：

- JAX/LINX 的 float64、HMC/NUTS 或大批量可微推断显著受 4090 FP64 限制；
- 单模型/批量确实超过 24GB 显存；
- 已有 profiling 证明 A100 可将总成本降低。

A100 应作为阶段性验证节点，而不是默认长期节点。

## 8.5 计算量估计

### GPU 训练与推断

出版级完整 campaign 的初步预算：

- 环境、复现、smoke：`80–150` 4090-equivalent GPU-hours；
- 模型开发与 ablation：`300–600` GPU-hours；
- 最终 ensemble、5 seeds、calibration：`500–1000` GPU-hours；
- inference、SBC、独立复现：`200–500` GPU-hours；
- 合计建议预留：**约 1,100–2,250 GPU-card-hours**。

该数值是项目级预算，不要求连续占用；必须通过自动关机降低空转。

### Solver 数据生成

先测单次热启动耗时 `t_sim`。墙钟时间估算：

```text
T_wall = N_sim * t_sim / (N_worker * efficiency)
```

对 `2e5–1e6` 个 solver labels，若单次为 `1–30 s`，总量约为：

- `~56–1,667 CPU-core-hours`（20 万点）；
- `~278–8,333 CPU-core-hours`（100 万点）。

因此数据生成应按 CPU 并行和主动学习优化，不应盲目堆 GPU。

## 8.6 存储与备份

- 代码：GitHub；
- 重要 manifests、checkpoints：AutoDL 文件存储 `/root/autodl-fs`；
- 高 I/O 训练数据：运行时复制到 `/root/autodl-tmp`；
- 每日同步；
- 每个 shard 写完立即生成 SHA256 和完成标记；
- 禁止只保存在本地数据盘；
- 实例连续关闭前检查数据已迁移；
- 所有长任务支持 resume。

建议容量：

- 共享可靠存储：100–300GB；
- 每节点本地高速盘：200GB 以上；
- 使用 Zarr/Parquet/HDF5，禁止百万个小文本文件。

## 8.7 AutoDL 运行规范

- 调试时优先使用无卡模式；
- 训练命令结束后自动关机；
- 每 15–30 分钟 checkpoint；
- 每个 job 写 heartbeat；
- OOM、NaN、solver crash 自动标记并重试有限次数；
- 不在 notebook 中启动无人值守生产任务；
- 所有生产任务通过 CLI + config；
- 维护 `docs/compute/autodl_inventory.md` 和 `docs/compute/cost_ledger.csv`。

---

## 9. 统计与科学验收阈值

### 9.1 后验收敛

- split R-hat `< 1.01`；
- bulk/tail ESS `> 1000`；
- MCSE `< 2%` posterior SD；
- nested sampling evidence error 明确报告；
- 多峰后验必须使用适合的方法并验证 mode coverage。

### 9.2 物理结论稳健性

主结论必须通过：

- 关键 prior 宽度变化；
- abundance 数据替换；
- solver/network 替换；
- rate set 替换；
- 训练 seed；
- 数值精度；
- OOD 策略；
- 固定/自由参数合理组合。

### 9.3 盲化

高影响力主统计量在最终 production 运行前冻结：

- 数据选择；
- prior；
- 主参数；
- 显著性/证据阈值；
- 核心图；
- 排除条件。

任何事后修改写入 deviation log。

---

## 10. 论文产出结构

### Paper A — Track A

候选主题：

> Robust parameter inference with BBNet in extended BBN cosmologies: convergence, extrapolation control, and parameter degeneracies

核心贡献：

- 当前管线严谨化；
- hard/soft OOD 结论；
- 10D posterior；
- `kappa` 退化/可辨识性；
- Schramm 物理切片；
- 可复现 release。

### Paper B — Track B 方法与物理

候选主题：

> End-to-end marginalization of nuclear-rate uncertainties in non-standard Big-Bang nucleosynthesis

核心贡献：

- 核 rate nuisance 的条件分布 emulator；
- 主动学习与主模态；
- 多 solver discrepancy；
- 标准 BBN 复现；
- 扩展宇宙学应用。

### PRL / Nature 子刊版本

标题必须以物理结论而不是工具名为中心，例如：

> Nuclear uncertainties reshape constraints on a stiff post-inflationary Universe

或

> A small set of nuclear uncertainty modes controls early-Universe constraints from primordial abundances

只有通过 Phase 8 gate 才可使用这类叙事。

---

## 11. 推荐 Issue / Milestone 划分

### Milestone M0 — Bootstrap

- R0.1–R0.3

### Milestone M1 — Baseline Freeze

- B1.1–B1.7

### Milestone M2 — Solver UQ Interface

- U2.1–U2.4

### Milestone M3 — Pilot Dataset & Sensitivity

- D3.1–D3.5

### Milestone M4 — Emulator Families

- E4.1–E4.5

### Milestone M5 — Calibration & Validation

- V5.1–V5.5

### Milestone M6 — Joint Inference

- I6.1–I6.4

### Milestone M7 — Physics Result

- P7.1–P7.4

### Milestone M8 — Release & Manuscript

- validation sign-off；
- code/data release；
- paper freeze；
- journal gate。

---

## 12. 首个 14 天执行顺序

### Days 1–2

- 初始化仓库、环境、CI、目录；
- 迁移现有代码；
- 登记现有数据和模型；
- 建立 AutoDL 3 节点。

### Days 3–5

- 完成 solver/emulator smoke；
- benchmark 单次 solver、内存、I/O；
- 复现一组已知丰度和当前 BBNet 指标；
- 检查所有硬编码与断点续跑。

### Days 6–8

- 重构 MCMC；
- 4 链、R-hat/ESS/MCSE；
- 生成 hard/soft 十维 posterior 对比；
- 输出参数而非仅丰度的定量距离。

### Days 9–11

- 运行 `n_t=-r/8` 与 free `n_t`；
- `kappa` 条件切片与 full marginal；
- 生成 Schramm-style 图；
- 冻结 Track A 主结论列表。

### Days 12–14

- 建立 reaction-rate registry；
- 打通一个 solver 的 `q_i` 扰动；
- 生成 Pilot-1k/10k；
- 完成第一版 sensitivity/Jacobian；
- 根据实测吞吐决定是否扩容到 4–6 节点。

---

## 13. 禁止的科研捷径

- 禁止用生成模型自行产生未标注“真值”来替代 BBN solver。
- 禁止把训练集插值精度外推到未覆盖参数域。
- 禁止用单链、固定步数或目测 corner plot 宣称收敛。
- 禁止只比较 abundance posterior 而忽略目标物理参数 posterior。
- 禁止在发现 `kappa` 被其他参数覆盖后仅固定这些参数并称为真实约束。
- 禁止把 solver disagreement 当作随机噪声直接平均掉。
- 禁止只报告最优 seed。
- 禁止在文章中隐藏失败率、OOD rejection 或 prior dependence。
- 禁止将 forecast 与真实数据约束混写。
- 禁止将锂问题的核物理解法预设为成立。

---

## 14. 合并与发布最终检查表

每个论文级 PR 必须回答：

- [ ] 对应哪个任务 ID？
- [ ] 物理假设是什么？
- [ ] 与现有文献相比新增什么？
- [ ] 输入参数、prior、单位是否登记？
- [ ] 数据是否来自真实批准 solver？
- [ ] 数据/模型/config/commit hash 是否记录？
- [ ] 是否有独立 holdout/challenge set？
- [ ] 是否通过 convergence、coverage、SBC、OOD？
- [ ] 是否至少两个 solver/network？
- [ ] 是否报告所有 seed？
- [ ] 是否有 solver fallback？
- [ ] 结果是否依赖固定参数或 prior 边界？
- [ ] 是否能在新 AutoDL 实例复现？
- [ ] 是否更新 claim-evidence matrix？
- [ ] 是否更新计算资源与成本记录？
- [ ] 是否满足目标期刊的 go/no-go gate？

---

## 15. 初始参考文献清单

以下条目是实施时的最低阅读集，代理应在 `docs/literature/` 中维护结构化笔记：

1. Zhang et al., *BBNet: accurate neural network emulator for primordial light element abundances*, arXiv:2512.15266 (2025).
2. Giovanetti et al., *LINX: A Fast, Differentiable, and Extensible Big Bang Nucleosynthesis Package*, Phys. Rev. D 112, 063531 (2025), arXiv:2408.14538.
3. Giovanetti et al., *Cosmological Parameter Estimation with a Joint-Likelihood Analysis of the CMB and BBN*, Phys. Rev. D 112, 063530 (2025), arXiv:2408.14531.
4. Burns, Tait & Valli, *PRyMordial*, Eur. Phys. J. C 84, 86 (2024), arXiv:2307.07061.
5. Schöneberg, *The 2024 BBN baryon abundance update*, arXiv:2401.15054.
6. Fields et al., *Big-Bang Nucleosynthesis after Planck*, JCAP 03 (2020) 010.
7. Iliadis & Coc, *Thermonuclear Reaction Rates and Primordial Nucleosynthesis*, ApJ 901, 127 (2020), arXiv:2008.12200.
8. Cook & Meyers, *Insights for early dark energy with big bang nucleosynthesis*, Phys. Rev. D 113, 043519 (2026).
9. Gloeckler et al., *All-in-one simulation-based inference*, ICML 2024.
10. Sloman et al., *Bayesian Active Learning in the Presence of Nuisance Parameters*, UAI 2024.
11. Emma & Ashton, *Residual neural likelihood estimation and its application to gravitational-wave astronomy*, Phys. Rev. D 113, 124064 (2026).
12. Chen et al., *Enhanced primordial gravitational waves from a stiff postinflationary era*, Phys. Rev. D 110, 063554 (2024).

---

## 16. 最终决策原则

本项目的优先级固定为：

```text
物理正确性
> 可校准的不确定度
> 跨 solver 稳健性
> 可复现性
> 计算效率
> 模型新颖性
> 宣传性结果
```

当更复杂的 AI 模型与更简单、可验证的物理方法结论一致时，优先使用后者；当 AI 模型能够以严格校准和显著更低的 solver 预算实现此前不可行的联合推断时，才将其作为核心贡献。
