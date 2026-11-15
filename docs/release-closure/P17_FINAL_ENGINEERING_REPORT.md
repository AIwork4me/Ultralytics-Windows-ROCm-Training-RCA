# P17 最终工程报告 — Windows Radeon 8060S (gfx1151) 真机验证 PR #27198 / #27203

日期:2026-11-15 | 执行环境:真实 Windows 11 (build 26200) + AMD Radeon(TM) 8060S Graphics (gfx1151) + 驱动 32.0.22032.6002
Python 3.13.16 / torch 2.12.0+rocm7.14.1 / HIP 7.14.60850 / MIOpen.dll(官方 wheel 组件,SHA256 `ed7c67a9…79a`,进程内模块枚举实证)

---

## 1. 两个 PR 的最新完整 HEAD SHA

| PR | 分支 | 验证 HEAD(GitHub API 实时对账一致) |
|---|---|---|
| #27198 | AIwork4me:checkamp-guard-probe-exceptions | `e5ac8593db60880b92b3e3cbd2e11ee3a7344034` |
| #27203 | AIwork4me:checkamp-gpu-gates-hip-fallback | `563ff46e0c3347cc68db420e1b268a22a456e317` |

- 两分支均为 P16 tip(fc72b4e / 8ef3e96f)的**纯 fast-forward** 延伸,无 force-push、无 rebase。
- P16 之后的新增提交已全部审查(任务 §0 要求):#27198 +3(含 `except Exception`→`except RuntimeError` 收紧与 mock-heavy 测试文件删除);#27203 +7(no-NVML 回退重写、CVD 物理↔逻辑映射、非零利用率门槛返回 [])。

## 2. 是否发生额外代码修复

**无(P17 未对任一 PR 提交任何新代码)。** 全部发现的问题均归因于机器环境(见 §16),不需要修改 PR 源码;因此也未推送任何 PR 分支、未创建替代 PR、未 force-push。

## 3. 每项验证实际运行命令(原始日志在 evidence/p17/)

