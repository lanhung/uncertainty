# AGENTS v0.2.0 规范分卷：论文路线、里程碑与发布

> 本文件是根级 `AGENTS.md` 的规范性组成部分。冲突时以根级文件为准。
> 覆盖范围：Nature Astronomy/NCS/NMI/NC 路线、Milestone、首个 14 天、年度节奏、禁令、发布检查与最低阅读。

---

## 10. 论文与投稿路线

### 10.1 Paper A — Track A

候选题目：

> Robust inference with neural BBN emulators in extended cosmologies: convergence, extrapolation control and parameter degeneracies

核心：

- 当前管线严谨化；
- hard/soft OOD；
- 十维 posterior；
- `kappa`/`n_t`/`T_re`；
- Schramm slices；
- 可复现 release。

Track A 不包含函数型核 rate 的旗舰结论，避免提前消耗 Track B 核心贡献。

### 10.2 Flagship Astrophysics — Route NA

标题必须是物理结论，例如：

> Nuclear-rate function uncertainties reshape limits on a stiff post-inflationary Universe

或：

> Primordial abundances reveal a nuclear-systematics boundary for gravitational-wave probes of the early Universe

主文结构：

1. broad astrophysical problem；
2. why current treatment is insufficient；
3. headline discovery；
4. physical mechanism；
5. cross-solver/data validation；
6. implications for current/future observations；
7. methods concise，细节进 Methods/Supplement。

### 10.3 Flagship Computational — Route NCS

候选：

> Calibrated amortization of structured nuisance functions across multi-fidelity scientific simulators

必须突出：

- general problem；
- algorithm/framework；
- total-cost scaling；
- BBN discovery；
- cross-domain demonstration；
- open benchmark/software。

### 10.4 Flagship ML — Route NMI

候选标题只能在算法真正新时确定。主文必须：

- 先定义 ML 问题；
- 给出新 objective/algorithm/theory；
- 多 benchmark 与 ablation；
- calibration/OOD/failure；
- BBN 作为高影响力应用；
- 对 SBI/ML 社区提出普遍结论。

### 10.5 Nature Communications 路线

适合完整而重要的专业推进：

- function-valued rate UQ；
- multi-solver discrepancy；
- non-standard BBN inference；
- open benchmark；
- 明确的专业科学结论。

### 10.6 投稿前编辑测试

提交 presubmission inquiry 或正式稿前，准备一页：

```text
Problem
What was unknown
What we found
Why it matters broadly
Why now
Why this journal
Three strongest figures
Three strongest robustness tests
Closest competing papers
```

若第一段必须用大量 BBNet/SBI 术语才能解释重要性，Route NA 不成熟；若没有跨任务算法证据，Route NMI 不成熟；若没有总成本与通用框架，Route NCS 不成熟。

### 10.7 外部预审

旗舰稿至少邀请：

- 1 位 BBN/核天体物理专家；
- 1 位早期宇宙/GW 专家；
- 1 位统计/SBI/ML 专家；
- 1 位不参与项目的计算科学或软件复现人员。

记录但不强制公开外部反馈与处理决定。

---

## 11. Milestone 与 Issue 划分

### M0 — Bootstrap

- R0.1–R0.3

### M0.5 — Boundary & Preregistration

- LIT-01/LIT-02；
- WHY-NOT-01；
- OBS-01；
- NEUTRON-01；
- route success criteria。

### M1 — Track A Freeze

- B1.1–B1.7

### M2 — Solver & Functional Rate Foundation

- S2.1；
- R2.2–R2.3；
- S2.4；
- C2.5。

### M2.5 — Fisher Gate

- G2.5.1–G2.5.3；
- `FISHER_GATE_REPORT.md`。

### M3 — Pilot & Sensitivity Reordering

- D3.1–D3.6

### M4 — Model Families

- E4.1–E4.5；
- E4.6 仅 NCS/NMI。

### M5 — Calibration & Validation

- V5.1–V5.6

### M6 — Joint Inference

- I6.1–I6.5

### M7 — Physics Discovery

- P7.1–P7.6

### M8 — Computational/ML Discovery

- C8.1–C8.2；
- M8.3–M8.4。

### M9 — Flagship Gate & Release

- Route Gate；
- independent sign-off；
- code/data/model release；
- manuscript freeze；
- presubmission inquiry/submission。

---

## 12. 从现在开始的首个 14 天

### Days 1–2：仓库与 Track A 立即恢复

- 将全部现有代码迁入 GitHub；
- 建立环境锁、CI、目录、README；
- 恢复一组已知 BBNet 结果；
- 启动 Node S 与 Node T；
- 创建所有 blocker issues。

