# HANDOFF — Release-to-Upstream Closure 交接文档

写于 2026-11-14 收工（P8 独立审计批次后更新；**P9 批次 2026-11-14 深夜更新**）· 分支 `work/windows-rocm-training-release-closure` · HEAD 见 git log（本文件随审计批次提交推送）

## 1. 一分钟状态

**任务**：Windows ROCm YOLO 训练 Release-to-Upstream Closure（P0–P8），**P9–P12 证据加固批次进行中（mission P9-P12，§3 P8-findings-closure + §4 AMP fix/validation）**。
**P9 已完成**（全部有 raw 证据）：
- **§3.1/3.2 t07/t08 重写**：per-parameter tensor-delta + GradScaler 全插桩 + 严格 t07（无无条件 AMP PASS）+ skip/failure 分类；CPU 对抗套件 34/34（GPU 前抓出 4 个插桩真 bug）；**ENV A amptrack 复跑 14/15 PASS + t16 = 24 次真实重复参数更新**（audit M5 关闭）；历史 t08 FAIL 按步重分类为"预期溢出跳步"（机制已证）。
- **§3.3 G4 epoch 记账**：31 vs 30 根因 = 上游 `final_eval()` epoch+1 best-metrics 回调（8.4.174/8.4.182 源码验证）——30 个训练 epoch 正确，非过训练；harness 重写（对账块 + in-process DLL probe + 内嵌 results.csv + wall samples + checkpoint 元数据）。
- **§3.4 证据合同 v2**：verifier 286 检查（断言重算/SKIP≠PASS/run-id+env-id 跨日志一致/按环境 DLL 一致防污染/硬件一致性/claims→证据引用对账）；对抗 fixtures 12/12 已知坏记录全部被拒。
- **G4 在 ENV A/B 重跑完成**（第三环境限定消除）：ENV A `e97891df`、ENV B `ed7c67a9`，30/30 对账，fitness 0.505→0.602/0.603；A/B：ENV A AMP 有效 1.43×/VRAM−33%；ENV B check_amp 回退被如实标记（ratio=null，"NOT AN AMP MEASUREMENT"）。
- **官方 wheel 周扫**（2026-11-14 13:32Z）：最新 Windows wheel 仍为 torch-2.12.0+rocm7.14.1 → BLOCKED_RELEASE 维持（`release-provenance/raw/official_wheel_rescan_20261114.json`）。
- **重大发现（§4.2）**：上游已在 **8.4.197（PR #26967，2026-11-01）重新设计 check_amp**（未训练模型 + 逐层相对范数 ≤5%，取代 amp_allclose）——PR-C（IoU matcher 替换）对 main 已过时，不再提交重复补丁；转向**验证新 check 在 gfx1151 的表现**（含历史 FAIL 的 warm-training 态），IoU matcher 保留为证据套件（CPU 26/26 + 归档真张量 + GPU 负对照全捕获）。
- **§4.4 真实 AMP 学习**：t16 24 次更新已在生命周期内证明；imagenette2-160 代表性数据集 FP32-vs-AMP 对照运行在 P9 批次 2 中执行。
**Verdict**：GO-A **CONDITIONAL PASS（升级）** · GO-B **CONDITIONAL PASS（升级）** · GO-C **NO-GO（BLOCKED_RELEASE 维持，外部阻塞）**——见 `GO_NO_GO.md` P9 addendum。
**唯一决定性阻塞**：截至 2026-11-14 13:32Z 没有任何官方发行包包含 PR #13437 修复。

## 2. 本日关键发现（按重要性）