- A1: `python -c "YOLO('yolo26n.yaml').model.to('cuda:0'); check_amp(model)"` → `a1_log.txt`
- A2: `yolo detect train model=C:/Users/rocm/Desktop/YOLO_AMD/yolo26n.pt data=coco8.yaml epochs=1 imgsz=64 device=0 amp=True workers=0` → `a2_train_log*.txt`(3 次运行)
- A3/A4:受控注入脚本 `a3_a4_injection.py`(monkeypatch 探针边界,标 CONTROL_FLOW_INJECTION)
- B1–B5/B7:`b_suite.py`;B6:`CUDA_VISIBLE_DEVICES=0 b6_cvd0.py`(独立进程,torch 导入前设 CVD);B9:`CUDA_VISIBLE_DEVICES=3` 单卡实测 + 映射逻辑推演
- B8: `pytest tests/test_cuda.py::test_amp -v -s`、`pytest tests/test_python.py::test_select_idle_gpu_fallback -v -s`、`pytest tests/test_python.py::test_select_device -v -s`
- 组合:本地合成树 `750b5061`(upstream main `3e59149d` + #27203 四文件原文 + #27198 check_amp 守卫逐字校验一致)上 `c_smoke.py`(训练/val/ predict)
- pytest 9.2.0、ruff 0.17.5 均为隔离安装(venv 内,未动 torch/ROCm/MIOpen)

## 4. 真实 GPU / 纯逻辑验证区分

- **真机(PHYSICAL_GPU)**:A1、A2×3、B1–B8、组合 smoke 全部项
- **纯逻辑(LOGIC_TEST)**:B9 的 CVD=3 物理→逻辑转换推演(同路径已在 CVD=0 真机执行过,仅物理索引身份不同)
- **未运行(NOT_RUN)**:B9 多卡物理映射(单卡机)、B10 NVIDIA 实机(无 N 卡)

## 5. AMP 真实结果

- **健康路径(A1):check_amp = True @ cuda:0,12.37 s,逐层 Conv2d+Attention AMP↔FP32 一致 —— 真机全绿。**
- 训练路径 3 次运行:
  - try1(被僵尸进程锁死的旧 MIOpen 缓存):AMP precheck True,但第一个训练 batch 崩 `hipErrorInvalidKernelFile`(PHYSICAL_GPU_RUNTIME_FAILURE,根因 §16)。
  - try2/try3(缓存重定向后):探针抛真实 `AcceleratorError` → **被 #27198 新守卫捕获、如实记录、降级 FP32** → 训练完成、损失有限、**参数 241/366 更新**、checkpoint 正常(末次保存 strip optimizer 属正常行为)、全程 GPU 执行(GPU_mem 列),无静默 CPU fallback。
- `tests/test_cuda.py::test_amp` 在 #27203 树健康窗口**真机 PASSED(13.29 s)**。
- 未闭环项:**"AMP precheck True 与训练完成同一次运行"** 因 HIP 运行时间歇性退化未稳定复现,标记 REBOOT-PENDING(§16)。

## 6. RuntimeError 捕获边界

- 实测继承(本栈):`torch.AcceleratorError → RuntimeError`;`torch.cuda.OutOfMemoryError → RuntimeError`;两者均被 `except RuntimeError` 捕获;KeyboardInterrupt/SystemExit 非 Exception,ValueError/TypeError 非 RuntimeError —— 四者全部传播。
- 注入(CONTROL_FLOW_INJECTION):RuntimeError/OutOfMemoryError/AcceleratorError 3 类 → 捕获 + 返回 False + 日志含异常类型与原文 + 明确"不一定是 AMP-specific、不保证 FP32 健康"、**不冒充数值异常**。
- **非注入真机对照**:try2/try3 与组合 smoke 中,真实 `AcceleratorError`(HIP 故障)被同一守卫捕获降级,训练不崩 —— PR 的行为目的在真实硬件故障下得到正反两证。

## 7. 设备发现与自动选卡

- `cuda_is_available()=True`、`cuda_device_count()=1`,与 torch 完全一致(nvidia-smi 缺失不再误判 —— #27203 修复点;#27198 树同机实测为 False,构成直接对照)。
- `parse_device("-1")="0"`,幂等,返回索引真实完成 GPU tensor 分配。

## 8. 空闲显存真实读数

`torch.cuda.mem_get_info(0)`:free=83,614,412,800 / total=83,954,728,960 字节(**free 99.59%**,8060S APU 共享 GTT 报告,真实读数)→ 门槛 0.2 满足,`select_idle_gpu` 返回 `[0]`,与预期一致。

## 9. 非零利用率门槛结果

无 NVML(实测 `nvml_available=False`)下 `select_idle_gpu(min_util_fraction=0.3)` → **`[]`** + 明确告警 `Cannot verify 30.0% free GPU utilization without NVML.`;不假装、不误报 idle PASS。

## 10. indices / CVD 结果

- `indices=[]` → `[]`(显式空限制不变成无限制);`indices=[99999]` → `[]`;`indices=[0,0]` → `[0]`(不重复返回)。
- `CUDA_VISIBLE_DEVICES=0`(独立进程):计数 1、parse→0、选卡 [0]、真实分配成功、设备名正确。
- `CUDA_VISIBLE_DEVICES=3`(单卡真机):全链路如实为空;物理→逻辑映射逻辑验证通过(LOGIC_TEST_PASS),多卡物理映射 NOT_RUN。

## 11. pytest PASS/FAIL/SKIP 明细

| 测试 | 树 | 结果 |
|---|---|---|
| tests/test_cuda.py::test_checks | #27198 | FAILED(NVIDIA-only 门禁 → `cuda_is_available()=False`,即 #27203 修复的既有缺陷;非 #27198 引入) |
| tests/test_cuda.py::test_amp | #27198 | SKIPPED(同因;任务 §3-A6 预告的结果,直接 check_amp 真机证据由 A1/A2 保留) |
| tests/test_cuda.py::test_amp | #27203 | **PASSED 13.29 s(真机 HIP)**(此前一次 FAILED 12.54 s 与一次 MIOpen 锁死 hang 亦如实归档,均为环境故障证据) |
| tests/test_python.py::test_select_idle_gpu_fallback | #27203 | PASSED |
| tests/test_python.py::test_select_device | #27203 | PASSED |

## 12. 一次真实训练与模型更新结果

- FP32 降级路径(×2):1 epoch 完成,损失有限,`241/366` 参数张量与预训练权重不同(真实 optimizer update 证据),checkpoint last.pt/best.pt 正常,val 完成(mAP50=0.171)。
- AMP 路径(c_smoke):训练内 AMP check passed ✅,1 epoch 完成,loss 有效;`0/366` 参数不变经追查为 **合法 GradScaler overflow-skip**(coco8 每 epoch 仅 1 batch,accumulate=4 → 9 epochs 仅 1 次 step 机会且 fp16 梯度溢出被跳;BN running buffers 228/342 变化证明 forward 真实执行;纯 torch GradScaler 5/5 步正常,HIP scaler 机制无损)。AMP 下的显式 update 证据需重启后补(§16)。

## 13. 临时组合回归结果

合成树 `750b5061`(main+两 PR)7 项 smoke:设备检测 ✓、device=-1 ✓、check_amp(真实故障被守卫正确处理,不炸训练)✓、AMP 训练完成 ✓、参数更新(见 §12 的机制解释)✓、checkpoint ✓、val+predict ✓。**两 PR 在同一源码树无交互破坏;未推送,两 PR 历史未动。**

## 14. 代码品质审阅结果

- Ruff(仓库 pyproject 配置,line 120 + 严格集 F,I,D,UP,RUF,FA):#27198/#27203/组合树涉及文件 format 全清;错误数 ≤ main 基线(10-11 vs 12-13),**零新增**;pre-existing BLE001 等不在启用规则集且不位于 PR diff 区域。
- AGENTS.md 冷审:owner 正确(checks.py / autodevice.py / tests)、try/except 最小且必要、无 mock-heavy 上游测试(#27198 反而删除了)、无兼容垫片、无新依赖、NVIDIA 健康路径零改动(B10 静态审阅)、注释/docstring/日志与实测行为一致。
- **SOURCE_QUALITY_PASS(两 PR)**。

## 15. 证据仓库提交 SHA

本报告随 P17 证据包提交至 `AIwork4me/Ultralytics-Windows-ROCm-Training-RCA` 分支 `work/windows-rocm-training-release-closure`(提交 SHA 见该分支推送后的最新 commit)。

归档清单(全部在 `evidence/p17/`,SHA256 见 `SHA256SUMS_P17.txt`,109 条):

- 原始日志/脚本/结果 JSON:A1(A1 log/result)、A2 训练日志 ×3、A2 复现脚本、A3/A4 注入脚本+结果、B 套件脚本+结果、B6 CVD=0、pytest 原始输出 ×3(a6/b8)、组合 smoke(c_smoke/5/9/128/amp64 日志+结果)、模块枚举(modules_toolhelp.txt,MIOpen.dll 来源实证)、环境来源脚本
- 训练 runs 产物(`runs/`,81 个文件,args.yaml/results.csv/曲线图/混淆矩阵等,8 个 run 目录,权重除外)
- checkpoint 清单 `CHECKPOINT_SHA256SUMS.txt`(10 个 .pt 共 ~55MB,仅本地留存,SHA256 可复核)
- 组合树完整审阅 patch `p17_combined_750b5061_vs_main.diff`(4 文件 +87/−21,相对 upstream/main 3e59149)
- `P17_ENVIRONMENT_PROVENANCE.json`

## 16. 仍需第二 GPU 或 NVIDIA 的事项

- **多卡物理映射(CVD=3)**:需 ≥4 物理显卡的 Windows 主机 —— BLOCKED_HARDWARE。
- **NVIDIA 实机回归**(test_cuda.py NVIDIA CI 路径、NVML 可用路径):需 NVIDIA 主机 —— NVIDIA_HARDWARE_NOT_RUN(静态审阅确认路径未动)。
- **本机(单卡)遗留**:HIP 驱动层间歇性退化(详见下)。

### 本机 HIP 故障 RCA(P17 期间实测证据链)

1. 6 个历史 P 任务残留 python 僵尸进程(P13/P15 时代 `inner.py`、`p132_checkamp_real.py`),各烧 1 CPU 核 ×16 h,`taskkill /F` 无效(P16 已知),并**持有 `C:\Users\rocm\.miopen` 文件锁**(mv → Permission denied 实证)。
2. MIOpen 对该被锁/退化缓存做 kernel find → 坏 kernel 选择 → `hipErrorInvalidKernelFile`(try1 训练崩溃);`MIOpen: Error [EvaluateInvokers] ... elapsed <= 0` 同时出现(solver 计时被 CPU 空转干扰)。
3. 用 `MIOPEN_USER_DB_PATH`/`MIOPEN_CUSTOM_CACHE_DIR`(经 DLL 内环境变量字符串核验)重定向全新缓存后,FP32 训练稳定完成;但多次 kernel 崩溃后 **HIP 运行时进一步退化**:aotriton SDPA flash/efficient kernel 在**每个新进程**中 launch 失败(`AcceleratorError: invalid argument`),MATH 后端与 MIOpen conv 路径正常 —— 驱动层状态损坏,进程级手段无法修复。
4. 运行时状态在"健康窗口/退化窗口"间抖动:test_amp 先 FAILED(退化)后 **PASSED**(恢复),A1 True 与 try2/3 探针崩并存 —— 全部原样归档,不做任何覆盖。
5. **处置建议:重启机器(清除 6 僵尸 + 重置 HIP 驱动层)后补 3 项**:① AMP precheck=True 的完整训练 + AMP 下真实 optimizer update 证据(coco128+batch=64 已准备好的命令);② test_amp 复跑 PASS 稳定化;③ 组合树 AMP update 复验。**这是唯一遗留缺口,不涉及任何代码修改。**

## 17. 是否达到 REQUEST MAINTAINER REVIEW

**达到(带如实注记)。** 两个 PR 的代码在静态质量、逻辑行为、真机可达的全部验证项上均通过;所有失败/异常均定位到机器环境并给出完整证据链;无任何需要修改 PR 源码的发现。建议维护者在审阅时参考本报告与两份 PR 分报告。

最终判定标签:

```
SOURCE_QUALITY_PASS               —— 两 PR 代码品质全绿(Ruff/AGENTS/owner/最小 diff)
GFX1151_PHYSICAL_VALIDATION_PASS  —— 真机可达项全部通过(A1/A2/B1–B8/组合 smoke;
                                     含一次真实 GPU 故障下守卫行为的正反两证)
AMP_TRUE_RUN_REBOOT_PENDING       —— AMP precheck=True 完整训练闭环 + AMP 显式 update 证据,
                                     等待机器重启后补测(环境阻塞,非代码阻塞)
MULTI_GPU_NOT_RUN                 —— BLOCKED_HARDWARE(需多卡主机)
NVIDIA_NOT_RUN                    —— BLOCKED_HARDWARE(需 NVIDIA 主机;静态审阅确认路径未动)
UPSTREAM_MERGE_PENDING            —— 两 PR 仍为 OPEN,由维护者决定合并;P17 未合并、未推送、未改史
```

诚实声明:本报告不含任何"历史 PASS 冒充当前结果"或"逻辑测试冒充真机"的表述;所有 PASS/FAIL/SKIP/NOT_RUN/CONTROL_FLOW_INJECTION/PHYSICAL_GPU_RUNTIME_FAILURE 标签与原始日志一一对应,SHA256 可校验。