交付：`make smoke`、现有结果复现报告、AutoDL inventory。

### Days 3–4：竞争基线

- 安装/运行 LINX、PRyMordial；
- 获取 PRIMAT/PArthENoPE 版本信息；
- 完成 competitor matrix 第一版；
- 写 why-not memo 初稿；
- 复现标准 BBN 中至少一个 rate marginalization 结果。

交付：`LIT-01`、`competitor_matrix_v0.1.csv`。

### Days 5–6：数据与中子寿命预注册

- 整理 LBT 2026、legacy、EMPRESS、D/H、Li；
- 冻结主候选和 stress-test 角色；
- 定义 N0–N3；
- 登记 CMB/BAO 与 LVK 数据版本；
- 不查看任何新 Track B production 显著性。

交付：`ADR-OBS-001`、`ADR-NEUTRON-001`。

### Days 7–9：solver matrix 与局部响应

- 打通 S0/S1/S5/S6 至少四条路径；
- 统一 rate IDs 与 abundance conventions；
- 在 20–40 个点计算中心值与 Jacobian；
- benchmark cold/warm/CPU/RAM/float64；
- Node V 按需开启做独立检查。

交付：`ADR-SOLVER-001`、throughput 表、local response plots。

### Days 10–11：Fisher Gate 第一版

- 扩展到至少 64 个代表点；
- 估算 scalar rate、function-shape proxy、solver discrepancy 对后验影响；
- 分类 G0/G1/G2/G3；
- 明确是否允许 Pilot-10k。

交付：`FISHER_GATE_REPORT-v0.1.md`。

### Days 12–14：分流执行

若 `G0`：

- Track A 全速推进；
- Track B 只保留方法可行性与精确负结果；
- 不生成大数据。

若 `G1/G2/G3`：

- 完成 function-rate basis v1；
- 生成 Pilot-1k；
- 通过后开始 Pilot-10k；
- 建立 sensitivity atlas 复现；
- 更新资源预算与 flagship route 候选。

同时 Track A 继续运行 4 链 MCMC，不因上述工作停止。

### 12.1 结果依赖型年度节奏

以下是项目管理窗口，不是对科学发现或投稿日期的承诺。每个阶段只有通过出口 Gate 才进入下一阶段。

| 时间窗口 | 主任务 | 强制出口 |
|---|---|---|
| 2026-07-21 至 2026-08-03 | Bootstrap、Track A 恢复、竞争矩阵、OBS/NEUTRON 预注册 | `make smoke`、LIT/OBS ADR、至少四条 solver 路径、Fisher v0.1 |
| 2026-08-04 至 2026-08-17 | matched-physics solver 审计、64–128 点 Fisher campaign | G0/G1/G2/G3 决策；决定是否允许 Pilot-10k |
| 2026-08-18 至 2026-09-15 | Track A 冻结；通过 Gate 时运行 Pilot 与 sensitivity-atlas 复现 | Track A claim freeze；Pilot 数据卡；非标准敏感性重排初判 |
| 2026-09-16 至 2026-10-31 | 三个头部反应的函数型 posterior、multi-solver 数据设计 | scalar-vs-shape 结论；production 数据规模与 basis 冻结 |
| 2026-11-01 至 2026-12-31 | M2–M7、强非深度基线、主动学习、multi-fidelity | 模型候选不超过两类；端到端成本与 calibration learning curves |
| 2027-01-01 至 2027-02-28 | SBC、blind challenge、direct posterior recovery、联合 BBN/CMB/GW 推断 | `VALIDATION_PASS` 或明确失败；主后验冻结 |
| 2027-03-01 至 2027-04-30 | 旗舰物理/计算发现、外部专家 red-team、独立复现 | Route NA/NCS/NMI/NC Gate 评审；发现主张或诚实 pivot |
| 2027-05-01 至 2027-06-30 | release candidate、论文、editor pitch、presubmission inquiry | 开放代码/数据/model card、复现包、稿件与 cover letter |

Track A 的完成不依赖 Track B Gate。Track B 的 Nature 路线不以日期强行开启；没有通过证据门槛时，继续验证或转向，而不是按日历宣布发现。

### 12.2 每周固定科研节奏

- 周一：锁定本周任务、预算、预期失败模式；
- 周二至周四：生产实验；新发现只登记，不临时改变 confirmatory protocol；
- 周五上午：结果与统计诊断；
- 周五下午：literature delta、成本账本、claim–evidence matrix、失败复盘；
- 每两周：A09 red-team mini-review；
- 每月：Novelty Clearance refresh 与 Nature 三句话测试；
- 每个 Gate 前：冻结 config/hash，禁止“最后再调一次”式无记录修改。

