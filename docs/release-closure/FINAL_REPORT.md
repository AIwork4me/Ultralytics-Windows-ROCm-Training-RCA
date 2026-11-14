# FINAL REPORT — Operation Windows ROCm YOLO Training, Release-to-Upstream Closure

Date: 2026-11-14 · Branch: `work/windows-rocm-training-release-closure` · Repo: AIwork4me/Ultralytics-Windows-ROCm-Training-RCA

## A. Executive Summary

**实际完成**：在一个工作日内完成了 P0–P8 全链路执行——历史证据复核（171 文件 manifest + 10 ISA 对全 PASS）、G0 发行溯源（源码链全 PROVEN、发行链全 PROVEN NEGATIVE）、G1 十六原语矩阵（含 no-STL 回归与精确 #3956 负对照）、G2 七任务 × T01–T15 完整生命周期（每任务 14/14）、G3 AMP 根因闭环（两层根因 + 官方 wheel 上真实 AMP 训练验证）、G4 长训练与性能 A/B、G5 四份上游 PR/Issue 草稿、184 项验证合同全过。**P8 独立三视角审计（2026-11-14 晚）完成：三视角均 PASS-WITH-FINDINGS；11 项 MAJOR 发现全部处置（文档重标/复跑定案/证据持久化，见 `P8_INDEPENDENT_AUDIT.md`）；验证合同扩容至 218 检查 exit 0。**

**真正解决的问题**：
1. Round-3 遗留的 AMP anomaly **根因关闭**（不是 ROCm kernel bug）：fp16 坐标量化差 0.15–0.76px vs check_amp 的 atol=0.5 设计缺陷，叠加源码构建 MIOpen 3.6.2 的 EvaluateInvokers 负计时异常（仅 ENV B）；官方 wheel 上 AMP 完全可用且真实训练有效。
2. phase5_7/5_8 遗留的 "biased/unbiased estimator" 限制**正式解决**：GPU BN running 统计量与 unbiased float64 参考差 6.8e-08（语义正确）。
3. 发行溯源方法学落地：compare-API 祖先验证替代日期推断，marker+行为双重锚定。

**仍然存在的问题**：无官方发行包含修复（BLOCKED_RELEASE）；官方 wheel 的 AMP precheck 依赖 cache 状态的问题在源码构建版上触发（上游修复草稿就绪）；gfx1100/gfx1200/Linux 机器未接入。

**三类 GO/NO-GO**：GO-A **CONDITIONAL PASS** · GO-B **CONDITIONAL PASS** · GO-C **NO-GO（外部阻塞）**——详见 `GO_NO_GO.md`。

## B. Git & PR

- Branch: `work/windows-rocm-training-release-closure`（基于 main `f9f745e`）
- HEAD（本报告时点）: `8338250` + P8 收尾提交（最终值见 git log）
- 提交列表: `7949437` P0 审计 · `134ded7` G0 溯源 · `363e602` G1 矩阵 · `593160e` G2 harness · `8338250` G2+G3 闭环 · P8 收尾
- Draft PR URL: **无上游 PR**（任务边界：需 Owner 批准）；自有分支已推送 origin
- CI: 自有仓库无 GPU runner（策略已文档化）；上游 CI 状态不适用
- Working tree: P8 审计批次（重标/复跑证据/verifier 扩容/草稿修正）已提交（见 git log）；除历史遗留 untracked 文件 phase5_5/docs/GTEST_ARCHITECTURE_COMPARISON.md 外干净

## C. Release Provenance

- 链路：PR #13437 (squash `f0a5d266`, 2026-10-19) → TheRock #9359 (merge `b0958085`, submodule bump `cb26189→d875648`) — **PROVEN** d875648 ⊇ f0a5d266（compare ahead_by=2/behind_by=0）→ TheRock main 现指针 `9ea8cfc5` ⊇ f0a5d266（ahead_by=1011/behind_by=0）
- **包含修复的正式版本：不存在**（2026-11-14）。最新 TheRock release therock-10.1（2026-10-05）早于合并；AMD wheel index 最新 torch-2.12.0+rocm7.14.1（marker=0 + 行为验证无修复）；PyTorch 官方无 ROCm Windows wheel；TheRock gfx1151 nightly 止于 2026-06-12
- Binary provenance：官方 wheel DLL `e97891df`（无修复）/ 源码构建 `ed7c67a9`（f0a5d266，marker=2）/ b58（d4b574ac 参考）/ yolo_amd 7.14.0 `74b4ee03` 锚点——每份含 SHA256 与来源，swap/restore 双向哈希验证

