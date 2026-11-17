# R22A.5N.1 最终报告 — 物理证据再验证、锁来源关闭与独立验收（2026-11-17）

## A. 执行判定（Executive Verdict）

**最终判定：`R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS`**（任务书 §13 允许的最高判定）。

依据：加固版验收引擎（`scripts/r22a5n1/nightly_acceptance.py`）对**全部新增物理证据包 B** 独立重算，
PKG / LK / G0 / G1 / G2 / G3 / G4 / G5 / G7 九个 gate 全部 PASS；判定的每一项都来自
原始字节（lock/DLL/wheel SHA、逐事件序列、进程树、原始日志），而非任何存储的汇总布尔值。
原始 R22A.5N 证据（pack A）逐字节保全，其原始判定 `R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS`
经历史引擎复跑仍可复现 —— 本任务把它的两处真实缺陷（P0-A 锁误绑定、P0-B 原始日志缺失）
定位、修复并以新物理实验关闭，而非重写历史。

## B. 精确 Git 与 PR 状态

| 项 | 值 |
|---|---|
| 起点 HEAD | `9713eec1bf8987a50916e0afd3d982ac068400c3`（R22A.5N，Draft PR #22 头） |
| 集成基线 | `ff52f87393d66f5773e95b70c1721550d8065b0b`（PR #21 合并后的 integration HEAD） |
| 证据+引擎提交 | `cb0181c` |
| CI 工作流修复提交 | `d613e39` |
| 最终 PR HEAD | 本报告所在文档提交（前向提交，无 force-push；本地=远端 SHA 已核） |
| CI | exact-HEAD `workflow_dispatch`（cpu-contract.yml：compileall×3 + 311 pytest + 22 closure）——运行号记录于 PR 描述 |
| PR 状态 | #22 保持 **Draft**，目标分支不变，等待 owner 审阅；未合并 |
| 工作树 | 干净（除两个预先存在且已披露的未跟踪遗留文件） |

## C. 历史证据和解（每处差异 → 根因 → 处置）

| # | 差异 | 根因 | 处置 |
|---|---|---|---|
| 1 | `adamw_amp.json` / `workers8_amp.json` / `workers8_amp_v2.json` 记录 `wheel_lock_sha256=97a2da63…`（DEV 锁），而运行时是 nightly | `audit_adamw_amp.py` 第 54 行硬编码 DEV 锁并无条件哈希；`--channel` 只影响 runtime 分类 | 判定为**收据归因损坏而非运行时错误**（同收据内 torch 2.16.0a0+rocm10.3.0a20261116 与 DLL `f9312c3e…` 证明运行时确为 nightly）。修复=`--wheel-lock` fail-closed 绑定（v1 版 lock gate）；引擎新增 LK gate 重哈希重绑定；pack A 三份收据原样保全，演示重算见 `pack_a_reconciliation.json`（SHA_MISMATCH×3 被正确捕获） |
| 2 | 5 份被收据引用的原始日志（adamw_amp.log、workers8_amp.log/v2.log、torchvision_ops.log、lifecycle_summary.log）不存在于任何位置 | 仪器从不自己写这些文件（`raw_log_path` 指向调用方重定向，未提交后遗失） | `ORIGINAL_LOG_NOT_RECOVERABLE` 如实申报；全部以新物理运行 + 执行信封（`run_envelope.py` 运行期捕获 stdout/stderr/PID/env/git/lock）重建对应 gate 证据 |
| 3 | G1 负向控制 v1 污染（DLL 借道 pm13437_merged） | 历史已知，pack A 已诚实记录 INCONCLUSIVE | 保留原文；v2（pm13437_official）+ 本次 Stage B 复测共同关闭 |
| 4 | G1 候选/控制 DLL 身份仅取自父进程 | `verify_miopen_nostl.py` 旧实现只记录 `miopen_identity_in_parent` | 新增**子进程内**身份上报（pre-op / **at-failure** / post-op 三时机）；pre-fix 子进程死在 BN 的 HIPRTC 编译里，at-failure 捕获拿到真实加载的 DLL `e97891df…`（marker=0） |
| 5 | 中途普查单点快照可能落入 epoch 间隙 | 旧 census 一次性采样 | 有界快照序列（全进程树、每张保留、取峰值），实测 16 个 spawn 子进程全部带 `spawn_main` 命令行 |

## D. 包身份与锁来源（Package Identity and Lock Provenance）

