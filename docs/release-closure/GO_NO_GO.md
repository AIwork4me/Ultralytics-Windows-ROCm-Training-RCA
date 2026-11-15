# GO / NO-GO — Final verdicts (2026-11-14)

## GO-A: Experimental Windows FP32 Training — **PASS (CONDITIONAL on ENV-B labeling)**

| Condition | Status |
|---|---|
| Native Windows AMD HIP (torch.version.hip=7.14.60850, real device, fwd/bwd/optimizer proven) | ✅ |
| Verified MIOpen (in-process loaded-DLL sha256 per leg) | ✅ |
| FP32 training lifecycle PASS | ✅ 7 tasks × T01–T15 (14/14 each) on ENV B + 30-epoch long run (third environment — miniconda base, pre-fix official 7.14.0 wheel; audit-corrected labeling) |
| Reproducible installation/environment | ✅ pinned wheel command + lock records + probe tools |
| Explicit limitations | ✅ ENV B = **source-built patched MIOpen** (G0 BLOCKED_RELEASE — no official wheel with the fix exists yet); official wheel works for FP32 with host STL visible |

**Conditional nature**: the PASS describes the validated environment; on the *official wheel today*, spatial-BN training works only because host MSVC STL is present — the no-STL robustness comes exclusively from the fix, which ships in no official package yet.

## GO-B: Complete Windows Training — **CONDITIONAL PASS**

| Condition | Status |
|---|---|
| GO-A | ✅ |
| AMP verified | ✅ on official wheel (precheck PASS + 10-epoch probe: scaler anneal semantics correct, 3/4 steps overflow-skipped, ≥1 real update — **not a weight-learning demonstration**; audit-corrected scope M5); on ENV B the precheck can silently fall back (root-caused, cache-state dependent) — falls under known-limitations |
| Task matrix covered | ✅ all 7 tasks the current version supports |
| Checkpoint/resume works | ✅ T12 7/7 + integrity audits |
| Quality/stability evidence | ✅ 30-epoch public-dataset run, A/B with disclosed limits; **quality-vs-reference INCONCLUSIVE** (no Linux reference machine — BLOCKED_HARDWARE) |
| GPU families tested or claims narrowed | ✅ claims narrowed to gfx1151 only |

**Conditional nature**: AMP PASS is wheel-scoped (official); quality claims remain functional-level (no benchmark claim); non-tested families explicitly excluded.

## GO-C: Upstream Official-Ready — **NO-GO today / CONDITIONAL on external events**

| Condition | Status |
|---|---|
| G0 official release package confirmed | ❌ **BLOCKED_RELEASE** — no obtainable official package contains PR #13437 (2026-11-14) |
| G1/G2/G3/G4 gates satisfied | ✅ (G1/G2/G3 on ENV A/B; **G4 on a third environment** — miniconda base, pre-fix official 7.14.0 wheel, no in-process DLL probes — audit-corrected, P8_INDEPENDENT_AUDIT.md M4) |
| Maintainer-friendly tests | ✅ drafts + executed supersets (PR-A/B/C/D + MIOpen issue draft) |
| CI strategy + execution evidence | ⚠️ strategy documented; GPU-CI execution requires self-hosted runner (Owner Action Required) |
| Documentation matches supported scope | ✅ conditional wording audited (P8 three-reviewer audit); verifier pattern-scan is a 4-regex guard over doc dirs — a *screening* aid, not exhaustive enforcement (audit-corrected, m4) |
| No unsupported claims | ✅ audited claim-by-claim in P8_INDEPENDENT_AUDIT.md; the 218-check verifier covers structure/status-vocab/globs — it cannot catch every doc-vs-record mismatch (audit-corrected, m4/m5) |

**Path to GO-C**: (1) an official Windows wheel built from a post-merge MIOpen lands (re-run G0 §4 checklist + G1/G2 against it) → (2) owner approves upstream submissions → (3) GPU CI runner provisioned. GO-C is *blocked on external events + human approvals*, not on unknowns.

