# AGENTS v0.2.0 规范分卷：计算资源、统计与物理验证

> 本文件是根级 `AGENTS.md` 的规范性组成部分。冲突时以根级文件为准。
> 覆盖范围：AutoDL/CPU/GPU、存储与备份、成本账本、统计/物理/计算验收。

---

## 8. AutoDL、CPU/GPU 与存储资源计划

### 8.1 当前立即启用：三类角色，2 台常驻，第 3 台按需

项目需要三个计算角色，但不要求三张 GPU 永久在线。

#### Node S — `uq-sim-01`，常驻

用途：solver 编译、Fisher、数据生成、rate GP posterior 传播、CPU 多进程。

AutoDL-only 建议：

- 1 张价格合适的 4090/4090D 或其他附带高 CPU/RAM 配额的卡；
- 16–32 vCPU，优先 32；
- 64–128GB RAM；
- 200GB 以上本地 SSD；
- 选择主机时按 vCPU/RAM/SSD 与单价排序，不按 GPU 峰值排序。

若有校内 HPC 或纯 CPU 云，solver farm 优先迁移到 CPU 资源，AutoDL GPU 不应仅作为购买 CPU 配额的长期昂贵方式。

#### Node T — `uq-train-01`，常驻

- 1 × RTX 4090 24GB；
- 8–16 vCPU；
- 64GB RAM；
- 200GB 本地 SSD；
- 用于 emulator、flow、ensemble、active-learning surrogate 和一般 MCMC。

#### Node V — `uq-verify-01`，按需

- 默认 1 × RTX 4090；
- 独立验证、SBC、重复训练、challenge set；
- LINX/JAX float64、HMC/NUTS 或显存受限时改用 1 × A100 40/80GB；
- 只在验证窗口开启，完成即关机。

**明确结论**：

- 默认常驻：2 台机器、2 张卡；
- 稳妥并发：3 台机器、3 张卡；
- 当前不租 8 卡节点；
- 多卡 DDP 不是项目瓶颈，优先多独立单卡任务与 CPU 并行。

### 8.2 Gate 后峰值扩展

只有 `FISHER-GATE >= G1` 且 Pilot 显示收益时，临时扩展到：

- 4–6 台单卡节点；
- 其中 2–4 台偏 CPU-rich 数据节点；
- 1–2 台训练/多 seed；
- 1 台独立验证；
- 任务结束立即释放。

### 8.3 A100 使用条件

A100 不是默认卡，只在 profiling 证明后使用：

- 4090 FP64 对 JAX/LINX stiff ODE 或 NUTS 明显受限；
- 单模型或 batch 超过 24GB；
- A100 减少总成本而非仅单次更快；
- NVLink/多卡通信确实成为瓶颈。

每次使用需在 `docs/compute/ADR-A100-*.md` 记录前后 benchmark。

### 8.4 资源预算

#### 前 30 天

- 2 张 4090 等效卡常驻/按量；
- 第 3 张卡按验证需要开启；
- GPU 预算：约 `100–250 card-hours`；
- CPU 预算：由 solver benchmark 决定；
- 不允许 production 级百万点生成。

#### 完整项目工作区间

当前规划而非预先购买：

- 4090 等效 GPU：`600–1,500 card-hours`；
- 未经新 ADR 的硬上限：`2,200 card-hours`；
- A100：`50–200 card-hours`，仅 float64/HMC/大模型阶段；
- CPU-core-hours 按实际 solver time 单独统计。

该预算包括开发、5 seeds、SBC、独立验证和最终推断，不代表必须耗尽。

### 8.5 Solver 数据生成公式

```text
T_wall = N_sim * t_sim / (N_worker * efficiency)
```

每个阶段必须报告：

- `t_sim` 的 median/p90/p99；
- cold vs warm；
- 失败率与重试；
- CPU-core-hours per accepted label；
- I/O 占比；
- solver/network 分别吞吐。

数据规模只能沿 learning curve 扩展，不预设 1M。

### 8.6 存储与备份

- 代码：GitHub；
- 重要 manifests/checkpoints：`/root/autodl-fs`；
- 高 I/O 数据：运行时复制到 `/root/autodl-tmp`；
- 本地盘无冗余，不得作为唯一副本；
- 每个 shard 完成即 checksum；
- 每日同步；
- 关机/释放前执行 `make backup-check`；
- 连续关机接近平台释放期限前确认实例状态；
- 使用 Zarr/Parquet/HDF5，禁止百万小文件。

建议：

- 共享可靠存储 100–300GB 起步；
- 每节点本地盘 200GB 以上；
- production 前根据 Pilot 实测更新。

### 8.7 AutoDL 运行规范

- 调试可用无卡模式，但注意其 CPU/RAM 很低；
- 所有 production 使用 CLI + config；
- 每 15–30 分钟 checkpoint；
- job 写 heartbeat；
- OOM、NaN、solver crash 结构化记录并有限重试；
- 训练完成自动关机；
- notebook 不启动无人值守任务；
- 维护：

```text
docs/compute/autodl_inventory.md
docs/compute/cost_ledger.csv
docs/compute/solver_throughput.csv
```

---

## 9. 统计、物理与计算验收阈值

### 9.1 后验收敛

- split `R-hat < 1.01`；
- bulk/tail ESS `>1000`；旗舰主参数建议 `>4000`；
- MCSE `<2%` posterior SD；旗舰主参数建议 `<1%`；
- nested evidence error 明确报告；
- 多峰后验验证 mode coverage；
- HMC divergence、BFMI、tree depth 报告；
- 不因达到最大步数自动视为收敛。

### 9.2 物理效应量

至少报告：

```text
normalized shift = (median_A - median_B) / pooled_posterior_sd
interval ratio
credible-volume ratio
region overlap
exclusion topology change
information gain
```

不得只报告 p-value、JS divergence 或图形目测。

### 9.3 物理稳健性

主结论必须通过：

- prior 宽度/形式；
- LBT、legacy、EMPRESS stress；
- D/H alternative；
- neutron N0–N3；
- solver/network；
- scalar/function rate；
- rate compilation；
- training seed；
- precision；
- OOD 策略；
- transition smoothness；
- fixed/free 参数合理组合。

### 9.4 Emulator 与 distribution calibration

- 点误差与观测误差归一化阈值见 V5；
- 68%/95% coverage 达标；
- conditional coverage 不被总体平均掩盖；
- posterior recovery `<0.1 sigma`；
- false-safe OOD `<10^-3`；
- 5 seeds；
- blind challenge 通过。

### 9.5 多 solver 条件

旗舰主结论至少满足：

- 两个独立 solver/network 同号同趋势；
- 主要 effect size 差异在预注册容忍区间；
- 若不一致，必须以 solver discrepancy 为结果本身，不能挑选一个；
- 选定点由第三路径或直接 PRIMAT/LINX 检查。

### 9.6 计算方法验收

NCS/NMI 路线需报告：

- equal-budget comparison；
- total cost including labels；
- solver calls to target accuracy；
- sample efficiency curve；
- calibration vs cost；
- scaling with nuisance dimension；
- scaling with number of solvers；
- cross-domain generalization；
- failure envelope。

### 9.7 盲化与多重比较

production 前冻结：

- 主数据；
- 主 prior；
- 主参数；
- 主统计量；
- 主 figure；
- discovery/route thresholds。

探索性扫描和 confirmatory analysis 分离。多重检验需报告 family 与 correction，或明确为 hypothesis generation。

---
