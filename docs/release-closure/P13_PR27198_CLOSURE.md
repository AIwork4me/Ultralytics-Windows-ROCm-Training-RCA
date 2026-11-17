# P13.1 — Ultralytics PR #27198 Closure

日期:2026-11-15 · 执行:MISSION P13 TRACK A · PR:https://github.com/ultralytics/ultralytics/pull/27198

## 状态

**PASS(工程闭环)— 等待上游 Tests CI 完成与维护者复审**(未合并,不视为上游解决)。

| 项 | 值 |
|---|---|
| PR head(推送后) | `124de39`(= `3f6076c` 修复提交 + UltralyticsAssistant 自动格式化 1 commit) |
| 基点 | 上游 main `d0cfceaf`(8.4.213)— 与 main 同步 |
| Diff | **2 文件,+161/−7,全 LF,零 CR** |
| 修复前 PR diff | 2 文件 +1311/−1249(checks.py 被 CRLF 全文件改写 — 本次推送根除) |
| Docs CI | **success**(D103 已修复:新测试函数全部带 docstring) |
| CLA | **success**(所有者本人 2026-11-14T23:47Z 亲自签署,非代签) |
| Tests CI | in_progress(推送后运行中;windows/ubuntu/macos/arm/py3.8 兼容矩阵) |
| AMD_GPU / GPU CI | skipped(上游硬件门控按设计跳过 — 本地 gfx1151 实机测试补位,见下) |

## 评审发现 → 修复

**MEDIUM(UltralyticsAssistant 线级评论,checks.py:1081)**:守卫块始于 `DetectionModel(...).to(device)` 之后 — 探针模型**构建**或**设备搬移**失败(内存紧张 OOM、损坏 runtime)仍会逃逸 `check_amp` 并炸掉训练 setup,与本 PR 要消除的失败模式相同。

**根因**:#26967 重写 check_amp 时只保留了 forward 级守卫(我们的第一版提交沿袭了同样的边界),探针生命周期中 forward 之前的两个阶段未覆盖。

**修复(3f6076c)**:探针全生命周期(构建 → hook 注册 → `.to(device)` → forward)纳入单个 `try / except Exception` → `LOGGER.error`(含异常类型+消息)→ `return False`(AMP 禁用、训练继续)。`KeyboardInterrupt`/`SystemExit` 是 `BaseException`,继续传播。健康路径零改动。

## 异常分类策略(上游补丁内 vs 外)

上游补丁保持 **backend-neutral 最小守卫**,不做硬编码异常映射(分类依据详见本仓库 P9/RCA 证据):