| 项 | 值 |
|---|---|
| 原始错误 DEV 锁 SHA（pack A 三收据） | `97a2da636a8264887e2f9f89443e43673967e6d8b50acb2b5003a626fe089533` |
| 正确 Nightly 锁 SHA（git blob，46 条记录） | `cf147540a166a623bcf4f7961e07540980af5e117c7a0cc1f2cf38c2b013a7ac` |
| 实际安装版本 | torch `2.16.0a0+rocm10.3.0a20261116`、torchvision `0.30.0a0+rocm10.3.0a20261116`、ultralytics `8.4.214`、rocm/sdk 全家 `10.3.0a20261116`（47 dists，pip check 无损坏依赖） |
| 安装前校验 | 46/46 缓存工件（45 wheel + 1 sdist）逐一 SHA256 对锁验证通过后才安装 |
| 加载 DLL（训练/G0/G1 候选/G2） | `f9312c3e…`（= 冻结审计的候选 DLL，marker=2） |
| pre-fix 控制 DLL（子进程 at-failure） | `e97891df…`（pm13437_official 自有，marker=0） |
| 新收据锁绑定字段 | `wheel_lock_path/sha256/channel/gfx/package_count + runtime_package_versions + provenance_gate_version`，且 LK gate 独立重算 |

## E. 物理 GPU 实验（次数、时间、资源）

共 **20 次信封包裹的物理尝试**（18 成功、1 次保留失败、1 次被分类器修复取代），
总 GPU 相关墙钟约 15 分钟；驱动 `32.0.22032.6002` 全程未变；每次尝试独立目录、独立 run 记录。
关键运行（全部在 `stage_logs/`，含完整命令、PID、UTC 起止、env 子集、git 脏状态）：

| 阶段 | 运行 | exit | 时长 |
|---|---|---|---|
| A 安装 | stage_a_install（130.7s）+ manifest | 0 | — |
| A 身份 | stage_a_g0 → G0_RUNTIME_IDENTITY_PASS | 0 | 23.9s |
| B 候选×3 轮 | 最终 cand5/cand6（含此前 cand1-4 仪器迭代保留） | 0 | ~22s×2 |
| B 控制 | ctrl3（v2；ctrl/ctrl2 为仪器迭代保留） | 0(脚本)/1(子进程,预期) | 7.1s |
| C G2 | 9/9 gates | 0 | 18.0s |
| C AMP | amp（失败，tloss dict 崩溃，保留）→ amp2 PASS | 1 / 0 | 27.4 / 36.6s |
| D 生命周期 | lifecycle（分类缺陷迭代保留）→ lifecycle2 PASS | 0 | 184.3 / 95.5s |
| E workers | workers8/b/c（普查迭代保留）→ c：16 spawn 工人 | 0 | ~72s×3 |

## F. no-STL 配对实验（正负对照分开报告）

**候选（nightly wheel，无任何 HIPRTC/STL 变通）×2 次独立冷试验**：
- 分类 `OFFICIAL_CANDIDATE_PASS`，exit 0；VCToolsInstallDir→空目录、INCLUDE="”、
  USERPROFILE→独立冷缓存 scratch（两次试验 PID/scratch 均不同）；
  前向/损失/反向有限；**子进程内**加载 DLL=`f9312c3e…`（marker=2）。
  BN 形状 = 历史失败形状 (20,100,35,45) BatchNorm2d(100)。

**负向对照（pm13437_official，官方 pre-fix 7.14.1 栈）**：
- 分类 `OFFICIAL_PRE_FIX_EXPECTED_FAIL`，exit 1，失败类 `MIOPEN_HIPRTC_COMPILATION`；
  原始日志含完整 #3956 签名（`'type_traits' file not found` + `HIPRTC_ERROR_COMPILATION`），
  引擎从**原始日志字节**重新分类一致；父进程 marker=0；**at-failure 子进程内 DLL=`e97891df…`**
  （其自有 pre-fix DLL，非候选 DLL——"换 DLL 冒充控制组"类篡改会被拒绝）。

**解读（如实限定）**：pre-fix 环境与 nightly 环境相差不止一个软件组件，本配对是
**强来源谱系 + 行为对照**，不是完美单变量干预；支持的是关于原始 HIPRTC/STL 失败的
窄结论：`NIGHTLY_NO_STL_REGRESSION_CONFIRMED`（不声称 Stable）。

## G. YOLO 与 AMP（Stage C 实测）

- 配置：YOLO26n（init 权重 SHA `9b09cc8b…`）、COCO128、`optimizer=auto`（框架自选 AdamW）、
  默认 AMP、device=-1、workers=0、3 epochs、imgsz 256、batch 8；resolved train args 全量入收据。
