# R22A — gfx1151 (Radeon 8060S) 官方 DEV 候选跨架构验收报告

- 任务：R22A（Windows Radeon 8060S / gfx1151 跨架构官方 DEV 候选验收）
- 日期：2026-11-16（UTC）
- 执行者角色：Principal Validation Engineer / 独立 Release Quality Reviewer
- 最终判定：**`R22A_GFX1151_DEV_CANDIDATE_PASS`**，且共享快照与 gfx1100 完全一致 ⇒
  **`R22_DEV_DUAL_ARCH_VALIDATED`**（项目内部 DEV 级判定；**不是** OFFICIAL_STABLE_PASS，
  **不是** R23_RELEASE_READY）
- 证据目录：`evidence/raw/r22a-gfx1151/`（46 个文件 + SHA256SUMS.txt）、
  `windows-golden-path/reports/r22a-gfx1151/`

## A. Git 状态

| 项 | 值 |
|---|---|
| 集成分支（base） | `work/windows-rocm-training-release-closure` @ `58b475a17b67…`（R21.1 merge，PR #15；fetch 时即为 live HEAD，无更新工作被覆盖） |
| R22A 分支 | `feature/r22a-gfx1151-dev-acceptance`（自 58b475a 创建） |
| 提交树 | CPU contract（45 tests）、RCA verifier（575/0）、verifier 自测（12/12）全部在干净树 `58b475a` 上运行 |
| PR | 见 PR 链接（目标：集成分支；不合并 main、不 force-push） |

## B. 主机

| 项 | 值 |
|---|---|
| OS | Windows 11 25H2，build 26200.9974 |
| GPU | AMD Radeon(TM) 8060S Graphics（Ryzen AI MAX+ 395 APU）；`torch.cuda.get_device_properties(0).gcnArchName == "gfx1151"`（独立架构来源，非手写标签） |
| 驱动 | 32.0.22032.6002（2025-12-15） |
| 内存/磁盘 | 123.6 GB RAM（开始时空闲 91.9 GB）；C: 空闲 236 GB |
| Python | 3.12.16（隔离 conda env `r22a_py312`，仅用于创建 venv；未动系统 Python） |
| 运行栈 | torch `2.15.0+gitf6cd88cb.devrocm10.3.0.dev0-ff576965…`（cp312）、torchvision `0.29.2+gitb2281111…`、HIP `7.18.26441`、Ultralytics `8.4.214`（PyPI 正式分发） |
| 环境健康 | 有界探测全 PASS：FP32/FP16 GEMM 有限且正确、同步干净、子进程退出 0；无 HIPRTC/MIOPEN/VCTOOLS/INCLUDE 覆盖；开始时已运行 12h（2026-11-15 晚重启后） |
| 遗留进程 | 2 个 P19B 会话遗留 python 进程（`p1_amp_audit.py`，已知 HIP-teardown 挂起模式）；按任务规则未杀他人进程，实测不阻塞新 GPU 工作 |

## C. 官方 DEV 包溯源

