# AGENTS v0.2.x 规范分卷：计算资源、统计与物理验证

> 本文件是根级 `AGENTS.md` 的规范性组成部分。冲突时以根级文件为准。  
> 覆盖范围：共享 Vultr 控制宿主机、跨项目共享 AutoDL/CPU/GPU、存储与备份、成本账本、统计/物理/计算验收。

---

## 8. Vultr 控制面、弹性 AutoDL、CPU/GPU 与存储资源计划

### 8.1 资源模型：1 个共享控制宿主机 + 0–2 个本项目 lease 的现有 AutoDL worker

项目需要控制、模拟、训练和验证等逻辑角色，但这些角色不是永久绑定的物理机器。

#### Control Host — 共享 Vultr，常驻但轻量

用途：

- 同时运行多个项目的 Codex 进程；
- 为每个项目运行隔离的 status server、SQLite ledger、dashboard 和 Git 快照；
- 执行 plan reconcile、轻量 smoke test、代码审阅和运维诊断。

本项目实例必须使用独立的：

```text
research-ops-uncertainty.service
/etc/research-ops/uncertainty.env
/var/lib/research-ops/uncertainty/
/root/uncertainty-status/
port 8787（或负责人登记的替代端口）
```

控制宿主机不承担 production solver、训练、大型 MCMC 或 SBC。其配置按稳定性、磁盘和网络选择，通常 2–4 vCPU、4–8GB RAM 可起步；多个 Codex 并发明显占用内存时再扩容。控制成本由多个项目摊销，不计入本项目 GPU-card-hours。

#### Existing AutoDL Pool — 两台跨项目共享、按量计费、可关机的物理 worker

当前可用的两台 AutoDL 规格相近，属于：

- 约 25 vCPU；
- 约 92GB RAM；
- 单张 48GB vGPU；
- 本地系统/数据盘与地区文件存储；
- 按小时计费；
- 可能同时服务其他项目。

上述是资源级别描述，不得把“48GB vGPU”直接等同于 4090、A100 或某个固定 FP64 性能。每台节点必须由 `scripts/capture_worker_inventory.py` 和实际 solver/training benchmark 记录真实 GPU 名称、驱动、compute capability、PyTorch/CUDA 兼容性、FP64 行为和吞吐。

两台物理 worker 的默认名称应按地区/实例稳定标识，例如 `autodl-westb-01` 与 `autodl-bjb1-01`，而不是永久命名为 sim/train。

#### 逻辑工作负载角色

任一空闲物理 worker 可以在某个任务 attempt 中承担：

- `solver`：solver 编译、Jacobian、Fisher、数据生成、rate posterior 传播和 CPU 多进程；
- `train`：emulator、flow、ensemble、active-learning surrogate；
- `verify`：独立 MCMC、SBC、重复训练、challenge set、direct recovery；
- `elastic`：尚未指定，由任务、benchmark 与资源 lease 决定。

角色切换必须登记在 ledger message、run manifest 和成本账本中。不能因为同一台机器先后运行 train 和 verify 就宣称物理或软件环境独立。

#### 明确结论

- 空闲状态：只有共享 Vultr 控制实例；本项目 AutoDL 使用数为 0；
- 普通窗口：从两台现有 AutoDL 中 lease 1 台；
- 并行窗口：两台都空闲时，本项目可同时 lease 2 台并动态分配角色；
- 若任一节点正在服务其他项目，本项目不得把它计为可用；
- 独立验证需要独立 environment/attempt/artifact lineage；必要时临时增加第三台 AutoDL，而不是假装共享节点上的同一环境独立；
- 当前不租 8 卡节点；
- 多卡 DDP 不是默认瓶颈，优先独立任务、CPU 并行、合适单卡和按需启停。

### 8.2 跨项目资源 lease

research-ops ledger 跟踪本项目 task state；物理节点 lease 防止不同项目抢占同一资源。两者必须同时成立。

默认 host-level lease：

```text
gpu0       单张 GPU 独占
cpu-heavy  占用大部分 CPU 的 solver/MCMC
io-heavy   占用大部分本地盘吞吐的数据任务
```

规则：

- GPU production 默认独占 `gpu0`；未经 profiling 不允许两个项目共享；
- 20+ 进程 solver farm 默认获取 `cpu-heavy`；
- 每个节点至少保留 2–3 vCPU 给系统、heartbeat、I/O 和诊断；
- lease 入口：`scripts/with_resource_lease.sh`；
- 退出码 75 表示资源被其他项目占用，禁止删除对方 metadata；
- 关机必须检查所有项目 lease，而不能只看 uncertainty dashboard。

### 8.3 Gate 后峰值扩展

只有 `FISHER-GATE >= G1` 且 Pilot 显示端到端收益时，才可在现有两台之外临时扩展：

