# ADR-0005：以待投 JCAP 稿件为科学基线，并转向可自包含的不确定度续篇

- **状态**：Accepted
- **日期**：2026-07-23
- **适用范围**：Track A、Track B、科学资产、BBNet+、SageNet+、stiffGWpy、核反应率 UQ、投稿优先级
- **替代/澄清**：替代把“恢复旧两丰度 BBNet 管线”作为唯一关键路径的执行假设；不降低根级 `AGENTS.md` 的物理正确性、预注册、验证与停止条件

## 1. 新事实

作者提供的待投 JCAP 稿件已经包含一条比旧计划更成熟的科学基线：

1. 四丰度 BBNet+：`Y_p`、`D/H`、`3He/H`、`7Li/H`；
2. 两个 stiff-extended BBN backend：PArthENoPE 与 AlterBBN；
3. SageNet+ SGWB 谱 emulator 与稳定的 `Delta N_eff` 积分层；
4. Cobaya 联合推断、partial-likelihood tests、free-`Delta N_eff` 与 free-`kappa10` diagnostics；
5. 明确的物理定义：

   ```text
   kappa10 = rho_stiff / rho_gamma at T = 10 MeV
   ```

6. 论文主结果是一个定量 no-independent-lithium-solution 结论：能够降低 `7Li/H` 的 homogeneous stiff expansion 方向同时把 `D/H` 与 `Y_p` 推出允许区；
7. 稿件已报告四丰度 emulator 的 held-out accuracy、约 `10^4` 单点加速、两个 backend 的后验上限、partial-likelihood 机制诊断与直接数值 Cobaya wall-time benchmark。

因此，项目不再把“是否存在一条可投稿的 Track A 科学线”视为未知。当前首要任务是把这条已经存在的科学线变成**可审计、可复现、与数据/软件可用性陈述一致的发布包**。

## 2. 决策

### 2.1 当前优先级

立即采用以下顺序：

```text
M0：JCAP 稿件与公开资产冻结
  > UQ0：自包含 baseline 与三十天内可运行的 scalar-UQ smoke
  > UQ1：正式 64 点 Fisher/linear gate
  > 条件性 Pilot / emulator / Nature-tier campaign
  > 其余通用 ABCMB/LINX 审计与 ML 方法扩展
```

当前未直接服务于 M0、UQ0 或 UQ1 的审计任务移出 desired-state critical path；它们保留在 Git 历史和 backlog 文档中，后续按证据需要恢复。

### 2.2 Track A 的新定义

Track A 不再是“从缺失的旧 checkpoint 猜测并重建两丰度 BBNet”。Track A 现在定义为：

> **冻结、复现并提交四丰度 BBNet+ + SageNet+ + stiff-SGWB 的 JCAP 稿件。**

必须完成：

- 精确登记稿件使用的代码、权重、scaler、数据生成配置、solver 修改、Cobaya 配置、chains、scan tables 与 plotting scripts；
- 在干净环境中复现至少一组 emulator accuracy、一个 main posterior、一个 partial-likelihood result 和一个 deterministic no-go diagnostic；
- 修复论文数据与软件可用性陈述和实际公开仓库之间的差异；
- 在 GitHub/Zenodo 上发布不可变版本、checksums、license 与引用信息；
- 明确区分“稿件复现数据层”和“下一篇 UQ 主分析数据层”。

### 2.3 Track B 的新旗舰问题

近期 Track B 不再从泛化的“完整 UQ 是否改变任意 stiff-era/SGWB 结论”起步，而冻结为更尖锐、可直接继承稿件的检验：

> **在完整传播核反应率、弱反应与 backend discrepancy 后，待投稿件关于 homogeneous pre-BBN stiff phase 不能独立解决 lithium problem 的结论是否仍成立？**

主终点为：

1. `Delta log10(kappa10_95)`：相对 central-rate baseline 的 95% 上限移动；
2. `V_viable`：同时满足注册的 `Y_p`、`D/H`、`7Li/H` 条件的可行体积或其严格上限；
3. `min_DH_tension_at_Li_plateau`：把 lithium 拉到 plateau 时最小可实现的 deuterium tension；
4. `min_Yp_tension_at_Li_plateau`；
5. full 与 D/H+`Y_p`、Li-only partial likelihood 之间的结论稳定性；
6. PArthENoPE-like、AlterBBN-like、PRIMAT/LINX-like rate choices 下的稳定性；
7. 哪些核反应控制 no-go boundary，而不只是控制标准 BBN 的单一丰度。

Nature Astronomy 路线只有在上述结论发生定性变化、允许区拓扑变化、或得到跨模型的一般 no-go/viable-mode 发现时才重新开放。

### 2.4 首批核反应集合由 3 个扩大为 6 个

原先仅针对 deuterium 的三反应集合不足以直接检验 lithium no-go。首批 scalar-UQ core 固定为：

```text
d(p,gamma)3He
d(d,n)3He
d(d,p)t
3He(alpha,gamma)7Be
7Be(n,p)7Li
7Li(p,alpha)4He
```

`tau_n` 与 weak-rate normalization 单独处理，禁止重复计数。

函数型 rate modes 不再预先固定为只做三个 deuterium reactions。只有 scalar smoke/Fisher 显示某反应对 no-go endpoint 有决策意义后，才为该反应构造 GP/KL/物理 shape modes。