1. **AMP 根因闭环（P4/G3）**：Round-3 的 AMP "anomaly" 不是 ROCm kernel bug —— fp16 坐标量化差 0.07–0.76px（逐列 0.0730–0.7606；conf ≤0.0043、cls=0、检测数相同；audit-corrected）被 Ultralytics `check_amp` 的 `allclose(atol=0.5)` 误判 → 静默回退 FP32；结果**随 MIOpen cache 状态翻转**（fresh home 0.233px=PASS，default home 0.760px=FAIL，各 5/5 确定性）。官方 wheel 两态全 PASS（0.264/0.423px 均低于阈值）→ **AMP 在官方 wheel 上可用**（10-epoch 实证：GradScaler 65536→8192 退火语义正确、≥1 真实步进——审计 M5 修正：这证明的是 scaler 语义 + 无异常完成，**非"真实学习"**）。次要新发现：源码构建 MIOpen 3.6.2 的 `EvaluateInvokers` 负计时异常（gfx1151）——**审计 M2 修正：源码构建上重复（4×），官方 3.5.2 罕见但存在（1× 于中止尝试；干净复跑 0×）**，ENV-B 特有的是差值越过 0.5px 阈值 → Issue 草稿已按审计修正。
2. **BN unbiased 语义证实（P2/G1）**：GPU running_var 与 unbiased float64 参考差 6.8e-08（**审计 B-F3 修正：原仅存在于文字，现已持久化复现**——`raw/g1_bn_estimator_probe.json`，6.812e-08，比 biased 参考近 45×）—— phase5_7/5_8 的 "biased estimator 限制" 遗留疑虑正式关闭。
3. **8.4.182 行为变化**（写 harness 时踩到并记录）：`on_before_zero_grad` 回调已不再触发；warmup 首步 lr=0；`trainer.stop=True` 走 final-strip（不可 resume）——中断要用回调抛异常（save_model 在 on_fit_epoch_end 之前执行，得到可 resume 的 epoch+optimizer checkpoint）。
4. **发行链全 PROVEN NEGATIVE**：AMD index 最新 torch-2.12.0+rocm7.14.1（marker=0）；PyTorch 官方零 ROCm Windows wheel；TheRock nightly gfx1151 止于 2026-06-12；无 release tag 晚于 2026-10-19 合并。TheRock main submodule `9ea8cfc5` ⊇ f0a5d266（compare API behind_by=0，非日期推断）。

## 3. 证据索引（都在仓库内，勿改动历史目录 phase5_7/phase5_8）

| 内容 | 路径 |
|---|---|
| 总入口/报告 | `docs/release-closure/{INDEX,FINAL_REPORT,GO_NO_GO,CLAIMS_AND_EVIDENCE,BASELINE_STATE}.md/json` |
| **P8 独立审计** | `docs/release-closure/P8_INDEPENDENT_AUDIT.md`（三视角 verdicts + 发现台账 + 处置 + 复跑证据） |
| G0 溯源 | `release-provenance/{G0_VERDICT,RELEASE_LINEAGE,RELEASE_MATRIX,BINARY_PROVENANCE,WHEEL_MANIFEST,LOADED_DLL_REPORT}` |
| G1 矩阵 | `windows-training-validation/G1_VERDICT.md` + `reports/G1_*.json` + `raw/gtest_nostl_r*.log` |
| G2 生命周期 | `windows-training-validation/G2_VERDICT.md` + `raw/g2_*.json`（7 任务 × 14 测试） |
| G3 AMP | `amp-rca/{ROOT_CAUSE,G3_VERDICT,PRECISION_COMPARISON.csv,MINIMAL_REPRO.py}` + `raw/g3_*.json` |
| G4 | `quality-stability/*` + `performance/*` + `raw/g4_*.json` |
| G5 草稿 | `upstream-readiness/*`（PR-A/B/C/D + MIOpen Issue + Checklist） |
| 平台矩阵 | `platform-matrix/*`（gfx1151 已填，其余 BLOCKED_HARDWARE 模板） |
| 验证合同 | `scripts/verify_release_closure.py`（无 GPU 可跑，218 检查（审计修复扩容后，原 184），当前 exit 0） |

工具链位置（仓库外，本机）：ENV A `pm13437_official`（pristine 官方 wheel）/ ENV B `pm13437_merged` / 源码构建 `C:\b58m`（f0a5d266）/ `C:\b58`（d4b574ac）/ 工作目录 `C:\Users\rocm\Desktop\YOLO_AMD\g2_work`（runs + weights）/ 数据集 `C:\Users\rocm\Desktop\YOLO_AMD\datasets`（含 imagenette2-160，sha256 `64d0c485…`）/ 历史验证 `C:\YOLO_PR13437_PostMerge`。