- G1：通常不超过现有 1–2 台；
- G2：可临时增加 1–2 台偏 CPU-rich 数据节点或独立验证节点；
- G3/Nature campaign：总计 4–6 台 AutoDL/HPC worker 的短期峰值；
- 完成 checkpoint/manifest、成本登记和 ledger 更新后立即释放。

共享 Vultr 不随 worker 数线性扩容；只有 API/SQLite/Codex 的实测负载成为瓶颈时才升级。

### 8.4 A100/高 FP64 卡使用条件

当前 48GB vGPU 是默认已拥有池，但其真实底层 GPU 必须实测。A100 或其他高 FP64 卡只在 profiling 证明后临时租用：

- 当前 vGPU 对 JAX/LINX stiff ODE、float64 或 NUTS 明显受限；
- 单模型或 batch 超过 48GB/实际可用显存；
- 高 FP64 卡减少**总成本**而非只缩短单次运行；
- NVLink/多卡通信确实成为瓶颈。

每次升级需在 `docs/compute/ADR-A100-*.md` 记录当前 vGPU 与候选机器的端到端 benchmark。

### 8.5 资源与费用账本

#### 前 30 天

- 共享 Vultr 常驻，但按多项目摊销；
- 两台 AutoDL 均按任务窗口开启，不因“已经创建”而默认全时占用；
- 通常本项目同时 lease 1 台，明确并发收益时 lease 2 台；
- GPU/worker 预算先以 `100–250 device-hours` 为控制上限；
- CPU-core-hours、GPU-hours、节点开机小时与人民币费用分开统计；
- 不允许 production 级百万点生成。

#### 完整项目工作区间

当前规划而非预先购买：

- 现有 48GB vGPU/4090 等效 device-hours：`600–1,500`；
- 未经新 ADR 的硬上限：`2,200 device-hours`；
- 临时高 FP64/A100 类资源：`50–200 card-hours`；
- CPU-core-hours按实际 solver time 单独统计；
- Vultr 控制成本列为 shared control overhead；
- 节点小时按项目 lease 归属，不按物理机器名称归属。

每次 run manifest 至少记录：

```text
physical_node
provider_region
logical_role
lease_resource
started_at / ended_at
billed_hours
hourly_price_snapshot
cpu_core_hours
gpu_hours
solver_calls
accepted_labels
```

价格是运行时事实，必须进入本地/版本化成本账本，不在科研规范中永久写死。

### 8.6 Solver 数据生成公式

```text
T_wall = N_sim * t_sim / (N_worker * efficiency)
```

每个阶段必须报告：

- `t_sim` median/p90/p99；
- cold vs warm；
- 失败率与重试；
- CPU-core-hours per accepted label；
- I/O 占比；
- solver/network 分别吞吐；
- 物理节点、逻辑角色、lease 时长和实际费用；
- 其他项目干扰是否存在。

数据规模只能沿 learning curve 扩展，不预设 1M。

### 8.7 存储、跨地区与备份

- 代码、配置、小型报告、manifest 和 checksum：GitHub；
- Vultr ledger：`/var/lib/research-ops/uncertainty`，定期备份；
- AutoDL 项目持久目录：`/root/autodl-fs/projects/uncertainty`；
- AutoDL 项目高 I/O 目录：`/root/autodl-tmp/projects/uncertainty`；
- AutoDL host-level Tailscale：`/root/autodl-fs/_research-host/tailscale`；
- 本地数据盘无冗余，不得作为唯一副本；
- 每个 shard 完成即 checksum；
- 关机/释放前同步 checkpoint、manifest 和日志摘要；
- 使用 Zarr/Parquet/HDF5，禁止百万小文件。

两台 AutoDL 位于不同地区时，各自 `/root/autodl-fs` 不得被假定为共享。大规模跨地区数据使用批准的对象存储/rclone 数据层；Vultr 不作为大型科学数据中转仓库；默认不建立 worker-to-worker SSH 信任。

建议：

- 每地区 AutoDL 文件存储按实际数据量初始化；
- 不可再生 checkpoint 至少有一个地区持久副本和一个对象存储/外部备份；
- local scratch 只放可重建数据；
- production 前根据 Pilot 实测更新容量。

### 8.8 AutoDL 共享运行规范

- worker 是按需、可替换、跨项目共享节点；控制状态不依赖其存活；
- 一台物理节点只运行一份 host-level Tailscale；
- 每个项目 env 独立，默认不自动 source 到 `.bashrc`；
- 调试可用较小资源，但不得由低配结果推断 production 成本；
- 所有 production 使用 CLI + config；
- 每 15–30 分钟 checkpoint；
- job 写 heartbeat；
- OOM、NaN、solver crash 结构化记录并有限重试；
- notebook 不启动无人值守任务；
- 科学依赖不得全局 `pip install` 污染其他项目；
- 节点关机前运行 `scripts/autodl_node_status.sh` 并检查所有项目 lease；
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