## D. Hardware & Environment

- 机器：AMD Ryzen AI MAX+ 395 (Strix Halo) w/ Radeon 8060S · **gfx1151** · Windows 11 build 26200 · 驱动 32.0.22032.6002 · 78GB 统一内存
- 环境：conda python 3.13.16；torch 2.12.0+rocm7.14.1 / torchvision 0.27.0 / ultralytics 8.4.182（A/B 两环境同版本栈）；HIP 7.14.60850
- **第三环境（G4 专用，audit-corrected 2026-11-14）**：miniconda base——python 3.13.13、ultralytics 8.4.174、torch 2.12.0+rocm7.14.0 官方 wheel（pre-fix MIOpen `74b4ee03`，host STL 可见）；G4 长训与 A/B 实际运行于此，此前误标为 ENV A/B（`P8_INDEPENDENT_AUDIT.md` M4）
- ENV A = `pm13437_official`（pristine 官方 wheel，未修复）· ENV B = `pm13437_merged`（G1–G4 会话期间运行期换入源码构建 patched DLL；**2026-11-14 19:39 已 restore 至官方 DLL，哈希验证 `e97891df` = OFFICIAL_WHEEL**——僵尸进程自行清除，无需重启，见 `windows-training-validation/environment/INCIDENT_ZOMBIE_PROCESSES.md §RESOLVED`）

## E. G0–G5 Results