- **引擎从 per_step 事件独立重算**：11 次 scaler 尝试 / **7 次有效参数更新**（sentinel delta>0）/
  4 次 found_inf 溢出跳过；批索引单调；无"既非溢出又无更新"的异常步；溢出步参数零位移；
  有效步梯度全有限；scale 序列 65536→4096、4 次回退且每次 inf 跳过后必随回退 ——
  与收据存储计数完全吻合（**11/7/4 是重算结果，不是硬编码**；pack A 历史序列经同一重算亦吻合）。
- 低精度证据：stem conv 输出 dtype 直方图 {float16:96}，autocast 采样 48/48 全启用；
  per-epoch 观测（损失/验证指标/mAP）随收据记录（e1 mAP50=0.483）。
- checkpoint：last.pt/best.pt SHA 入收据；训练后模型 366 参数张量变化（>1e-9）且全有限。

## H. Checkpoint 与 Resume（Stage D，v2 深度状态取证）

- 真实中断：epoch 1 检查点安全落盘（rows=2、kill 时 SHA `1fb0e51a…`）后仅终止自有训练进程
  （TerminateProcess）；新独立进程 `resume=True`。
- **恢复证据（实测而非声称）**：optimizer 状态字典 **366 项**载入（新优化器应为空）；
  resume 起点 epoch 1；resume 后 **8/8 步全部有效更新**；epoch 连续性由数值行重算
  （rows 2→5、末行 epoch=4）；第三进程 best.pt 推理 INFER_OK。
- **状态序列化类别（本次新发现，观测键集直接分类）**：
  - 已序列化：model 权重（训练中存于 `ema` 键，最终存于 `model` 键）、optimizer、
    **GradScaler（`scaler` 键）**、epoch、best_fitness、train_args、ema、updates；
  - `NOT_SERIALIZED_BY_UPSTREAM`：**LR scheduler**（8.4.214 的 save_model 不写入，
    resume 时由 train_args 重建）——如实报告其对 resume 语义的影响，不计入"已恢复"。
- 判定：核心 `RESUME` 通过且状态深度如实（G5 PASS；`FULL_TRAINING_STATE_RESTORE_PASS`
  语义按上游实际行为界定，scheduler 缺失明确披露）；last.pt/best.pt 字节随 pack 提交，
  与信封工件哈希锚定（篡改收据 SHA 会被 G5 拒绝）。

## I. 证据完整性（原始证据逐项可及性）

- pack B：106 条 SHA256MANIFEST（raw=105 / derived=1），`evidence_pack verify` 0 问题；
  每次尝试的原始 stdout/stderr 字节、命令、PID、UTC 时间戳、净化 env、git 身份、锁 SHA、
  事后工件哈希全部在库；失败尝试保留。
- pack A：29/29 原始清单在干净克隆中重哈希一致；新增 `raw_host_recovery/` 21 件
  （g5 stage1/3/4 日志与脚本、g0 子进程日志×2、三份 leg 日志、四组 args.yaml/results.csv），
  其中三份 leg 日志与既有提交副本**字节一致**（互证）；原始清单未被改写。
- 大文件：pack A 权重（8×5.5MB）保留在宿主机并全部 SHA 盘点（不声称可从 PR 独立字节验证）；
  pack B 生命周期 last.pt/best.pt（11MB）**已入库**供独立验证。