### 12.3 每日运行看板

每台计算节点必须在 `docs/compute/daily_status/DATE.md` 登记：

```text
node / GPU / CPU / RAM / storage
active run IDs
completed accepted labels
failed labels by reason
GPU-hours and CPU-core-hours
checkpoint age
backup status
blocking issue
next decision
```

项目看板只统计可追溯 run；手工 notebook 试验在转为 CLI/config 前不得计入正式证据。

---

## 13. 禁止的科研捷径

- 禁止用生成模型产生未经 solver 验证的物理真值。
- 禁止把标量 `q_i` 接入网络称为全新方法。
- 禁止把标准 BBN 的已知关键反应排名称为发现。
- 禁止忽略 PRyMordial、PRIMAT、LINX、ABCMB 与 2026 sensitivity/GP 工作。
- 禁止只比较 PArthENoPE 与 AlterBBN 就声称跨 solver 稳健。
- 禁止只报告单次 forward 加速而隐藏标签生成成本。
- 禁止用单链、固定步数或目测 corner plot 宣称收敛。
- 禁止只比较 abundance posterior 而不比较物理参数 posterior。
- 禁止在 `kappa` 不可辨识后固定退化参数并称为真实约束。
- 禁止将 solver disagreement 当作白噪声直接平均。
- 禁止只报告最佳 seed。
- 禁止在看到结果后选择 LBT/EMPRESS/D/H 或中子寿命模型。
- 禁止把 forecast 与真实约束混写。
- 禁止通过缩窄 prior、选择模型边界或删除 tension 数据制造显著性。
- 禁止为迎合 Nature 目标夸大负结果或不确定发现。
- 禁止 NMI 路线只在 BBN 单任务上验证。
- 禁止 NCS 路线不报告端到端成本和开放框架。
- 禁止 Nature Astronomy 标题以工具名或网络架构为中心。
- 禁止未经独立验证签署提交旗舰稿。

---

## 14. 合并、冻结与发布检查表

每个论文级 PR 必须回答：

- [ ] 对应哪个任务 ID 和 claim ID？
- [ ] 科学假设与零假设是什么？
- [ ] 与 LINX/PRyMordial/PRIMAT/最新文献相比新增什么？
- [ ] 数据、prior 和主统计量是否预注册？
- [ ] scalar 与 functional rate 是否区分？
- [ ] 中子寿命模型是否登记？
- [ ] 至少两个独立 solver/network？
- [ ] 数据是否全部来自批准的真实 solver？
- [ ] config/dataset/model/commit hashes 是否记录？
- [ ] 是否有 block holdout 和 blind challenge？
- [ ] convergence、coverage、SBC、OOD 是否通过？
- [ ] direct solver posterior recovery 是否通过？
- [ ] 是否报告所有 seed 和失败率？
- [ ] 是否有 solver fallback？
- [ ] 结果是否依赖固定参数、prior boundary 或单一数据？
- [ ] 是否更新 cost ledger？
- [ ] 是否更新 competitor matrix 与 literature snapshot？
- [ ] 是否更新 claim–evidence matrix？
- [ ] 独立 Validation 与 Red-Team 是否签署？
- [ ] 是否满足目标 Route Gate？
- [ ] 能否在新 AutoDL 实例复现？

最终 release 还必须包含：

- frozen configs；
- environment lock；
- dataset/model manifests；
- reproduction commands；
- code/data licenses；
- Zenodo/GitHub Release；
- known limitations；
- failure cases；
- compute statement。

---

## 15. 强制最低阅读与持续更新清单

以下是 v0.2.0 的最低边界，不是完整 bibliography。正式笔记进入 `docs/literature/`。

### BBN 代码、联合推断与竞争基线

1. Zhang et al., **BBNet: accurate neural network emulator for primordial light element abundances**, arXiv:2512.15266.
2. Giovanetti et al., **LINX: A Fast, Differentiable, and Extensible Big Bang Nucleosynthesis Package**, arXiv:2408.14538; Phys. Rev. D 112, 063531.
3. Giovanetti et al., **Cosmological Parameter Estimation with a Joint-Likelihood Analysis of the CMB and BBN**, arXiv:2408.14531.
4. Burns, Tait & Valli, **PRyMordial: The First Three Minutes, Within and Beyond the Standard Model**, arXiv:2307.07061; EPJC 84, 86.
5. Schöneberg, **The 2024 BBN baryon abundance update**, arXiv:2401.15054.
6. Pitrou et al., **Precision big bang nucleosynthesis with improved Helium-4 predictions**, arXiv:1801.08023, Physics Reports 754.
7. Pitrou et al., **Precision Big Bang Nucleosynthesis with the New Code PRIMAT**, arXiv:1909.12046.
8. Zhou, Giovanetti & Liu, **ABCMB: A Python+JAX Package for the Cosmic Microwave Background Power Spectrum**, arXiv:2602.15104.

