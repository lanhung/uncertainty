# AGENTS v0.2.x 规范分卷：计算资源、统计与物理验证

> 本文件是根级 `AGENTS.md` 的规范性组成部分。冲突时以根级文件为准。  
> 覆盖范围：共享 Vultr 控制宿主机、AutoDL/CPU/GPU、存储与备份、成本账本、统计/物理/计算验收。

---

## 8. Vultr 控制面、AutoDL、CPU/GPU 与存储资源计划

### 8.1 资源模型：1 个共享控制宿主机 + 0–2 个常规按需 AutoDL worker

项目需要控制、模拟、训练/验证三类逻辑角色，但不是三台常驻 Vultr，也不是三张 GPU 永久在线。

#### Control Host — 共享 Vultr，常驻但轻量

用途：

- 同时运行多个项目的 Codex 进程；
- 为每个项目运行隔离的 status server、SQLite ledger、dashboard 和 Git 快照；
- 执行 plan reconcile、轻量 smoke test 和运维诊断。

本项目实例必须使用独立的：

```text
research-ops-uncertainty.service
/etc/research-ops/uncertainty.env
/var/lib/research-ops/uncertainty/
/root/uncertainty-status/
port 8787（或负责人登记的替代端口）
```

控制宿主机不承担 production solver、训练、大型 MCMC 或 SBC。其配置按稳定性、磁盘和网络选择，通常 2–4 vCPU、4–8GB RAM 即可起步；若多个 Codex 并发明显占用内存，再单独扩容。控制宿主机成本是多个项目共享的，不计入本项目 GPU-card-hours。

#### Node S — `uncertainty-sim-autodl-*`，按需 AutoDL

用途：solver 编译、Fisher、Jacobian、数据生成、rate GP posterior 传播和 CPU 多进程。

选择优先级：

- 16–32 vCPU，优先 32；
- 64–128GB RAM；
- 200GB 以上本地 SSD；
- FP64 行为和实际 solver throughput；
- 按 vCPU/RAM/SSD 与单价排序，不按 GPU 峰值排序。

AutoDL 平台可能因资源绑定附带 GPU；这不意味着 solver 本身是 GPU 工作负载。若有校内 HPC 或更便宜的纯 CPU 资源，可替代或补充 Node S，但必须继续向同一 Vultr ledger 报告。

#### Node T — `uncertainty-train-autodl-*`，按需 AutoDL

起步建议：

- 1 × RTX 4090/4090D 24GB；
- 8–16 vCPU；
- 64GB RAM；
- 200GB 本地 SSD；
- 用于 emulator、flow、ensemble、active-learning surrogate、一般 MCMC 和部分 SBC。

Node T 只在训练、推断或验证队列存在时开启；任务和产物安全落盘后立即关机。

#### Node V — `uncertainty-verify-autodl-*`，验证窗口临时增加

- 默认 1 × RTX 4090；
- 独立验证、SBC、重复训练、challenge set；
- LINX/JAX float64、HMC/NUTS 或显存受限时改用 1 × A100 40/80GB；
- 只在必须保持环境/人员/attempt 独立的验证窗口开启，完成即释放。

#### 明确结论

- 空闲状态：只有共享 Vultr 控制实例，AutoDL GPU 数可以为 0；
- 常规科研窗口：1 台 sim AutoDL + 1 台 train AutoDL，通常 2 台机器、最多 2 张平台附带/实际使用的卡；
- 预算紧张或早期阶段：可只开 1 台 AutoDL，串行承担 sim 与 train，但不得据此声称独立验证；
- 稳妥验证峰值：再临时增加 1 台 verify AutoDL，即 3 台 AutoDL worker；
- 当前不租 8 卡节点；
- 多卡 DDP 不是项目默认瓶颈，优先独立任务、CPU 并行、合适单卡和按需启停。

### 8.2 Gate 后峰值扩展

只有 `FISHER-GATE >= G1` 且 Pilot 显示收益时，临时扩展到：

- 4–6 台 AutoDL/HPC worker；
- 其中 2–4 台偏 CPU-rich 数据节点；
- 1–2 台训练/多 seed；
- 1 台独立验证；
- 任务完成、checkpoint/manifest 同步并更新 ledger 后立即释放。

共享 Vultr 控制宿主机不随 worker 数线性扩容；只有 dashboard/API/SQLite 的实测负载成为瓶颈时才升级。

### 8.3 A100 使用条件

A100 不是默认卡，只在 profiling 证明后使用：

- 4090 FP64 对 JAX/LINX stiff ODE 或 NUTS 明显受限；
- 单模型或 batch 超过 24GB；
- A100 减少总成本而非仅单次更快；
- NVLink/多卡通信确实成为瓶颈。

每次使用需在 `docs/compute/ADR-A100-*.md` 记录前后 benchmark。

### 8.4 资源预算

#### 前 30 天

- 共享 Vultr 控制实例常驻，但按多项目摊销；
- AutoDL worker 在任务窗口按量开启，不预付整月常驻；
- 通常同时 1–2 台 AutoDL；第 3 台只在独立验证时开启；
- GPU 预算：约 `100–250 card-hours`，是使用上限区间而非必须耗尽；
- CPU 预算：由 solver benchmark 决定；
- 不允许 production 级百万点生成。

#### 完整项目工作区间

当前规划而非预先购买：

- 4090 等效 GPU：`600–1,500 card-hours`；
- 未经新 ADR 的硬上限：`2,200 card-hours`；
- A100：`50–200 card-hours`，仅 float64/HMC/大模型阶段；
- CPU-core-hours 按实际 solver time 单独统计；
- Vultr 控制成本单列为 shared control overhead，不得混入 GPU 加速比。

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
- solver/network 分别吞吐；
- AutoDL 实例类型、实际开机时长和总费用。

数据规模只能沿 learning curve 扩展，不预设 1M。

### 8.6 存储与备份

- 代码、配置和小型报告：GitHub；
- Vultr ledger：`/var/lib/research-ops/uncertainty`，定期备份；
- AutoDL 重要 manifests/checkpoints/outbox/artifacts：`/root/autodl-fs/uncertainty`；
- AutoDL 高 I/O 数据：运行时复制到 `/root/autodl-tmp/uncertainty`；
- 临时盘和 AutoDL 本地盘无冗余，不得作为唯一副本；
- 每个 shard 完成即 checksum；
- 关机/释放前同步并运行 backup/checkpoint 检查；
- 使用 Zarr/Parquet/HDF5，禁止百万小文件。

建议：

- AutoDL 共享可靠存储 100–300GB 起步；
- 每个活跃 worker 本地盘 200GB 以上；
- Vultr 只保存 ledger、控制日志、小型快照与必要备份，不作为科学数据湖；
- production 前根据 Pilot 实测更新。

### 8.7 AutoDL 运行规范

- AutoDL worker 是按需、可替换节点；控制状态不依赖其存活；
- 调试可用无卡模式，但注意其 CPU/RAM 很低；
- 所有 production 使用 CLI + config；
- 每 15–30 分钟 checkpoint；
- job 写 heartbeat；
- OOM、NaN、solver crash 结构化记录并有限重试；
- 训练/生成完成并安全同步后关机；
- notebook 不启动无人值守任务；
- 使用短生命周期 worker 时优先采用 tagged ephemeral Tailscale auth key；
- 若 `/dev/net/tun` 不可用，使用已测试的 Tailscale userspace 模式；
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