- 通道：`https://dev.repo.amd.com/rocm/whl-next/`（dev），TheRock 快照 `ff5769655eeb1b91a46bce9edc16d87ca0efe7b6`（amd-compiler-2026-11-5-COT）
- 46 个 wheel 全量锁定（`R22A_GFX1151_PACKAGE_LOCK.json`，逐个 SHA256）；gfx1151 专属：`amd-torch-device-gfx1151`、`amd-torchvision-device-gfx1151`、`rocm-sdk-device-gfx1151`（版本串与 gfx1100 对应包完全一致，仅架构名不同）
- 与 gfx1100 冻结 lock 对比（`R22A_GFX1100_VS_GFX1151_LOCK_DIFF.json`）：43 个共享包版本+SHA256 **全部一致**（含 torch、torchvision、rocm-sdk-core、rocm-sdk-libraries、rocm-bootstrap）；依赖差异 0；`SHARED_PACKAGES_IDENTICAL` ✓
- `rocm-sdk-libraries` wheel SHA256 `dac27df5…` 与 gfx1100 **byte-identical**；内嵌 MIOpen.dll SHA256 `47a2e32c…`，版本串 `3.6.3.4e7d93e3`，`miopen_initializer_list` 标记 2（仅筛选信号）
- 溯源链（实时 API，非日期推断）：TheRock `ff576965` git-tree → 子模块 `rocm-libraries @ 4e7d93e34d35…`；GitHub compare `f0a5d266...4e7d93e3` → status ahead、ahead_by 604、**behind_by 0**（修复为祖先）⇒ `PROVENANCE_COMPLETE`
- G0 运行时核验：实际加载的 MIOpen.dll SHA256 == 内嵌 == lock；无 shim、无 VCTOOLS 覆盖、无二进制替换、无 PYTHONPATH 注入 ⇒ `OFFICIAL_CANDIDATE`

## D. G0–G5 结果（attempt 2，全部 PASS）

| 门 | 命令/内容 | 结果 |
|---|---|---|
| G0 | `verify_provenance.py --lock … --ancestry-evidence r22a_channel_binary_audit_gfx1151.json` | PASS：`ANCESTRY_VERIFIED`（behind_by=0）、lock↔installed 完全一致 |
| G2 | torch/torchvision 9 项 GPU 门（FP32/FP16、autograd、Conv2d、BN、`torchvision.ops.nms`、同步、退出） | PASS（无 CPU 回退） |
| G1 | #13437 回归：`nn.BatchNorm2d(100)`，形状 (20,100,35,45)，无宿主 STL（VCToolsInstallDir→空目录、INCLUDE=""、全新 USERPROFILE 冷缓存） | **PASS：`OFFICIAL_CANDIDATE_PASS`**（前向/反向有限、同步干净） |
| G3 | **精确命令** `yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1`（零非默认参数，隔离进程） | PASS：exit 0，device=-1 选中 CUDA:0 = Radeon 8060S，AMP check PASSED，epoch+val 完成，losses 有限，best.pt `c29d42c9…` / last.pt `90e26543…` 落盘并哈希 |
| G4 | 复用 R21.1 optimizer 审计（coco128） | PASS：AMP 真实启用（amp_resolved=True，GradScaler 逐步历史 184 步 2048→256、3 次 backoff 逐点计数）；**184 步全有限，359/366 可训练张量变化**（max |Δ|=0.282，mean 0.038）；checkpoint 保存 |
| G5 | R21.1 resume 生命周期（多 epoch 训练→受控中断→新进程 resume=True→续跑完成→第三进程 best.pt GPU 推理） | PASS：epoch 连续性验证，resume=True 真语义（非 weights-only），3 进程日志全存 |

**attempt-1 披露（首败保留）**：第 1 次编排 G0/G2/G1 PASS 后 G3 以 exit=1 停 NO-GO。根因：**本方环境预置缺陷**——为规避 GitHub 网络不稳而在 settings.json 设置了 `runs_dir` 覆盖，使 checkpoint 落到 cache 目录而非 gate 扫描的一次性 workdir（训练本身 exit 0、mAP50 0.941、checkpoint 已保存）。非栈缺陷、非 harness 缺陷。修正（移除 `runs_dir`，恢复 SettingsManager 默认 cwd-relative 行为）后 attempt 2 全绿。首败证据完整归档于 `attempt1_g3_first_failure/`，未删除、未替换。

## E. G8 可靠性（`R22A_RELIABILITY.json`）