### 2025–2026 直接前沿

9. Cook & Meyers, **Insights for Early Dark Energy with Big Bang Nucleosynthesis**, arXiv:2512.11163; Phys. Rev. D 113, 043519.
10. Burns, **Inside the Black Box of Big Bang Nucleosynthesis: Parameter Sensitivity Studies in Light of new LBT Data**, arXiv:2603.22414.
11. Launders, Giovanetti & Liu, **A data-driven prediction for the primordial deuterium abundance**, arXiv:2604.16600.
12. Aver et al., **The LBT `Y_p` Project IV: A New Value of the Primordial Helium Abundance**, arXiv:2601.22238.
13. Yeh et al., **The LBT `Y_p` Project V: Cosmological Implications**, arXiv:2601.22239.
14. Yanagisawa et al., **EMPRESS. XV. A New Determination of the Primordial Helium Abundance Suggesting a Moderately Low `Y_p` Value**, arXiv:2506.24050; Astrophys. J. 1004, 55 (2026).
15. Kislitsyn et al., **A New Precise Determination of the Primordial Abundance of Deuterium: Measurement in the metal-poor sub-DLA system at `z=3.42` towards quasar J1332+0052**, arXiv:2401.12797; MNRAS 528, 4068 (2024).
16. Pettini & Cooke, **Precision cosmology with the lightest elements**, Astrophys. Space Sci. 371, 20 (2026).
17. Goldstein & Hill, **A 2% determination of `N_eff` from primordial element abundance, CMB and BAO**, arXiv:2603.13226.
18. LVK, **Cosmological and High Energy Physics implications from gravitational-wave background searches in O1–O4a**, arXiv:2510.26848.
19. Fuwa et al., **Improved measurements of neutron lifetime with cold neutron beam at J-PARC**, arXiv:2412.19519.
20. Tait, **Deuterium-Proton Fusion in an Effective Field Theory Constructed from On-Shell Amplitudes**, arXiv:2607.05514.

### 核反应率、Li 与统计方法

21. Iliadis & Coc, **Thermonuclear reaction rates and primordial nucleosynthesis**, arXiv:2008.12200.
22. Iliadis et al., **Bayesian Estimation of Thermonuclear Reaction Rates**, arXiv:1608.05853.
23. de Souza et al., **Hierarchical Bayesian Thermonuclear Rate for `7Be(n,p)7Li`**, arXiv:1912.06210.
24. Gloeckler et al., **All-in-one simulation-based inference**, ICML 2024.
25. Sloman et al., **Bayesian Active Learning in the Presence of Nuisance Parameters**, UAI 2024.
26. Emma & Ashton, **Residual neural likelihood estimation and its application to gravitational-wave astronomy**, Phys. Rev. D 113, 124064.

### 目标期刊范围

27. Nature Astronomy, **Aims & Scope**.
28. Nature Computational Science, **Aims & Scope**.
29. Nature Machine Intelligence, **Aims & Scope**.
30. Nature Communications, **Aims & Scope**.

Literature Agent 必须在每个旗舰 Gate 前检查这些条目的版本、同行评议状态和后续引用。

---

## 16. 最终决策原则

项目优先级固定为：

```text
物理正确性
> 数据与核物理来源可信
> 可校准的不确定度
> 跨 solver / 跨数据稳健性
> 可证伪的新发现
> 可复现性与开放科学
> 端到端计算效率
> 机器学习或架构新颖性
> 期刊宣传性
```

最终规则：

1. 简单方法能达到相同物理结论与校准时，优先简单方法。
2. AI 只有在解锁此前不可行的推断、产生新科学发现或形成通用算法时才成为核心贡献。
3. Nature Astronomy 路线由物理发现决定；Nature Computational Science 路线由通用计算突破决定；Nature Machine Intelligence 路线由新 ML 原理决定。
4. Nature Communications 是重要专业推进的候选，不是可以通过包装自动达到的最低保证。
5. 任何负结果只要预注册、精确、跨 solver 稳健并能改变未来研究决策，都是有价值的科学结果。
6. 期刊目标是提高证据标准，绝不能反过来扭曲证据。

当旗舰结果尚未通过 Gate 时，默认行动不是继续扩大模型，而是：

```text
复现竞争基线
-> 冻结数据与 prior
-> 通过 Fisher Gate
-> 生成最小 Pilot
-> 验证物理影响
-> 再决定模型复杂度和算力
```