## One-line summary

**The engineering is done and evidenced; the release channel and the human approvals are the remaining gates.** A Windows developer still cannot get the fixed MIOpen from any official wheel today — that is the single decisive blocker (BLOCKED_RELEASE), and until it clears, "official support" language is forbidden everywhere in this repo (screened by the verifier's pattern scan and audited line-by-line in P8_INDEPENDENT_AUDIT.md).

---

## P9 addendum (2026-11-14, mission P9–P12 §3/§4) — evidence hardening re-verdict

Verdicts **maintained**; conditions upgraded from prose-scoped to per-step-proven:

**GO-A (upgrade)**: G4 long-run + matched A/B re-executed **on ENV A and ENV B separately** with in-process DLL probes (`raw/g4_long_run_ENV_A_p9.json` `e97891df…` / `raw/g4_long_run_ENV_B_p9.json` `ed7c67a9…`) — the P8 "third environment" caveat (audit M4) is **eliminated**; both runs reconcile configured=observed=30 epochs with the upstream `final_eval` epoch+1 callback accounting proven from source (8.4.174 + 8.4.182).

**GO-B (upgrade)**: AMP scope upgrades from "scaler semantics + ≥1 update" to **genuine repeated updates**: t16 records 24 real optimizer updates (per-parameter, all 366 tensors changed per step, scaler anneal 65536→2048) on the official wheel (`raw/g2_detect_amptrack_20261114T131559Z.json`); the historical t08 FAIL is per-step reclassified as **intended GradScaler overflow skips** (mechanism previously "plausible-unproven"). Representative-dataset learning validation: see `raw/g3_amp_learning_*.json` (P9 §4.4). The AMP **precheck** false-failure design flaw was independently fixed upstream in 8.4.197 (PR #26967, per-layer relative-norm design replacing `amp_allclose`); validation of the new check on gfx1151: `raw/g3_checkamp84212_*.json`.

**GO-C (unchanged)**: official-wheel rescan 2026-11-14 13:32Z — newest Windows wheel remains torch-2.12.0+rocm7.14.1 (`release-provenance/raw/official_wheel_rescan_20261114.json`) → **BLOCKED_RELEASE stands**. Upstream submission now authorized by the Owner (mission §1); submit only what validated evidence supports.

---

## P13 addendum (2026-11-15, mission P13) — CURRENT authoritative verdict

Verdicts: **GO-A CONDITIONAL PASS(maintained)** · **GO-B CONDITIONAL PASS(maintained,scope+)** · **GO-C NO-GO(BLOCKED_RELEASE 维持)** · **GATE 4 NOT_MET(依赖 GO-C)**

**GO-B(P13.1 scope upgrade)**:upstream PR #27198 按评审 MEDIUM 发现扩展为**探针全生命周期守卫**(probe-model 构建 + `.to(device)` 搬移 + forward),异常分类策略显式化(OOM/构建/搬移/forward/中断传播),7/7 回归测试绿(gfx1151 实机,含真实 GPU 健康正控),Docs CI 绿,CLA 已由 Owner 本人签署,torch 1.8 兼容修复已推。**未合并 — 保持"提交≠上游解决"原则。** 见 `P13_PR27198_CLOSURE.md`。

**GO-A(P13.2 scope correction,如实降级一处表述)**:P9 的 "ENV B 混合态确定性崩溃根因 = fdb 不可读" 假设被 P13 受控实验**部分推翻**:"unreadable" = 文件不存在(bin 目录两环境均无 FDB,官方 3.5.2 不发起该查找,属 3.6.2 行为差异);该警告非致命(128/128 层 fp16 重算全过);崩溃在 P13 同 env/DLL/缓存下 **3 种独立配置均不可复现** → 根因 **UNRESOLVED**(三候选已归档),P9 会话内 3/3 崩溃证据保留不改写。见 `P13_INVALID_KERNEL_FILE_RCA.md`。

**GO-C(P13.3 sharpened)**:2026-11-15 复扫官方 index 最新仍 `torch-2.12.0+rocm7.14.1`;TheRock 全部公开 tag(10.1=2026-09-25 等)**早于**修复合并(2026-10-19)→ "无任何含修复的 release 切片"坐实;torch-2.13.0 仅 linux。**BLOCKED_RELEASE 维持**,已向 #15862 提交发布链切点证据评论。

**Verifier 权威计数对账**:565(P9 wave-3 中间值)→ **575 checks / 0 violations @ HEAD**(本会话实测,exit 0);dated 历史文档保持不动,活文档(本文件、Draft PR #13 body)已更正。

**GATE 状态**:G1 ✅(ENV A/B 工程正确) · G2 ⏳(#27198 open 等复审;#13437 已合) · G3 ❌ BLOCKED_RELEASE · G4 ❌ NOT_MET(依赖 G3;Golden Path 文档就绪度见 `P13_GOLDEN_PATH_REPORT.md`,独立用户测试 BLOCKED_INDEPENDENT_USER_TEST)。

---

## P14 addendum (2026-11-15, mission P14) — CURRENT authoritative verdict

Verdicts: **GO-A CONDITIONAL PASS(维持,证据面扩大)** · **GO-B CONDITIONAL PASS(维持,质量精修)** · **GO-C NO-GO(BLOCKED_RELEASE 维持并升级为双通道+运行时证据)** · **GATE 4 NOT_MET(维持)** · **新增:安全事件已处置(owner 须轮换密钥)**

**GO-B(P14.2)**:PR #27198 推进至 `090e378` —— ① 探针异常日志改为真实陈述(不再把后端异常错报为"AMP 数值异常",新增 FP32 关联诊断);② 删除与既有 `test_cuda.py::test_amp` 重复的健康正控测试(官方指南去重),保留 6 个 CPU 故障注入测试;实机复验(gfx1151):健康 True / 注入 False+新消息、6/6 CPU 测试绿、ruff clean、CI **15 pass / 6 skip / 0 fail**。仍未合并(等待人工复审)。见 `P14_PR27198_UPSTREAM_READINESS.md`。

**GO-C(P14.1 证据升级)**:发现**第二官方通道** `stable.repo.amd.com/rocm/whl-next/` 提供 Windows torch 2.13.0/2.14.0+rocm10.1.0(推翻 P13"通道未前进"表述)——但二进制溯源(内嵌版本 `3.6.1.39d8d603`,构建点 2026-09-16 < 合并 2026-10-19;修复标记 0)+ **运行时三腿 no-STL 对照**(A 官方 7.14.1 FAIL / B whl-next 10.1.0 FAIL 逐字同签名 / C 合并源码参照 PASS)证实仍无修复 → **BLOCKED_RELEASE 维持**;#15862 已更新(含切点与运行时证据、路由问题)。正面发现:whl-next 新栈在 gfx1151 可真实 GPU 计算(修复轮发布后可直接作基座)。见 `P14_OFFICIAL_WINDOWS_WHEEL_AUDIT.md`、`P14_NO_STL_COMPARISON.json`。

**GO-A(P14.3)**:可执行 Golden Path 套件(`golden-path/` 十件套)在本机官方栈 MODE B **全流程实测 PASS**(环境验证/冒烟/20ep 代表训练 mAP 0.4919→0.5603/验证/检查点核验/真实中断→跨进程续训 epoch 15→20/错误 UX exit-2 拒绝 CPU);P13 报告不可执行表达式已修订。见 `P14_GOLDEN_PATH_EXECUTION_REPORT.md`。人工实机证据 ≠ GATE 4(独立用户)。

**安全事件(P14.0 发现)**:P9 时代 21 个已推送证据 JSON 含宿主 `ZHIPU_API_KEY` 实值(公开仓库)。HEAD 已全量脱敏 + `scripts/scan_secrets.py` 常设防护(`e3398d4`);**git 历史旧 blob 仍在 → owner 必须轮换该密钥**;历史改写留 owner 决定。

**环境状态**:ENV B 还原与 E5 单组件实验仍被 P13 记录的 ghost 锁阻塞(P14 重核验:6 个 ghost 进程 CIM 可见、taskkill "无实例"、DLL 写锁 err32,`p14_ghost_recheck.json`);invalid-kernel 根因维持 UNRESOLVED。

**GATE 状态**:G1 ✅ · G2 ⏳(#27198 open / #13437 已合) · G3 ❌ BLOCKED_RELEASE · G4 ❌ NOT_MET(Issue #14 零回应,BLOCKED_INDEPENDENT_USER_TEST)。

---

## P15 addendum (2026-11-15, mission P15) — CURRENT authoritative verdict

Verdicts: **GO-A CONDITIONAL PASS(维持, P15 证据面再扩大)** · **GO-B CONDITIONAL PASS(维持, 全链金路径 P15 重跑)** · **GO-C NO-GO(BLOCKED_RELEASE 今日实测维持)** · **GATE 4 NOT_MET(维持)** · **GATE 5 NOT_RUN(NVIDIA_COMPARISON_BLOCKED_HARDWARE)** · **GATE 6 IN_PROGRESS/BLOCKED_RUNNER**

**P15 上游贡献(两项, 均未合并)**:
1. **#27198 → `fc72b4e`**: 按现行 AGENTS.md 冷审后测试收缩(6 个 mock 重测试 → 2 个聚焦契约, −79/+13, 删 torch>=1.13 兼容垫片); CI 15 pass/6 skip/0 fail。**无人工评审 — 不作接受宣称**。
2. **#27203 (新开, `78b5b15`→`a1be048`)**: P15 冷审新缺陷 — 上游 `cuda_device_count()`(nvidia-smi)与 `GPUInfo.select_idle_gpu()`(NVML)双 NVIDIA-only 门使 `tests/test_cuda.py` 在健康 AMD HIP 实机整文件静默跳过; 修复后 gfx1151 实测 SKIP→**PASS**; bot MEDIUM(indices=[] 语义)已修复并答复。

**GO-A/B(P15 GPU 全链, 官方发布栈 torch 2.12.0+rocm7.14.1 + released 8.4.182, gfx1151)**: amp-probe(autocast fp16 dtype 证明 + GradScaler 8/8 真实更新)→ smoke w0/w2/w4/暖缓存全 PASS(23.1–23.5s)→ 30ep COCO128(mAP50-95 0.4927→0.5980→0.5851)→ 硬中断(PID 11452, epoch≥20)→ 新进程恢复(from epoch 22, lr0=0.000119 还原)→ best.pt val 0.5949 → 重载推理 6 框。证据 `release-provenance/raw/p15_gfx1151/`。

**GO-C(P15.1 复扫)**: 双官方通道索引无新 Windows wheel; 决定构件 `rocm_sdk_libraries-10.1.0` 与 P14 预修复版逐字节同尺寸(118,645,973)+ Last-Modified 2026-10-05(早于合并)→ 未重建, **BLOCKED_RELEASE 维持**; 无新材料故未评论 #15862(反骚扰规则)。

**P15.5**: NVIDIA UX parity 契约**预注册冻结** + `scripts/p15/nvidia_reference.py` 就绪; NVIDIA 侧全 NOT_RUN, 零捏造值。

**GATE 状态**: G1 ⚠️(一类完成/二类 BLOCKED_HARDWARE → 任务书口径 NOT_MET) · G2 ⏳(#27198/#27203 open 等人工评审) · G3 ❌ BLOCKED_RELEASE · G4 ❌ NOT_MET(#14 今日实测 0 评论) · G5 ❌ NOT_RUN(对照硬件缺失) · G6 ⏳(Layer A 随两 PR 上行; Layer B BLOCKED_RUNNER, 本地 runner 契约已交付)。安全事项维持: owner 须轮换 ZHIPU_API_KEY。详见 `P15_FINAL_GO_NO_GO.md`。