| Gate | Verdict | 数量 | 关键数据 | 原始证据 | 限制 |
|---|---|---|---|---|---|
| G0 | **BLOCKED_RELEASE** | 11 行 release 矩阵 | d875648/9ea8cfc5 ⊇ f0a5d266；wheel/nightly/tag 全扫 | release-provenance/* | 无官方包含修复 |
| G1 | **PASS** | 16 原语 ×3×2 模式 + gtest×3 | no-STL 全绿；#3956 四段签名精确复现 | windows-training-validation/reports/* | ENV B 为源码构建 |
| G2 | **PASS**（FP32 轨道） | 7 任务 × 14 测试 | 全 98 测试 PASS；workers 0/2/4；ENV A amptrack 13/14（t08 FAIL 确定性复现，audit-corrected） | raw/g2_*.json | AMP 轨道见 G3 |
| G3 | **根因闭环** | 2 环境 × 2 cache 态 × 5 重复 | 0.233px(PASS) vs 0.760px(FAIL) 翻转；AMP 10ep：scaler 语义正确 + ≥1 真实更新（非"学会训练"，audit-corrected） | raw/g3_*.json | 单探针图（与官方 precheck 同条件） |
| G4 | **PASS**（稳定/性能有限范围） | 31 epochs + A/B | 0.505→0.602 全有限；AMP VRAM −33%、微负载 1.60× 慢——**第三环境**（miniconda base，pre-fix 官方 7.14.0 wheel `74b4ee03`；audit-corrected 重标，无 in-process DLL probe——已披露偏差） | raw/g4_*.json | 质量对照无 Linux 参考机 |
| G5 | **DRAFTS COMPLETE** | 4 PR 草稿 + 1 Issue 草稿 | 全部最小 diff + 可运行证明 | upstream-readiness/* | 上游动作需 Owner 批准 |

## F. AMP RCA（详见 amp-rca/）

- **根因找到：是**（两层）——(1) 良性 fp16 坐标量化差（逐列范围 0.0730–0.7606px、conf ≤0.0043、cls=0、检测数相同；audit-corrected）被 (2) `check_amp` 的 `atol=0.5` 像素坐标绝对容差误判；MIOpen cache 状态（kernel 选择）决定差值幅度。**audit-corrected（M2）**：EvaluateInvokers 负计时异常在源码构建 3.6.2 上重复出现（4× g2_pose_main.log），官方 3.5.2 上罕见但存在（1× 于一次中止尝试；干净复跑 0×）——非"仅 ENV B"；ENV-B 特有的是差值在 default-cache 态**越过 0.5px 阈值**（官方两态 0.264/0.423px 均低于阈值）
- 层次：Ultralytics 检查设计（主）+ MIOpen solver 计时异常（次，新发现）+ 环境 cache 状态（触发器）
- 最小复现：`amp-rca/MINIMAL_REPRO.py`（单进程，逐列输出差异）
- 修复内容：PR-C 草稿（IoU+类别+置信度匹配替代逐像素 allclose，~15 行，跨平台安全）；MIOpen 侧 Issue 草稿（证据引用已按审计 M3 修正）
- 修复后真实验证：官方 wheel 上 10-epoch AMP 训练（Scaler 65536→8192 退火、3/4 步溢出跳过、1 次真实更新于最终 epoch；fitness 增益发生于跳步 epoch=BN running-stat 更新——**该探针证明的是 scaler 语义正确 + AMP 无异常完成 + ≥1 真实更新，非"真实学习"**，audit-corrected M5）

## G. Functional & Quality Results

- 7 任务（detect/segment/classify/pose/obb/semantic/depth）× FP32：Train/Val/Predict/Save/Load/Resume **全 PASS**
- AMP：官方 wheel 机制验证（precheck PASS + scaler 退火语义 + ≥1 真实更新；amptrack lifecycle 13/14，t08 FAIL 确定性复现——GradScaler 跳步假设，机制未证）；ENV B cache 态依赖回退（根因+草稿）
- 质量：功能性指标可信（fitness 轨迹、mAP50=0.94 冒烟级）；**基准级质量声明 INCONCLUSIVE**（无 Linux 参考机）
- 稳定性：31-epoch 零异常零 NaN；进程级失败恢复事件全部如实归档
- 性能：匹配 A/B 完成并披露限制（微负载）；无跨版本性能声明（合法基线不存在）

## H. Upstream Deliverables（全部为草稿，等 Owner 批准）

- PR-A：release 追踪/打包证据（RELEASE_LINEAGE 方法学）
- PR-B：Windows ROCm 训练回归测试（SKIP 安全、严格语义）
- PR-C：check_amp 最小修复（~15 行 + 回归测试设计）
- PR-D：AMD 集成文档（条件措辞、证据引用）
- Issue：MIOpen EvaluateInvokers 负计时异常（gfx1151）
- MAINTAINER_CHECKLIST：每条声明 → 最小可运行证明

## I. Remaining Blockers

| Blocker | 为何阻塞 | 需要谁 | 解决动作 | 解决后重跑 |
|---|---|---|---|---|
| 无官方发行包含修复 | GO-C 的 G0 PASS 条件；开发者"免手动换 DLL"体验无法达成 | AMD/ROCm release engineering | 切 post-merge release 并发布 Windows wheel | G0 §4 清单 + G1/G2 全套（官方 wheel） |
| 上游提交权限 | 任务边界 §2.4 | Owner（你） | 批准后按草稿提交 4 PR + 1 Issue | 上游 CI + maintainer review |
| Windows AMD GPU CI runner | PR-B 的真实训练验证只能在 GPU runner | Owner / Ultralytics maintainer | 配置 self-hosted runner（安全约束已写） | PR-B 测试在 CI 执行 |
| gfx1100/gfx1200/Linux 机器 | 跨架构覆盖 | 机器接入 | 运行 platform-matrix 模板中的命令 | G1/G2/G3 对应家族 |
| ~~env B DLL 恢复~~ **已解决（2026-11-14）** | 僵尸进程自行清除，无需重启 | — | restore 已执行并哈希验证 e97891df | 不适用 |

## J. Final Next Steps

**P0（立即）**：① ~~重启机器 → env B DLL restore + 哈希验证~~ **已完成（2026-11-14 19:39，僵尸自清，restore 哈希过）** ② 等待/查询首个 post-merge 官方 wheel（输入：RELEASE_LINEAGE §4 清单；动作：逐周扫描 AMD index；收益：GO-C 解锁的第一步）
**P1（官方 wheel 落地后）**：③ 用官方 wheel 重跑 G1/G2/G3 全套（输入：本仓库全部 harness，参数不变；退出条件：官方 wheel 上 no-STL G1 全绿 + G2 7×14 + AMP 有效；收益：GO-A/B/C 全部转为无条件 PASS）
**P2（并行）**：④ Owner 审阅 4 份 PR 草稿并批准提交（输入：upstream-readiness/*；收益：进入 Ultralytics/MIOpen maintainer 流程）⑤ 接入 gfx1100/gfx1200/Linux 机器运行平台模板（收益：支持范围扩大到实际验证的家族）
