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

---

## K. P9 证据加固批次报告（mission P9–P12 §3/§4，2026-11-14 深夜）

### K.1 测试正确性修复（§3.1/§3.2 — P8 审计遗留全关闭）

| 审计遗留 | 修复 | 证据 |
|---|---|---|
| t08 聚合 Σ\|θ\| 可掩盖张量变化（取消抵消）且无法识别跳步 | 重写为 per-parameter tensor delta（float64、逐 tensor max-abs + 变更 tensor/元素计数；BN buffer 单列、永不计入更新证据） | `tests/amp_step_audit.py` + CPU 对抗套件 34/34（含取消抵消陷阱用例——旧方法在此用例下确实漏判，新方法捕获） |
| t07 对 AMP 梯度无条件 PASS | 严格分类：scaled 域非有限仅在 scaler 认定（found_inf）且跳步时接受（G_OK_SKIP 单列事件）；步进执行带非有限梯度 = BAD_GRAD_UPDATE（FAIL） | 同上 + ENV A/B 复跑记录 |
| t08 FAIL"机制未证"（audit B-F2） | **每步重分类证明**：生命周期 lr>0 步均为预期 GradScaler 溢出跳步（found_inf=true、scale 减半）——t08 如实 SKIP（绝不计入 PASS） | `raw/g2_detect_amptrack_20261114T131559Z.json`（ENV A，in-process `e97891df`） |
| audit M5"仅 1 次真实更新，非学会训练" | **t16 新测试**：12-epoch coco128 专项运行 = **24 次真实重复更新**/29 步机（1 warmup + 4 溢出跳步），每次更新 366/366 float tensor 变更（max delta 2.48e-05），scaler 退火 65536→2048 | 同上 t16 记录 |
| log 文件名按任务键碰撞（§3.4） | run_id 化不可变输出 `g2_{task}_{tag}_{runid}.*`，冲突即 fail；runner 写 run_id/env_id 进每个日志头 | `scripts/g2_runner.py` + 新 raw 记录 |

### K.2 G4 修复（§3.3）

- **31 vs 30 根因**：上游 `final_eval()` 在训练循环后 `self.epoch += 1` 再触发一次 `on_fit_epoch_end`（"log best metrics at step epochs+1"，8.4.174 与 8.4.182 源码一致）——**30 个训练 epoch 正确，第 31 个是上游有意的 final-eval 回调，非过训练**；旧 harness 把每个回调当训练 epoch 记账（重复条目的 epoch_time/lr/mem 均为陈旧值——最终验证只重算 metrics/fitness）。
- harness 重写：configured vs observed 对账块（csv 行=训练回调=30、final_eval=1 才 reconciled）、in-process DLL probe（训练后）、results.csv 原文内嵌（B-F9"CSV 已保留"虚假声明根治）、逐 epoch wall 采样、checkpoint 元数据、run_id 不可变输出。
- **ENV A/B 重跑**（消除 audit M4 第三环境限定）：ENV A `e97891df` 30/30 对账 fitness 0.505→0.602；ENV B `ed7c67a9` 30/30 对账 0.505→0.603。A/B：ENV A AMP 有效 1.43× 慢/VRAM−33%（微负载，含每 mode DLL probe）；ENV B check_amp 回退 → amp_leg 如实 SKIP（ratio=null，"NOT AN AMP MEASUREMENT"）。

### K.3 证据合同 v2 + 对抗自测（§3.4）

- verifier 286 检查：断言重算（t07/t08/t16 从内嵌证据重导出，声称与证据矛盾即 FAIL）、SKIP≠PASS、PASS 必须带 GPU+binary 双溯源、run_id 必须出现在对应日志、environment_id 跨日志一致、**同环境 DLL SHA 一致性（污染探测器）**、硬件一致性、G4 epoch 对账强制、claims 表逐行证据文件存在性。
- 对抗 fixtures `scripts/test_verify_release_closure.py`：已知好树 ACCEPT + 11 类已知坏记录（坏状态词表/全 SKIP 冒充/声称与证据矛盾/run_id 不一致/缺日志/缺 DLL/跨环境 DLL 污染/硬件冲突/epoch 未对账/缺 CSV/claims 引用不存在文件）**全部 REJECTED 12/12**。
- 防御记录：历史记录按 legacy 合同豁免断言重算（缺失新字段不构成违规——重算旧记录会制造假违规而非发现真违规）。

