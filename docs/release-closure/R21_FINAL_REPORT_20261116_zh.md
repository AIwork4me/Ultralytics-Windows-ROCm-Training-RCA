# R21→R22→R23 最终执行报告（中文，2026-11-16）

**主机**：AMD Radeon RX 7900 XTX (gfx1100) · Windows 11 build 26300 · 驱动 32.0.21030.2001
**任务书**：R21 Windows Golden Path Harness → R22 官方 wheel 验收 → R23 开发者体验发布
**详细工程报告**：[R21_GOLDEN_PATH_HARNESS_REPORT.md](R21_GOLDEN_PATH_HARNESS_REPORT.md)（英文，同事实）

## A. Git 状态

- 分支 `feature/r21-windows-golden-path`，冻结基线 `e81a89e`（=远端 release-closure 分支当时 HEAD）
- 提交：`31526a1`（harness + 契约 + 测试 + 文档 + R22/R23 交付物）、`3021e70`（全部物理证据 + 报告，42 文件 +79k 行）、本报告提交
- PR：**[#15](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/pull/15)** → `work/windows-rocm-training-release-closure`，已推送、OPEN、未合并（可评审状态）
- 推送经 GitHub API 复核（SHA 一致）；verifier **575 checks / 0 violations**；evidence manifest 111→148 条；历史 P14–P19B 证据零改动

## B. R21 — Windows Golden Path Harness

**交付**：`windows-golden-path/` —— 单入口 `run-golden-path.ps1`（-Preflight/-EngineeringReference/-OfficialCandidate/-OfficialStable/-PrepareRelease 五模式，默认 Preflight，绝不默认安装或启动长 GPU 负载）+ 13 个门脚本 + G0–G9 机器可查验收契约（acceptance-contract.json）+ 兼容矩阵 + 哈希锁定 lockfile（requirements-lock/）+ 28 项 CPU 契约测试 + docs（架构/排错/发布清单/R22 runbook/R23 草案）。

**失效封闭分类已实现并实证**：检出任何 HIPRTC/MIOPEN/DLL 重定向 workaround → 强制 `ENGINEERING_REFERENCE`，官方结论永不签发。

**物理 gfx1100 实测（工程参照栈 = 官方 7.14.1 轮字节 + 已披露 HIPRTC shim + ultralytics 8.4.214 发布轮，隔离 venv `C:\RadeonYOLO\venvs\r21-engref`）**：

| 门 | 结果 | 证据 |
|---|---|---|
| A 溯源 | ENGINEERING_REFERENCE（shim 自动检出；官方 DLL sha `e97891df…`=3.5.2.cd957402，marker 0） | r21A_provenance.json |
| A2 GPU 门 | **9/9 PASS**（含 torchvision.ops.nms） | r21A2_torch_gates.json |
| D1 无STL·去shim | **OFFICIAL_PRE_FIX_EXPECTED_FAIL**（#3956 签名逐字复现，冷缓存） | r21D1_nostl_official.json |
| D2 无STL·shim | **ENGINEERING_REFERENCE_PASS**（同轮字节，唯一差异=shim） | r21D2_nostl_engref.json |
| E1 精确命令 | `yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1` **PASS exit 0**（GPU、AMP 通过、损失有限、val、last/best.pt 哈希） | r21E1_train_cli.json |
| E2 优化器 | **PASS**：183 步；361/366 参数张量变化（max |Δ| 0.295）；scaler 8192→128、5 次逐步回退；前向 autocast 192/192；缓冲区排除；补充性 harness 已声明 | r21E2_optimizer.json |
| E3 中断→续训 | **PASS**：检查点优化器状态预验证 → 新进程 resume=True（"Resuming" 日志）→ 训至末 epoch（csv epoch 列=8）→ 第三进程 best.pt GPU 推理 | r21E3_resume.json |
| F 稳定性 | **3/3 独立进程 PASS**，零异常家族 | r21F_stability.json |
| F 契约测试 | 28/28 PASS（合成 fixture 永不产生 PHYSICAL_GPU_PASS） | tests/ |

**测试统计**：harness 28/28；仓库 verifier 自测 12/12；verifier 全量 575/0。
**复现性验证**：脚本+锁+原始日志全部入库可重放；6 个真实缺陷被 harness 验证过程自身发现并修复（PS 5.1 的 WaitForExit 毫秒单位、Start-Process -PassThou 丢 ExitCode、原生参数引码损坏、-Include 通配、cp936 解码、快 epoch 与中断窗口竞态）。
**运行时分类**：全程 ENGINEERING_REFERENCE（D1 为官方字节负对照）。
**剩余缺口**：无（R21 范围）。

## C. R22 — 官方 wheel 验收

**五通道实扫**（multi-arch/stable/**rc/nightly/dev**——后三通道为历史首次扫描）+ 二进制审计 + GitHub compare 祖先链，全部当晚实证（绝不以日期推断）：

| 通道 | 最新 Windows 组合 | #13437 修复? | 证据 |
|---|---|---|---|
| multi-arch | torch 2.12.0+rocm7.14.1 | ❌ | P14/P16 冻结审计 + R21-D1 实时复现 |
| stable | torch 2.14.0+rocm10.1.0 | ❌ | P16 字节一致复审计（DLL 266d716b… marker 0） |
| **rc** | torch 2.15.0+rocm10.2.0rc2 | ❌ **新证明** | 轮 sha `ffbf6c77…`；DLL `3.6.2.8faffed0f` marker **0**；compare f0a5d266…8faffed0f **diverged，behind_by=92** —— 合并后构建日期（2026-11-06）但源码分支先于合并（2026-10-29） |
| **nightly** | libraries 10.3.0a20261115 | ✅（仅 libraries） | 轮 sha `33f5ea8a…`；DLL `3.6.3.9ea8cfc5` **marker 2**；9ea8cfc5 behind_by=0（当日复核）—— 但 nightly **未列 gfx1100 设备轮** |
| **dev** | rocm 10.3.0.dev0+\<TheRock sha\> | ✅ | 实装 `+ff576965`（TheRock 2026-11-05）→ 子模块 `4e7d93e3` → **behind_by=0**（ahead 604）；gfx1100+gfx1151 设备轮齐全；另抽验 d318a1c3→7b33c3d9 亦 behind_by=0 |

**候选级实测（dev 栈：torch 2.15.0+gitf6cd88cb · HIP 7.18.26441 · ultralytics 8.4.214，去 shim 干净环境，物理 gfx1100）全绿**：

| 门（干净腿） | 结果 | 证据 |
|---|---|---|
| G0 溯源 | **OFFICIAL_CANDIDATE**（marker 2、DLL 3.6.3.4e7d93e3、零 workaround） | r22cA2_provenance_clean.json |
| G1 无STL | **OFFICIAL_CANDIDATE_PASS** —— 无 shim、冷缓存、VCToolsInstallDir 重定向 —— **Windows 上首个官方渠道修复后轮的运行时 PASS** | r22cC_nostl.json |
| G2 GPU 门 | **9/9 PASS** | r22cB2_torch_gates_clean.json |
| G3 精确 CLI | **PASS exit 0**（无 shim 训练成功） | r22cD2_train_cli_clean.json |
| G4 优化器 | **PASS** | r22cE2_optimizer_clean.json |
| G5 中断/续训 | **PASS** | r22cF2_resume_clean.json |
| G8 子集 | 暖 3/3 + 冷 2/2，零异常 | r22cG/G2/G3 |

标记说明：干净腿 B2/D2/E2/F2/G3 记录内的进程级 `runtime_class` 字段早于"channel+marker 感知分类"补丁（该补丁在运行之后合入，未来运行进程内自分类）；套件分类以溯源记录 A2（OFFICIAL_CANDIDATE）为准，已在报告中披露。

**裁定**：`R22_CANDIDATE_VALIDATED`（**DEV 通道级**，上限 DEV_CANDIDATE_PASS）。**stable 验收 = `R22_BLOCKED_OFFICIAL_ARTIFACT`**（stable 无修复轮；rc 被祖先链证据取消资格）。
**已交付**：R22_CANDIDATE_WATCHLIST.md、R22_RELEASE_GATE_MATRIX.json、R22_ACCEPTANCE_RUNBOOK.md（gfx1100+gfx1151 可移植）。
**未跑项与阻塞**：G7 gfx1151（runner 原样可移植，待 8060S 执行，未伪造）；G9 清洁 Windows（开发主机 → `BLOCKED_INFRASTRUCTURE`，仅取得 HOST_REUSE_FRESH_VENV 证据类）；≥10 次/架构完整可靠性行列（今晚为 R21 规模子集）。

## D. R23 — 开发者体验

- 全套文档草稿 `docs/r23/`：README 指南、INSTALL_WINDOWS、COMPATIBILITY、TROUBLESHOOTING、VALIDATION_RESULTS、quickstart.ps1、真实 CLI 输出样本（expected-cli-output.txt）、社区发布摘要（RELEASE_SUMMARY）。
- 安装命令**全部来自当晚实测验证的官方 URL**（无占位符）；gfx1100/gfx1151 仅设备轮名不同。
- Quickstart 就绪度：命令真实可用，但带 BLOCKED_RELEASE 横幅（无 VS Build Tools 的机器首个 BatchNorm 仍失败）——**不发布**。
- 独立开发者验证：**PENDING_EXTERNAL_VALIDATION**（无独立开发者可用，未伪造）。
- 公开发布授权：**无**（未达 R22 OFFICIAL_STABLE_PASS）。

## E. 证据清单

- `evidence/raw/r21/`：16 条记录 + wheel-scan/（五通道发现原始 JSON）+ SHA256SUMS.txt + 训练 stdout 原件
- `evidence/raw/r22-dev/`：19 条记录（含干净重跑组 + r22_channel_binary_audit.json 通道二进制/祖先审计）
- `windows-golden-path/reports/`：r22-dev-candidate/report.json + SHA256SUMS、R22_RELEASE_GATE_MATRIX.json
- `evidence/manifest.json`：148 条（append-only）；`scripts/verify_release_closure.py`：**575/0**
- 工作区（不入库）：`C:\RadeonYOLO\{evidence,logs,scratch,wheels,venvs}`（r21-engref 与 r22-dev 两 venv 可复查）
- 关键哈希：fix=f0a5d266；rc 轮 ffbf6c77…/DLL 2a3a026c…；nightly 轮 33f5ea8a…/DLL 3.6.3.9ea8cfc5；dev 栈 DLL 3.6.3.4e7d93e3（marker 均 2 或 0 如表）

## F. 下一步（外部依赖，不自动完成）

1. **AMD 发布负责人**（rocm-libraries#15862 仍无 assignee）：确认修复后 stable 轮切点——watchlist 第一条触发即跑完整 OfficialStable 序列
2. **候选轮验收**：stable 出现 rocm-sdk-libraries>10.1.0，或 rc3+（**必须重新证明祖先链**——rc2 教训：构建日期不可作为依据）
3. **gfx1151 真机执行**：8060S 原样运行 R22_ACCEPTANCE_RUNBOOK（含 ≥10 次可靠性 + 冷/暖缓存矩阵）
4. **清洁 Windows 独立安装验证**（新装系统/受控镜像 + 未参与本项目的开发者）

## 最终裁定（严格词汇）

| 任务 | 裁定 |
|---|---|
| **R21** | **`R21_HARNESS_VALIDATED`** —— harness 功能完备，全部由真实 gfx1100 测试背书 |
| **R22** | **`R22_CANDIDATE_VALIDATED`**（DEV 通道级：候选门全过、无 shim）；stable = `R22_BLOCKED_OFFICIAL_ARTIFACT` |
| **R23** | **`R23_DRAFT_READY`** —— 文档就绪，未获发布资格 |

未宣称 `R22_OFFICIAL_STABLE_PASS` / `R23_RELEASE_READY`：其证据不存在。