## 3. 自包含实现策略

### 3.1 优先策略：作者资产 handoff

若原始资产存在，应进入 quarantine、hash、license 与 schema review，而不是重新训练：

- BBNet+ 四丰度源码；
- PArthENoPE/AlterBBN 训练数据或可重建 generator；
- 两套 pretrained weights 与 scalers；
- stiff-extended solver source/patches；
- SageNet+ exact source/weights；
- stiffGWpy exact revision；
- Cobaya likelihood/theory/config；
- main、partial-likelihood、consistency、hard/soft chains；
- deterministic scan tables；
- figure/post-processing scripts。

### 3.2 允许策略：clean-room 自包含重建

如果部分旧资产无法恢复，允许从零重建；新实现必须明确标记为 clean-room scientific implementation，而不是“恢复原文件”。允许使用：

- 官方 PArthENoPE 3.0；
- AlterBBN 2.2 公共源码；
- LINX、PRyMordial 与 PRIMAT 作为公开回归/精度基线；
- `bohuarolandli/stiffGWpy` 中公开的 stiff/SGWB 物理定义；
- `YifangLuo/SageNet` 的公开谱 emulator 接口与权重；
- 作者提供或从批准 solver 新生成的训练数据。

Clean-room 重建的最小顺序：

```text
透明 stiff H(T) contract
-> direct solver implementation
-> standard/stiff regression
-> four-abundance training data
-> simple deterministic emulator baseline
-> manuscript posterior recovery
-> nuclear-rate UQ
```

任何 AI 生成但未经批准 solver 计算的数据都不能作为监督标签。

## 4. 公开资产与稿件陈述的硬门槛

稿件声称 BBNet+ 代码、trained weights 与 plotting/MCMC assets 可公开获取。因此投稿冻结前必须验证：

- 链接实际存在且指向 BBNet+ 四丰度版本，而不是旧两丰度代码；
- weights/scalers 不是 placeholder、删除文件或截断 archive；
- README 的参数、输出、版本、安装与 CLI 与实际代码一致；
- modified solvers 的许可允许发布；若不能发布，必须提供 patch、container 或可审计生成服务，并在稿件中准确说明；
- Zenodo 至少包含 chain summaries、deterministic scan tables、figure inputs、checksums 与环境信息；
- 数据与软件可用性陈述不得预先声称尚未上线的资产“已公开”。

在这些条件满足前，`M0-JCAP-FREEZE` 不得完成。

## 5. 数据层分离

建立两个不可混用的 analysis strata：

1. `MANUSCRIPT-OBS-v1`：精确复现待投稿件所用 PDG abundance likelihood 与 `tau_n` prior；
2. `OBS-v1`：下一篇 UQ 工作的 LBT/Cooke 主分析及预注册 stress tests。

`MANUSCRIPT-OBS-v1` 用于复现与投稿，不因新 UQ 计划而改写。`OBS-v1` 用于续篇，不得把稿件的 PDG 选择悄悄升级为 UQ 主数据。

## 6. 计算与方法路线

稿件已经提供直接 numerical SGWB+BBN Cobaya benchmark，说明在完整 wide-prior joint pipeline 中 emulator 有实际经济价值。该证据可支持稿件的工程必要性，但不能自动支持新的通用 ML claim。

- Nature Machine Intelligence 路线保持 dormant；
- Nature Computational Science 路线保持 dormant，除非产生新的、跨 simulator 的方法；
- 近期方法开发必须服务于 no-go robustness、coverage 或高维 rate marginalization，而不是为了模型名称；
- direct-first benchmark 仍保留，但不再阻塞 JCAP 稿件提交。

## 7. 停止与升级条件

### JCAP baseline

只要复现、release 与稿件审计通过，即可投稿；不等待完整核反应率 UQ。

### UQ gate

- scalar smoke 显示所有 no-go endpoints 远低于注册 null boundary：完成正式 Fisher 复核后停止大规模 Pilot；
- Fisher `G0`：形成 robust-null/upper-bound follow-up，不做 Pilot-10k；
- `G1`：只做 targeted Pilot-1k；
- `G2/G3`：才允许函数型 rates、Pilot-10k、多 solver production 与 Nature-tier red team。

## 8. 直接后果

- 第二台 AutoDL 不再是科学关键路径；一台合格 worker 足以推进 M0/UQ0；
- pending ABCMB full audit、LINX gradient audit、standard challenge grid 移出当前 desired state；
- 旧 `P0-reproduce-bbnet` 被四丰度 manuscript reproduction tasks 替代；
- `P0-solvers-build` 被“作者资产 handoff”和“clean-room public solver path”拆开；
- 核反应率第一阶段由 generic 12-reaction schema 改为 decision-focused core-6 scalar gate；
- Pilot-1k、Pilot-10k 与 Nature-tier tasks 在 Gate 之前不出现在 active plan 中。

## 9. 复审触发器

- JCAP 稿件物理模型、数据或主结论发生实质修改；
- BBNet+ / modified solver assets 无法在 7 天内交付；
- clean-room solver 无法复现 manuscript standard/stiff slices；
- scalar smoke 显示 lithium no-go 对核反应率极端敏感；
- 新文献直接完成同一 no-go robustness 分析；
- Fisher Gate 达到 G2/G3。