### K.4 AMP 修复转向（§4.2 — 上游已自行修复）

- **发现**：ultralytics **8.4.197（PR #26967，2026-11-01）重新设计 check_amp**——未训练 YOLO26n（免下载权重）+ 逐层 Conv2d/Attention 在 AMP 下从自身 FP32 输入重算 + 相对范数 ≤5% 容差（NaN/Inf 按比较语义天然失败），并移除 trainer 的 callbacks 备份 hack。我们的 PR-C（IoU matcher 替换 amp_allclose）**对 main 已过时**——不提交重复/过期补丁（mission §9）。
- PR-C 的 matcher 保留为**验证套件**：CPU 对抗 26/26（重排序/NMS 平局/类别翻转/增删检测/空预测/退化框/小大框/NaN/Inf/坏算子/边界），归档真张量 5/5，GPU 捕获（ENV A default 0.423px、ENV B fresh 0.423px、default 0.497px、warm-training 0.497px——均 old=new=5/5，5 类真张量负对照全捕获）。历史 0.7606px 态今日不可精确复现（cache 演化已记录；该幅度由合成 0.76px 用例覆盖）。
- **8.4.212 新 check 在 gfx1151 验证**（default/fresh/warm-training 三态 × ENV A/B）：`raw/g3_checkamp84212_*.json`（批次 3）。

### K.5 真实 AMP 学习（§4.4 — M5 遗留彻底关闭）

imagenette2-160（真实照片 10 类 9469 train）匹配 FP32-vs-AMP classify × 6 epochs，全步审计：
- **ENV A（官方 wheel）**：FP32 887 次更新 top1 0.935→0.973；AMP 887 次更新 top1 0.935→0.970（Δ−0.23%，正常 AMP 方差）、AMP 有效、0 溢出跳步、losses 全有限、**AMP 212.7s vs FP32 265.8s = 1.25× 快**（代表性负载，非微负载）
- **ENV B**：FP32 PASS（同 887/top1 0.973）；AMP leg check_amp 回退 → 如实 SKIP（FP32-vs-fallback top1 完全一致——同种子同数学）
- 判定：PASS 要求"稳定训练 + 有意义的成功更新次数 + 可信任务指标"——**887 次 per-parameter 验证更新 + top1 97% 达标**；"top1 增益是否来自 BN running-stat"的疑虑由 887 次真实权重更新直接消除。

### K.6 EvaluateInvokers（§4.3 — 状态：不可隔离复现，RCA 未决）

- 无 Ultralytics 最小复现（9 个纯 torch conv 配置 × fp16/fp32 × fresh-cache Find 路径 × 2 环境）：**0 次触发**（`raw/g3_evi_*.json`，repeat 对确定性一致）。
- 结论：异常为**全训练负载下的稀有间歇事件**（历史：ENV B 4×、官方 1× 于中止尝试、干净复跑 0×）——按 mission §4.3 要求"无法充分复现时不猜测"，以精确 Issue 提交（历史日志证据 + 隔离复现阴性结果 + 请求 maintainer 指认触发条件），RCA 标注 unresolved。

### K.7 P10 矩阵复跑（§5.1 L1 全绿）

7 任务 FP32 生命周期（detect/segment/classify/pose/obb/semantic/depth）× 新 per-parameter harness，**全部 14/14 PASS**（t08 每任务 per-parameter 证据）+ detect workers 2/4 各 14/14 —— 共 126 测试全 PASS，全部 in-process DLL probe `ed7c67a9`（ENV B patched）。L2 代表性数据集运行 = K.5 imagenette（classify 轨道）。