- **冷缓存 10/10 PASS**（独立进程 + 每 run 独立全新 USERPROFILE 缓存身份；单次 115.9–135.6 s；`anomaly_tally` 为空——无 HIP_KERNEL_IMAGE_FAILURE / MIOPEN_HIPRTC_COMPILATION / MIOPEN_RUNTIME_KERNEL / MIOPEN_SOLVER_ANOMALY / CK 符号缺失 / torchvision wheel 缺失）
- **暖缓存补充 3/3 PASS**（单次 29.5–32.6 s；单独报告，不计入冷样本）
- 已知非致命平台现象（如实披露）：child 日志中存在 `MIOpen: Error [EvaluateInvokers] … Invalid elapsed time (elapsed <= 0)` 消息（P19B 已记录的本机 MIOpen 现象），所有 run 均 exit 0 完成，未命中任何异常签名分类
- 无 9 PASS+1 FAIL→重跑凑数情形：冷 10 run 一次通过

## F. 跨架构对比

见 `windows-golden-path/reports/r22a-gfx1151/R22A_DUAL_ARCH_COMPARISON.md` 与
`R22A_DUAL_ARCH_MATRIX.json`。结论：共享快照 byte-identical + 双架构全门 PASS ⇒
**`R22_DEV_DUAL_ARCH_VALIDATED`**。APU vs dGPU 不做性能对比（任务 §14 禁止无对照设计的性能断言）。

## G. 证据与可复现性

- 原始日志、逐 gate JSON（含内嵌断言）、命令、退出码、wheel/DLL/checkpoint SHA256、缓存身份：`evidence/raw/r22a-gfx1151/`
- 汇总报告：`windows-golden-path/reports/r22a-gfx1151/report.json`（generate_report full，含 false-PASS 防护）+ `gate_status.json`（overall GO）
- `evidence/manifest.json` append-only 追加（196 条）；`SHA256SUMS.txt` 覆盖 46 个证据文件
- 复验：CPU contract 46/46（含新增回归测试）、RCA verifier 575/0、verifier 自测 12/12（提交树）；PR HEAD 复核见最终评审节
- 未提交任何 wheel 二进制或 .pt checkpoint

**独立复核发现的 harness 缺陷与最小修复（披露）**：复核重算时发现 G3 记录的 `gpu_name` 被截断为
`AMD Radeon(TM`、`gfx_target=unknown` — `generate_report.py` 训练日志解析正则 `[^,)]+` 在 GPU 名内嵌
括号（"(TM)"）处提前终止。原始日志（已归档 `gpD_train_stdout.log`）一直包含完整行
`CUDA:0 (AMD Radeon(TM) 8060S Graphics, 101293MiB)`；其余 6 个 gate 记录身份字段均正确。修复：正则改为
锚定尾部 `, NNNNMiB)`（旧模式保留为无内存后缀日志的回退）；新增 CPU 回归测试
`test_gpu_name_with_parens_not_truncated`；G3 摘要与 full report 由**未改变的归档原始日志字节**确定性
再生成（orchestrator 原始输出原样保留于 `reports/gp-20261116-093332/`）。训练未重跑。

## H. 发布边界

- gfx1100 与 gfx1151 均达 **DEV_CANDIDATE_PASS**（dev 通道）；Stable 仍 **BLOCKED_OFFICIAL_ARTIFACT**（stable 通道无修复后 wheel，沿用 P14/P16 审计结论）
- G9：本机分类 **`HOST_REUSE_FRESH_VENV`**（曾用于 P17–P19B 测试；新 venv ≠ 干净 OS；不做 CLEAN_WINDOWS_INSTALL 断言）
- R23：仍按 R21 报告的边界执行（Stable 工件 + 跨架构 Stable 验收 + 干净 Windows 独立验证后才能发布）

## I. 后续任务

1. 向 AMD #15862 更新双架构 DEV 证据（待 owner 批准后发布）
2. 等待 stable 通道出现含 f0a5d266 的 wheel → R22 Stable 验收
3. Stable 跨架构（gfx1100+gfx1151）验收
4. 干净 Windows 独立主机验证（G9 → CLEAN_WINDOWS_INSTALL）
5. R23 开发者文档发布
