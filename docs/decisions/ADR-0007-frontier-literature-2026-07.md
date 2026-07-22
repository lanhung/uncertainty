# ADR-0007：根据 2026 年 7 月前沿调研重排 BBN 核反应率 UQ 工作

- **状态**：Accepted
- **日期**：2026-07-23
- **适用范围**：核反应率先验、直接 Monte Carlo、solver 基线、SBI 方法、校准、任务 DAG、创新声明
- **前置决策**：`ADR-0006-uncertainty-core-refocus.md`
- **证据文件**：`docs/literature/FRONTIER_REVIEW_2026-07.md`

## 1. 新证据

系统搜索表明，原始构想的多个组成部分已经由公开工作完成：

1. PRIMAT 已提供原生 log-normal rate variation、`run_mc()` / `mc_uncertainty()` 与逐样本丰度输出；
2. PRyMordial 已能显式边缘化核反应率，Schöneberg 2024 已比较显式边缘化与 PArthENoPE 型事后理论误差；
3. LINX 已提供快速可微 BBN、`nuclear_rates_q` 与联合 CMB+BBN 核反应率边缘化；
4. 2026 sensitivity atlas 已系统覆盖 14 个物理/宇宙学参数和 63 个反应率；
5. 2026 data-driven D/H 工作已对三个头部氘反应使用 Gaussian process；
6. ETR25 已发布现代统计意义下的实验 thermonuclear-rate 产品，包括实际 PDF 的 16/50/84 百分位和 log-normal factor-uncertainty 近似；
7. TMNRE、AMNRE、posterior SBC、局部 conformal calibration 与 nuisance-aware active learning 已为高维 nuisance marginalization 提供强方法基线。

因此，本项目不能再把“Monte Carlo 反应率传播”“标量 `q_i`”“标准 BBN 显式边缘化”“三个氘反应的 GP”“普通 BBN emulator”或“把 flow 用到 nuisance variables”作为核心创新。

## 2. 决策

### 2.1 核物理输入优先级

Stage R0 的主候选实验 rate source 改为 ETR25，并强制区分：

```text
actual/posterior rate probability information
vs scalar log-normal approximation
vs solver-distributed legacy low/high representation
```

任何生产数据前必须：

- 固定 exact source、revision、license、checksum、temperature grid 与 units；
- 保留同一 nuclear-input realization 在温度上的 coherent rate curve；
- 禁止无协方差依据的独立 temperature-bin noise；
- 对缺失 cross-reaction covariance 建立预注册 stress model；
- 量化 actual PDF 与 log-normal approximation 的差异。

### 2.2 直接 baseline 优先于自制实现

新的自定义 Monte Carlo driver 不能早于以下复现：

1. PRIMAT native MC；
2. PRyMordial explicit marginalization；
3. LINX central + `nuclear_rates_q`；
4. sensitivity-atlas R0 slice；
5. 2026 GP deuterium prior structure。

这些 baseline 定义当前可直接完成的功能与成本下限。

### 2.3 第一项候选新科学对象

第一项可能支持新结论的对象不是 fixed-point theoretical band 本身，而是：

```text
p(Y_p, D/H | theta)
+ C_rate(theta)
+ joint tails/correlation
+ actual-PDF versus scalar/lognormal dependence
+ fixed-C_th posterior risk
```

Fixed-point band 仍是必要的复现和校准里程碑。

### 2.4 学习方法不预设

若 `UQ2-GATE-REPORT` 达到 `G1+`，方法比较顺序为：

1. deterministic conditional MLP；
2. heteroscedastic multivariate Gaussian / ensemble；
3. mixture or calibrated quantile model；
4. TMNRE / AMNRE-style marginal ratio estimation；
5. neural likelihood / flow only when distributional evidence requires it；
6. multi-fidelity or function-valued model only after measured necessity。

GAN、diffusion、Transformer、normalizing flow 与 active learning 均不是默认路线。

### 2.5 校准标准升级

除原有 direct posterior recovery 外，若使用 learned model，必须加入：

- prior SBC；
- posterior-focused SBC；
- multiple training seeds / ensembles；
- local coverage or equivalent conditional calibration；
- OOD and structured failure tests；
- certified direct fallback；
- 计入 label generation 的 end-to-end economics。

## 3. 新的候选贡献

本项目的最小可辩护贡献是下列交集的实证结果：

1. 当前核反应 probability/posterior information；
2. coherent rate-curve sampling；
3. parameter-dependent joint abundance distribution；
4. fixed post-hoc `C_th` 的有效区间或失效图；
5. matched solver/rate-library/weak-physics decomposition；
6. posterior fidelity、coverage、OOD 与 fallback；
7. 相对 PRIMAT、PRyMordial、LINX 和 marginal-SBI baseline 的完整成本优势。

任一单独组件均不获得创新许可。

## 4. 任务修改

`plan/plan.yaml` 升级到 version 4，新增：

- `P0-FRONTIER-2026-07`；
- `UQ0-ETR25-R0-INGEST`；
- `UQ0-RATE-PDF-AUDIT`；
- `UQ0-NATIVE-UQ-REPRO`；
- `UQ1-RATE-PDF-PROPAGATION`；
- `UQ2-METHOD-BASELINE-MANIFEST`。

并修改：

- `UQ0-R0-RATE-PRIOR` 依赖 ETR25/PDF audit；
- `UQ1-FIDUCIAL-MC-1K` 依赖 native baseline reproduction；
- `UQ2-GATE-REPORT` 同时评估科学新意和 learned-model necessity。

## 5. 停止条件

以下任一成立时，停止扩大主要主张：

- actual/posterior 与 scalar log-normal 在所有冻结终点上低于 null threshold；
- `C_rate(theta)` 在注册域内近似恒定；
- `U-M1` 与 `U-M2` 的 posterior shift `<0.1 sigma`、interval change `<5%` 且无 topology change；
- direct PRIMAT/LINX/PRyMordial 能在预算内完成完整 inference/calibration workload；
- learned model 未通过 coverage、posterior recovery、OOD 或 fallback gate。

不得通过事后增加反应、扩大 prior、更换数据、激活非标准宇宙学或更换神经网络架构追逐显著性。

## 6. 直接后果

- ETR25 ingestion 是当前最高优先级核物理任务；
- fixed-point MC band 明确降为 reproduction/calibration，不作为首创新声明；
- standard sensitivity ranking 与三个 deuterium GP 明确降为 baseline；
- TMNRE/AMNRE 加入 post-Gate 强制方法比较；
- Nature-tier Gate 继续关闭；
- 一台可用 AutoDL worker 仍足以推进 P0–UQ2，第二台只提供弹性容量。

## 7. 复审触发器

- ETR25 R0 posterior/sample products无法重建或不足以生成 coherent curves；
- 新论文直接完成 actual-PDF-to-posterior failure map；
- PRIMAT/PRyMordial/LINX API 或 release 发生实质变化；
- 16-point smoke 达到 `G2/G3`；
- direct workload 已经足够便宜，导致 learned-model 路线失去必要性；
- 月度文献刷新发现同类端到端工作。