| 失败类 | 探针期表现 | 行为 | 归属 |
|---|---|---|---|
| AMP_NUMERICAL_UNSAFE | 无异常,`all(close)` False | 既有路径:LOGGER.error + False(#26967 原有,未改) | Ultralytics |
| PROBE_CONSTRUCTION_FAILURE | DetectionModel() 抛 | 新守卫:日志+False,训练以 FP32 继续 | 本 PR |
| GPU_DEVICE_TRANSFER_FAILURE(含 OOM) | `.to(device)` 抛(OOM 是 RuntimeError 子类) | 新守卫:日志+False | 本 PR |
| AMP_SPECIFIC_OPERATOR_FAILURE / probe forward 抛 | 新守卫:日志+False | 本 PR |
| GPU_RUNTIME_INTEGRITY_FAILURE(如 hipErrorInvalidKernelFile) | 以上任一阶段抛 | 守卫如实验行 + 日志保留原始异常;**运行时缺陷归 ROCm/PyTorch 修复**(不得在 Ultralytics 内掩盖) | ROCm #15862 / P13.2 |
| GPU_OUT_OF_MEMORY | OOM → False(探针仅数百 MB;若训练期真 OOM 将在训练自身分配点诚实失败) | 本 PR |
| USER_INTERRUPTION | BaseException → 传播(Ctrl+C 不被吞) | 本 PR |
| UNKNOWN_ACCELERATOR_FAILURE | `except Exception` 兜底:日志+False(诊断含类型+消息) | 本 PR |

**下游 trainer 是否需要改**:不需要。`trainer.py:421` 只消费布尔 `check_amp(self.model)`;分类信息由守卫日志承载(类型+消息),最小 diff 原则下不动 trainer。

## 测试证据(本机 gfx1151 实测)

`tests/test_check_amp_probe_exception.py` — 7 passed(raw:`windows-training-validation/raw/p131_pr27198_pytest_gfx1151.log`,env:`p131_pr27198_pytest_env_identity.txt` = Python 3.13.13 / torch 2.12.0+rocm7.14.0 / AMD Radeon 8060S / Windows 11 26200):

| 用例 | 覆盖 | 断言 |
|---|---|---|
| construction_failure_returns_false | PROBE_CONSTRUCTION_FAILURE | False + 日志,CPU 可跑 |
| transfer_failure[RuntimeError/OutOfMemoryError] | DEVICE_TRANSFER/OOM | False + 日志,CPU 可跑 |
| forward_failure_returns_false | probe forward 抛(构造期 stride pass (1,3,256,256) 不受影响) | False + 日志,CPU 可跑 |
| repeated_invocation_after_failure | 清理/重入 | 两次均 False、无残留状态 |
| user_interruption_propagates | KeyboardInterrupt | 传播(非吞) |
| passes_on_healthy_accelerator | CASE A 正控(真实 GPU、无 mock 探针) | True |

设计要点:**故障注入测试 CPU 可跑**(在 DetectionModel 构建/搬移/forward 边界注入),普通 CI runner 会真正执行守卫路径而非静默 SKIP;只有健康正控需要真硬件。测试通过 `_FakeAcceleratorModel`(声称 device.type=="cuda" 的桩)+ patch `torch.cuda.get_device_name` 保证跨主机确定性。

## CASE A–H 映射

- A 健康加速器 → `passes_on_healthy_accelerator`(真 GPU)PASS
- B 探针 forward 抛 → `forward_failure` PASS(修复前行为:P9 实机 ENV B 崩溃 3/3,`g3_checkamp84212_ENV_B_patched.json`)
- C 构建抛 → `construction_failure` PASS
- D `.to(device)` 抛 → `transfer_failure` PASS
- E runtime 损坏 → P9 实机证据(hipErrorInvalidKernelFile,ENV B)+ 守卫行为由 B/C/D 等价覆盖;根因 RCA = P13.2
- F AMP 数值失配 → `all(close)` 既有路径(未改;P9 已验证)
- G 用户中断 → `user_interruption_propagates` PASS
- H 真 OOM → `transfer_failure[OutOfMemoryError]` PASS(探针级);训练期真 OOM 由 torch 在分配点诚实报错(设计边界,见上表)

## Diff 卫生修复(本次推送的关键工程决策)

上一轮推送的 checks.py blob 含 **1256 个 CR**(CRLF 全文件改写,diff 膨胀至 +1311/−1249,评审 diff_hunk 证实)。本次:本地克隆 `core.autocrlf=input` 重建,基于上游最新 main `d0cfceaf` 单提交推送(`--force-with-lease` 锁定旧 head `7f43b92`),推送后核验 blob CR=0。bot 随后追加 1 个格式化提交(AGPL 头 + docstring 重排,LF),即当前 head `124de39`。

## 遗留 / 边界

1. `torch.cuda.get_device_name` 留在守卫外(设计决策):trainer 调用路径中模型已在设备上,枚举失败意味着 runtime 坏到会在更早处诚实报错 — 守卫范围以"探针生命周期"为准,不扩到设备枚举。
2. AMP 数值失配路径(#26967 `all(close)`)未改 — 非本 PR 范围。
3. 上游 Tests CI 进行中(矩阵 10 项);AMD_GPU skipped 为上游硬件门控设计,gfx1151 实机证据在本地(此为如实状态,非全绿声明)。
4. 合并由所有者授权后人工判断(不代签、不代并)。

## 交付链接

- PR:https://github.com/ultralytics/ultralytics/pull/27198
- 评审回复(根因+SHA+证据+边界):https://github.com/ultralytics/ultralytics/pull/27198#discussion_r4576261378
- 本地证据:`windows-training-validation/raw/p131_pr27198_pytest_gfx1151.log`、`p131_pr27198_pytest_env_identity.txt`、`g3_checkamp84212_ENV_B_patched.json`(修复前实机崩溃)、`g3_checkamp84212_ENV_A_official.json`(健康正控)