## 4. 未完成事项（按优先级 — P9 更新）

| # | 事项 | 动作 | 状态 |
|---|---|---|---|
| 1 | ~~P8 独立二审~~ | 已执行（2026-11-14 晚） | ✅ 完成 |
| 2 | ~~env B DLL 恢复~~ | 已解决（2026-11-14 19:39 restore 哈希过；P9 批次内 swap-in/restore 双向再验证） | ✅ 完成 |
| 3 | 官方 wheel 扫描 | **2026-11-14 13:32Z 已扫**：最新仍为 torch-2.12.0+rocm7.14.1（`release-provenance/raw/official_wheel_rescan_20261114.json`）；出现 >7.14.1 后按 `RELEASE_LINEAGE.md` §4 清单重跑 G0→G1/G2/G3 | ⏳ 外部事件 |
| 4 | 上游提交 | **授权变更：mission P9-P12 §1 明确授权提交**（草稿限定被取代）；PR-C 已被上游 8.4.197 (#26967) 取代——改为提交 gfx1151 验证数据 Issue/评论 + EvaluateInvokers Issue；不提交重复补丁 | ⏳ P12 执行中 |
| 5 | 跨架构 | gfx1100/gfx1200/Linux 接入后按 `platform-matrix/*` 模板命令执行 | ⏳ BLOCKED_HARDWARE |
| 6 | ~~G4 在 ENV A/B 重跑~~ | **P9 完成**：ENV A/B 各 30ep 长训 + 匹配 A/B，全部带 in-process DLL probe + epoch 对账 + CSV 保全 | ✅ 完成 |
| 7 | ~~g3 harness 溯源升级~~ | **P9 完成**：新 g3 harness（paired-boxes/learning/repro）全部自带 dll_provenance + cache-home 记录 | ✅ 完成 |
| 8 | ~~PR-C matcher CPU 仿真~~ | **P9 完成**（26/26 + 归档真张量 5/5 + GPU 负对照 5/5 全捕获）；PR-C 本身被 #26967 取代 | ✅ 完成 |
| 9 | ~~8.4.197+ 新 check_amp 在 gfx1151 验证~~ | **P9 完成**：ENV A 官方 wheel 全 PASS（default 9.1s + warm 态，8.4.212 下 amp 有效）；**ENV B 混合态确定性崩溃 3/3**（hipErrorInvalidKernelFile，逐层 fp16 重算路径；根因 = 混合 bin 目录 fdb 不可读 → 运行时编译产生坏 kernel 对象），且 #26967 移除了异常守卫 → 探针异常会炸训练而非降级 AMP——上游健壮性 PR 草稿就绪（`upstream-readiness/patches/CHECKAMP_ROBUSTNESS_PR.md`） | ✅ 完成 |
| 9b | **ENV B DLL restore 待执行** | 4 个 HIP teardown 僵尸锁住 MIOpen.dll（WinError 32，与 P8 事件同型；僵尸最终自清）；恢复命令：`python windows-training-validation/scripts/envb_dll_swap.py --action restore --state-file windows-training-validation/environment/ENVB_DLL_STATE.json`（脚本自带双向哈希验证） | ⏳ 僵尸清除后执行 |
| 10 | **P10 全 7 任务矩阵复跑**（P9 新增） | 新 harness × 7 任务 FP32（ENV B patched）+ workers 2/4 + amptrack ENV B——批次 2 执行中 | ⏳ 批次 2 |
| 11 | **EvaluateInvokers 最小复现**（P9 新增） | `g3_evaluateinvokers_repro.py`（无 Ultralytics、逐 config 子进程、fresh-cache Find 路径）——批次 2 执行中；结果决定 Issue 形态 | ⏳ 批次 2 |

## 5. 复现快速命令（下次会话直接用）

```bash
cd C:/Users/rocm/Desktop/YOLO_AMD/Ultralytics-Windows-ROCm-Training-RCA
python -I scripts/verify_release_closure.py            # 证据完整性（无需 GPU）
# G1（例：ENV B）：
python -I windows-training-validation/scripts/envb_dll_swap.py --action swap-in --state-file windows-training-validation/environment/ENVB_DLL_STATE.json
python -I windows-training-validation/scripts/g1_runner.py --python "C:/Users/rocm/miniconda3/envs/pm13437_merged/python.exe" --legs envB_stl --mode stl --repeat 3 --raw-dir windows-training-validation/raw --report-dir windows-training-validation/reports
python -I windows-training-validation/scripts/envb_dll_swap.py --action restore --state-file windows-training-validation/environment/ENVB_DLL_STATE.json
# G2（例：detect）：
cd C:/Users/rocm/Desktop/YOLO_AMD/g2_work && python C:/Users/rocm/Desktop/YOLO_AMD/Ultralytics-Windows-ROCm-Training-RCA/windows-training-validation/scripts/g2_runner.py --python "C:/Users/rocm/miniconda3/envs/pm13437_merged/python.exe" --task detect --data coco8.yaml --weights yolo26n.pt --infer-source "C:/Users/rocm/Desktop/YOLO_AMD/datasets/coco8/images/val" --raw-dir "C:/Users/rocm/Desktop/YOLO_AMD/Ultralytics-Windows-ROCm-Training-RCA/windows-training-validation/raw"
```

## 6. 陷阱备忘（本日实际踩过的）

- Git Bash 里 `python` 是 miniconda base——**必须显式传 env 的 python.exe 路径**给 runner 的 `--python`。
- 跑 GPU 脚本**不要用 `-I`**（PyYAML 在 user-site，会被隔离掉）；G1/G0 脚本不依赖 yaml 所以当时没炸。
- 后台长跑必须 `-u` + 重定向文件（否则管道缓冲看不到进度）；结束后 `tasklist` 查残留 python——本机 HIP 退出清理会偶发挂起变僵尸（约 1/20），僵尸不影响新进程但锁 DLL 写替换。
- S3 慢下载用 8 段 Range 并行 + 字节精确校验（SIZE 必须先从响应头 `Content-Range` 取真实值——本日因猜 SIZE 多耗 30 分钟）。
- 硬件：iGPU 共享内存 78GB，conv 冷编译 ~30-60s/kernel；MIOpen cache 用 USERPROFILE 重定向隔离。

## 7. P16 附录(2026-11-15,三里程碑收官批次)

- **远程状态冻结**:`P16_BASELINE.md`(两 PR open+mergeable,CI 15/6/0;issue #14 仍 0 回复;#15862 仍无维护者回应)。
- **M1 修复**:#27198 描述与 live diff 对齐(2 测试)+ FDB 因果断言按 P13 否证结论淡化;#27203 no-NVML fallback 契约加固(mem_get_info 真实 free-memory 判据 / 索引存在性与去重 / util 判据不可测时显式披露警告)——自审发现严格"util>0→[]"语义会让上游 test_cuda.py(`min_util_fraction=0.3`)在 AMD 上重新全 SKIP,回归 PR 头版目标,已改为披露式选择;推送经 Git Data API(force=false 快进,git-over-HTTPS 当日故障)。
- **M2 重验**:whl-multi-arch 最新仍 `torch-2.12.0+rocm7.14.1`;whl-next 最新仍 `rocm_sdk_core/libraries-10.1.0` + `torch-2.14.0+rocm10.1.0`(无 10.2.0);`rocm_sdk_libraries-10.1.0` 重下载 SHA256 与 P15 审计副本逐字节一致,内嵌 MIOpen.dll(496,074,240 B,`266d716b…`,版本串 `3.6.1.39d8d603`,`miopen_initializer_list`=0)→ **BLOCKED_RELEASE 维持**,缺口仍为"2026-10-19 之后的 MIOpen→Windows SDK→发布周期"。详见 `P16_OFFICIAL_WHEEL_BINARY_AUDIT.md`。
- 陷阱新增:pytest 传测试路径须用 `C:/` 形式(`::` 节点符与 Git Bash `/c/` 路径不兼容);ruff/pytest 相对路径调用必须同命令内 `cd` 到 worktree。
