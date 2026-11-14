# HANDOFF — Release-to-Upstream Closure 交接文档

写于 2026-11-14 收工 · 分支 `work/windows-rocm-training-release-closure` · HEAD `051b4d9`（已推送 origin）

## 1. 一分钟状态

**任务**：Windows ROCm YOLO 训练 Release-to-Upstream Closure（P0–P8，十个 todo 大项）。
**已完成**：P0–P7 全部实质完成并有证据；P8 写完 FINAL_REPORT/GO_NO_GO/CLAIMS/验证合同（184 检查全过）。
**Verdict**：GO-A **CONDITIONAL PASS** · GO-B **CONDITIONAL PASS** · GO-C **NO-GO（BLOCKED_RELEASE，外部阻塞）**。
**唯一决定性阻塞**：截至 2026-11-14 没有任何官方发行包包含 PR #13437 修复。

## 2. 本日关键发现（按重要性）

1. **AMP 根因闭环（P4/G3）**：Round-3 的 AMP "anomaly" 不是 ROCm kernel bug —— fp16 坐标量化差 0.15–0.76px（conf ≤0.004、cls=0、检测数相同）被 Ultralytics `check_amp` 的 `allclose(atol=0.5)` 误判 → 静默回退 FP32；结果**随 MIOpen cache 状态翻转**（fresh home 0.233px=PASS，default home 0.760px=FAIL，各 5/5 确定性）。官方 wheel 两态全 PASS → **AMP 在官方 wheel 上真实可用**（10-epoch 实证：GradScaler 65536→8192 退火、真实步进、fitness 0.662→0.696）。次要新发现：源码构建 MIOpen 3.6.2 的 `EvaluateInvokers` 负计时异常（仅 ENV B，gfx1151）→ 已写 Issue 草稿。
2. **BN unbiased 语义证实（P2/G1）**：GPU running_var 与 unbiased float64 参考差 6.8e-08 —— phase5_7/5_8 的 "biased estimator 限制" 遗留疑虑正式关闭。
3. **8.4.182 行为变化**（写 harness 时踩到并记录）：`on_before_zero_grad` 回调已不再触发；warmup 首步 lr=0；`trainer.stop=True` 走 final-strip（不可 resume）——中断要用回调抛异常（save_model 在 on_fit_epoch_end 之前执行，得到可 resume 的 epoch+optimizer checkpoint）。
4. **发行链全 PROVEN NEGATIVE**：AMD index 最新 torch-2.12.0+rocm7.14.1（marker=0）；PyTorch 官方零 ROCm Windows wheel；TheRock nightly gfx1151 止于 2026-06-12；无 release tag 晚于 2026-10-19 合并。TheRock main submodule `9ea8cfc5` ⊇ f0a5d266（compare API behind_by=0，非日期推断）。

## 3. 证据索引（都在仓库内，勿改动历史目录 phase5_7/phase5_8）

| 内容 | 路径 |
|---|---|
| 总入口/报告 | `docs/release-closure/{INDEX,FINAL_REPORT,GO_NO_GO,CLAIMS_AND_EVIDENCE,BASELINE_STATE}.md/json` |
| G0 溯源 | `release-provenance/{G0_VERDICT,RELEASE_LINEAGE,RELEASE_MATRIX,BINARY_PROVENANCE,WHEEL_MANIFEST,LOADED_DLL_REPORT}` |
| G1 矩阵 | `windows-training-validation/G1_VERDICT.md` + `reports/G1_*.json` + `raw/gtest_nostl_r*.log` |
| G2 生命周期 | `windows-training-validation/G2_VERDICT.md` + `raw/g2_*.json`（7 任务 × 14 测试） |
| G3 AMP | `amp-rca/{ROOT_CAUSE,G3_VERDICT,PRECISION_COMPARISON.csv,MINIMAL_REPRO.py}` + `raw/g3_*.json` |
| G4 | `quality-stability/*` + `performance/*` + `raw/g4_*.json` |
| G5 草稿 | `upstream-readiness/*`（PR-A/B/C/D + MIOpen Issue + Checklist） |
| 平台矩阵 | `platform-matrix/*`（gfx1151 已填，其余 BLOCKED_HARDWARE 模板） |
| 验证合同 | `scripts/verify_release_closure.py`（无 GPU 可跑，184 检查，当前 exit 0） |

工具链位置（仓库外，本机）：ENV A `pm13437_official`（pristine 官方 wheel）/ ENV B `pm13437_merged` / 源码构建 `C:\b58m`（f0a5d266）/ `C:\b58`（d4b574ac）/ 工作目录 `C:\Users\rocm\Desktop\YOLO_AMD\g2_work`（runs + weights）/ 数据集 `C:\Users\rocm\Desktop\YOLO_AMD\datasets`（含 imagenette2-160，sha256 `64d0c485…`）/ 历史验证 `C:\YOLO_PR13437_PostMerge`。

## 4. 未完成事项（按优先级）

| # | 事项 | 动作 | 状态 |
|---|---|---|---|
| 1 | **P8 独立二审** | 已派审计 agent（三视角对照 raw 证据）但被取消；下次会话重新执行。审计提示词可复用 FINAL_REPORT 中 Reviewer A/B/C 检查清单 | ⏳ 待做 |
| 2 | **env B DLL 恢复** | 3 个僵尸 python（PIDs 29152/10940/43404，不可杀）锁住 MIOpen.dll；**重启机器**后跑 `python -I windows-training-validation/scripts/envb_dll_swap.py --action restore --state-file windows-training-validation/environment/ENVB_DLL_STATE.json`，验证哈希 `e97891df…` | ⏳ 等 Owner 重启 |
| 3 | 官方 wheel 扫描 | 每周检查 repo.amd.com index 是否出现 >7.14.1 版本；出现后按 `RELEASE_LINEAGE.md` §4 清单重跑 G0 → G1/G2/G3 全套（harness 全部现成，改 `--python` 参数即可） | ⏳ 外部事件 |
| 4 | 上游提交 | 4 PR 草稿 + 1 Issue 草稿等 Owner 审阅批准（任务边界：未经批准不得向上游提交/评论） | ⏳ Owner |
| 5 | 跨架构 | gfx1100/gfx1200/Linux 接入后按 `platform-matrix/*` 模板命令执行 | ⏳ BLOCKED_HARDWARE |

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