- 宿主机保留：`C:\r22a5n1\`（venv+scratch，冷缓存证据）、原 `C:\r22a5n\` 未动。

## J. 对抗审计（25 类伪造全部执行化测试）

`windows-golden-path/tests/test_r22a5n1_cpu.py`（45 项，全部 CPU 确定性）：
DEV 锁替换/伪造 rules_checked/改版本/改 wheel SHA/改 DLL SHA/ancestry behind_by>0/DEV 冒充
nightly/删日志/改日志字节/零更新伪造 PASS/溢出改有效/sentinel 清零/Scaler 转移不匹配/
FP32 冒充 AMP/换 GPU 身份/复用 run ID/改 checkpoint SHA/缺优化器状态声称恢复/伪造 epoch
连续性/无工人证据声称 workers=8/伪造孤儿清洁/删负对照/控制组换修复版 DLL/注入
HIPRTC shim 却称无变通/nightly 判定改 Stable —— **全部被拒绝或按合同判 INCONCLUSIVE**，
并附 pack A 真实 P0-A 值的 LK 检测回归测试。测试是执行出来的（pytest），不是断言声明。

## K. 最终 GO/NO-GO 矩阵（任务书 §13 逐项）

| 条件 | 来源证据 | 状态 |
|---|---|---|
| 原始 R22A.5N 证据逐字节保全 | clone 重哈希 29/29 | ✅ |
| 原始 DEV 锁误绑定独立诊断 | gap matrix + reconciliation + LK 演示 | ✅ |
| 新 Nightly 锁身份正确捕获 | pack B 收据 cf147540 + LK 重算 | ✅ |
| 实际安装 = Nightly 锁 | 46/46 预装校验 + PKG 双向 diff | ✅ |
| GPU 实际加载 DLL = 候选 | G0/G1/G2/G3 收据 + 子进程内证据 | ✅ |
| 全部新物理运行原始日志保全 | 20 信封尝试 + 106 条 manifest | ✅ |
| 关键缺失原始日志恢复或真实重跑 | 21 件恢复 + 5 缺失→A-E 重跑 | ✅ |
| G1 正负对照各自通过合同 | F 节 | ✅ |
| no-STL 隔离与缓存身份有观测支撑 | scratch/PID/DLL 三重 | ✅ |
| AdamW 有效更新由逐事件重算 | G 节 11/7/4 | ✅ |
| AMP dtype 与 GradScaler 决策独立检查 | dtype 直方图 + 回退一致性 | ✅ |
| YOLO 训练/验证为真实 GPU 执行 | per-step + per-epoch + DLL + 收据 | ✅ |
| Checkpoint 保存/重载/resume 物理确认 | H 节 | ✅ |
| 严格恢复声明受支撑或明确限定 | scheduler NOT_SERIALIZED 如实 | ✅ |
| Workers 证据归属真实进程树 | 全树普查 + 祖先链 | ✅ |
| 每份必需证据文件有有效 SHA256 | 两包 manifest verify | ✅ |
| 全部伪造测试拒绝篡改证据 | J 节 | ✅ |
| 独立干净克隆验证通过 | 5/5 | ✅ |
| 既有 CPU 回归保持绿 | 311 passed（266 基线全在） | ✅ |
| 最终 PR HEAD CI 通过 | workflow_dispatch @ 文档提交（URL 在 PR 描述） | ✅ |
| 无未授权系统修改 | 驱动/系统 DLL/全局工具链零改动 | ✅ |
| 未声称 Stable/双架构/G9 干净安装 | 判定封顶 AUDITED_PASS | ✅ |

## L. 剩余风险（分实阻塞性）

- **实际阻塞（针对 Stable 发布，非本任务）**：stable 通道仍是 OFFICIAL_PRE_FIX
  （10.1.0 wheel 字节级 pre-fix 复核于 R22A.5A/P16）；#14 外部测试者邀请 0 回复；
  #15862 无进展。
- **非阻塞限制**：ancestry 为外部记录的 gh 事实（引擎做一致性检查，不离线重算
  —— 承重证据是 wheel/DLL 字节，可独立验证）；pack A 权重在宿主机（已盘点）；
  单 GPU 单夜测（nightly 通道每日滚动，固定候选=20261116）。
- **顺延工作**：gfx1100 nightly 资格验证；R22A.5B（修复版 stable wheel 发布后的
  stable 物理验收）；G9 干净安装验收。

## M. AMD Release Engineering 交接摘要（致 Scott Todd，未发送）

Merged MIOpen PR #13437（`f0a5d266`）已在**官方 nightly 通道**物理证实交付：
`rocm_sdk_libraries-10.3.0a20261116`（wheel SHA `b11baad9…`，MIOpen.dll `f9312c3e…`，
构建 `25f28906`，f0a5d266→25f28906 ahead 1074/behind 0）。Windows gfx1151 上，
无任何 MSVC STL/HIPRTC 变通时 BatchNorm #3956 失败已消除（配对 pre-fix 对照复现原失败）；
YOLO26n 原生训练/AMP/验证/断点续训/8-worker 全部真机通过，且全部证据可由
第三方从字节哈希独立重算（含 46 包锁绑定与 25 类伪造测试全部拒绝）。
两个遗留发布质量问题：①Windows wheel 安装路径过长（MAX_PATH，需短路径 venv）；
②`rocm` sdist 离线构建依赖（pip 构建隔离会去 PyPI 拉 build deps）。
建议：将含修复的 libraries wheel 推入 stable 通道（R22A.5B 合同已就绪）。

## N. 下一任务建议

1. **gfx1100 Nightly 资格验证** — 复用本任务引擎与信封（nightly 已列 gfx1100 device wheels）。
2. **R22A.5B Stable 物理验收** — 触发条件：stable 通道出现 post-fix wheel；
   5 步流水线见 R22A5A_PACKAGE_COMPATIBILITY_MATRIX §5。
3. **G9 干净 Windows 验收** — 仍 BLOCKED_RELEASE（依赖 stable 修复）。
4. **独立外部测试** — #14 邀请仍开放；本任务的第三方可复核性已达到无需原环境的标准。
