# P15 最终工程报告（中文，2026-11-15）

按任务书 §19 的 21 项结构给出证据化结论。状态词汇严格使用：PASS / FAIL / IN_PROGRESS / BLOCKED_RELEASE / BLOCKED_HARDWARE / BLOCKED_MAINTAINER / BLOCKED_RUNNER / BLOCKED_INDEPENDENT_USER_TEST / INCONCLUSIVE / NOT_RUN。不以未来预期结果冒充现状。

## 1. 实际分支与完整 HEAD SHA

| 仓库/分支 | HEAD（P15 结束时实测） |
|---|---|
| RCA `work/windows-rocm-training-release-closure` | 基线冻结时 `9c30131a8a24a274e67ec0734a4e2a32d3d7ab8d`（远端=本地，干净树）；P15 交付物提交见本文末尾（追加式，无改写） |
| ultralytics PR #27198（fork 分支 `checkamp-guard-probe-exceptions`） | `fc72b4eb85d654e3268a5bee1bc4beebc8704b13`（P15 新增；此前 tip `090e378`） |
| ultralytics PR #27203（fork 分支 `checkamp-gpu-gates-hip-fallback`） | `a1be048`（bot MEDIUM 修复后；首个提交 `78b5b15`） |
| upstream ultralytics main | `d0cfceaf`（8.4.213；`checks.py` blob `bfad3c58cdb` 与 #27198 diff base 一致，无冲突） |

## 2. 变更仓库

- **ultralytics/ultralytics**（经 fork 提交，未合并）：#27198 更新 + 新开 #27203。
- **AIwork4me/Ultralytics-Windows-ROCm-Training-RCA**（自有仓库）：P15 全部交付物、P15 GPU 驱动脚本、原始证据。
- 未触碰 ROCm/PyTorch/AMD 文档仓库（无新缺陷归属彼处；#15862 无新材料不加评论）。

## 3. 上游规则核查

今日实测读取 upstream main 的 AGENTS.md / CONTRIBUTING.md / docs/AGENTS.md / pyproject.toml / docs.yml Ruff 精确选择器 / LICENSE。20 项硬性门槛矩阵：**17 PASS + 1 PASS-with-justification + 1 N/A = COMPLIANT**（`P15_UPSTREAM_COMPLIANCE_AUDIT.md`）。实际执行：worktree 工作流（C:\wp15、C:\wp15b）、推送前 ls-remote 校验远端 tip、bot 提交保留、现有 PR 上修复、CLA 与 AI 披露在场。

## 4. 复现的 bug

1. **PR #27198 测试策略违规**（非功能 bug）：144 行 6 个 monkeypatch 测试违反现行 AGENTS.md。
2. **新缺陷（P15 冷审发现）**：上游 `checks.cuda_device_count()` 依赖 `nvidia-smi` 子进程、`GPUInfo.select_idle_gpu()` 依赖 NVML——在 AMD HIP 实机上双双失效，导致 `tests/test_cuda.py` 在健康 gfx1151 上**整文件静默跳过**（"No CUDA devices available"）。实测复现：torch.cuda.is_available()=True 但 cuda_is_available()=False。

## 5. 确认的根因

- #26967 重设计 check_amp 时意外丢弃了探针的历史异常契约（8.4.182 是降级、8.4.197+ 是崩溃）——PR 已按 owner 修复，P15 仅做策略性测试收缩。
- test_cuda 全跳过 = 双重 NVIDIA-only 门（nvidia-smi 计数 → `CUDA_IS_AVAILABLE=False`；NVML 空统计 → `DEVICES=[]`）。两处 owner 各自最小修复。

## 6. 实现的修复

1. `fc72b4e`：#27198 测试文件 6→2（−79/+13），删除 torch>=1.13 兼容垫片，保留两个不同契约（探针异常→False+日志；KeyboardInterrupt 传播）。
2. #27203（`78b5b15` + `a1be048`）：`cuda_device_count` 在 nvidia-smi 缺失时回退 `torch.cuda.device_count()`（Jetson 分支既有先例）；`select_idle_gpu` 无 NVML 统计时按序回退选卡（尊重 indices 限制；bot 指出空列表语义后改为 `indices is not None` 判空）。净 +16/−9。

## 7. 阳性/阴性对照

- **阳性（实机）**：#27203 修复前 `tests/test_cuda.py::test_amp` SKIP → 修复后 **PASSED**（真实 HIP 设备，两次独立复跑 6.4s/2.1s）。
- **阴性**：NVIDIA 主机 nvidia-smi 成功路径代码未动；CPU-only 主机 `device_count()=0` → 门保持关闭；Jetson 早退分支未动；既有 `tests/test_python.py::test_select_device`（-1/CVD 翻译）修复前后均 PASS。
- **P15 GPU 全链**：amp-probe / smoke w0-w4 / 30-epoch / 中断 / 恢复 / finalcheck 全 PASS（§8）。

## 8. 真实物理 GPU 结果（gfx1151，官方发布栈 torch 2.12.0+rocm7.14.1 + released ultralytics 8.4.182）

- autocast 在 HIP 上真实触发（Conv2d 输出 fp16 vs FP32 dtype 证明）；check_amp=True。
- GradScaler 8/8 步真实参数更新（逐步参数 L2 校验和变化）；65536→65536 无溢出（溢出跳过语义由 P9 65536→2048 退火证据承载，已在文档如实标注）。
- 30-epoch COCO128（seed=0, workers=2, AMP）：mAP50-95 **0.4927→0.5980(ep22 峰值)→0.5851(ep30)**，无 NaN/inf。
- 硬中断（Stop-Process PID 11452，epoch≥20，21 行落盘）→ `process_alive_after_kill: False` → **新进程恢复** "from epoch 22 to 30"，lr0=0.000119 调度还原 → 30 行完整。
- best.pt 验证 mAP50-95 **0.5949** / mAP50 0.7823；重载推理 6 框；best SHA256 `b606f877…`。

## 9. AMP 与模型学习证据

`P15_AMP_NUMERICAL_ACCEPTANCE.md`：预注册（契约 §1 先于任何 GPU 腿冻结）→ **AMP_PASS**（gfx1151）。学习曲线与 P14 独立 20-epoch（0.4919→0.5603）互证：两曲线起点 ≈0.49 且显著上升，无未解释数值退化。无基准宣称（无参考机，INCONCLUSIVE 范围沿用 P13）。

## 10. 两个 Radeon 架构类状态

- Class A gfx1151：**PASS**（全部可跑腿）。
- Class B gfx1100/RDNA3：**BLOCKED_HARDWARE**（无物理硬件；Linux W7900 不等效；同架构替代不满足门槛）。
- ⇒ "两架构类" 门槛 **未达成**（硬件可用性，非软件状态）。

## 11. 实测 Windows NVIDIA 对比结果

**NVIDIA_COMPARISON_BLOCKED_HARDWARE**：契约已预注册冻结（§1 常量表 + A-J 判据 + 反捏造条款），`scripts/p15/nvidia_reference.py` 与 Radeon 驱动逐腿同构、随时可执行；`P15_NVIDIA_VS_RADEON_RESULTS.json` NVIDIA 侧全为 null/NOT_RUN，比较结论刻意为空，**不宣称 UX parity**。

## 12. Windows 可靠性结果

`P15_WINDOWS_RELIABILITY_REPORT.md` 15 项矩阵：新增实测 1-11 全 PASS（含 workers 0/2/4、新鲜/暖缓存 23.1-23.5s、检查点原子性、进程拆卸验证）；12-15 为 P13/P14 已存证；无新失败；ENV B ghost/DLL 锁为遗留项（owner：机器重启），未影响任何 P15 腿（全部运行于 ENV A 官方栈）。

## 13. 检查点/恢复结果

保存（best/last，SHA256 在案）→ 重载（YOLO(best.pt)）→ 推理（6 框）→ 硬中断 → 新进程恢复（epoch/优化器/调度器连续性经 args 行 + 行数 22→31 证明）。**PASS**。

## 14. 官方 wheel 与发布状态

**BLOCKED_RELEASE（今日实测维持）**：双通道索引无新 Windows wheel；决定性构件 `rocm_sdk_libraries-10.1.0-py3-none-win_amd64.whl` 与 P14 预修复版**逐字节同尺寸**（118,645,973）且 Last-Modified 2026-10-05 早于修复合并日；全部 TheRock tag 早于合并。发布链切点仍缺：post-merge MIOpen → Windows SDK 构建 → 发布。

## 15. 官方文档就绪度

上游 docs/en/integrations/amd 今日核实为 **Linux-only**（MIGraphX 明示 native Windows not supported），无 Windows PyTorch 训练文档。预备内容完整（`P15_OFFICIAL_WINDOWS_DOCS_READINESS.md`：支持矩阵/验证/训练/AMP/恢复/错误/锁定版本 + 构建与 prettier 流程），**提交推迟**至 GATE 3（不超前宣称未发布修复）。

## 16. 独立用户结果

issue #14 今日实测 **0 评论** → **BLOCKED_INDEPENDENT_USER_TEST**；不授予任何参与 credit。验收包（公开文档、金路径命令、manifest+schema、预期输出、安全报错指引）内容完备，测试者到位即可执行。公开召集帖已备好（未发布）。

## 17. 上游 PR 与维护者评审

| PR | 状态 | 评审 |
|---|---|---|
| #27198 | open @ fc72b4e，CI 15 pass/6 skip/0 fail | bot MEDIUM（探针守卫起点）已修复+答复；**无人工评审** |
| #27203 | open @ a1be048 | bot MEDIUM（indices=[] 语义）已修复+答复；**无人工评审** |
| ROCm #13437 | 已合并（f0a5d266） | —（P13437 任务收口） |

不把 bot/CI 绿当作人工批准。

## 18. CI 精确通过/失败/跳过

- #27198 @ fc72b4e：**15 pass / 6 skip / 0 fail**（GPU/Jetson/SlowTests/Conda/AMD_GPU 等按设计 skip；Tests 五平台 + Benchmarks + Docs + CLA 全绿）。
- #27203 @ 78b5b15：**13 pass / 6 skip**（a1be048 后 CI 重跑中）。
- 本地：#27198 测试 2/2 PASS；test_select_device PASS；gfx1151 test_amp PASS；P15 GPU 全腿 PASS。

## 19. 剩余外部依赖（owner + 解锁动作）

1. AMD 发布链：发布含修复的 Windows wheel（→G3 复裁，§5 清单就绪）。
2. ultralytics 维护者：#27198/#27203 人工评审（→G2）。
3. RCA owner：轮换 ZHIPU_API_KEY（历史 blob 仍在）；重启机器清 ENV B ghost；可选历史改写。
4. 项目 owner：提供第二 GPU 类 + NVIDIA Windows 对照机（→G1/G5）。
5. 独立开发者：接受 #14 邀请或响应公开召集（→G4）。

## 20. 六门禁终裁

| 门禁 | 裁决 | 一句话证据 |
|---|---|---|
| G1 工程正确性 | **NOT_MET**（一类完成，二类 BLOCKED_HARDWARE） | gfx1151 全链 PASS；gfx1100 无硬件 |
| G2 上游维护 | **IN_PROGRESS** | 两 PR open 等人工评审；#13437 已合 |
| G3 官方分发 | **BLOCKED_RELEASE** | 双通道今日复扫，构件仍 pre-fix |
| G4 首次开发者成功 | **NOT_MET** | #14 零回复；包就绪 |
| G5 NVIDIA UX parity | **NOT_RUN** | 对照机缺失；契约+参考测试已冻结就绪 |
| G6 回归防护 | **IN_PROGRESS / BLOCKED_RUNNER** | Layer A 已随两 PR 提交上游；Layer B 本地 runner 契约交付，无 runner 即不冒 PASS |

**项目总评：NOT_MET（外部状态未变），但全部未受阻工作已完成，并新增两项经实机验证的上游贡献。**

## 21. 对首次接触 Windows Radeon 开发者的具体收益

1. **可执行的金路径包**（WINDOWS_SETUP.md + 5 个脚本 + manifest/lock）：从官方渠道安装到 AMP 训练、断点恢复全程有据可依，错误信息可行动（CPU 拒绝退出码 2、缺失数据集、损坏检查点各有明确指引）。
2. **上行修复落地后**（#27198）：坏后端环境下 `train()` 不再崩溃——自动降级 FP32 并给出如实诊断（"该错误不必然是 AMP 专属"），训练可继续。
3. **#27203 落地后**：AMD 机器上 `device=-1` 自动选卡与上游 GPU 测试门第一次真正可用（SKIP→PASS 实证），为后续 AMD CI 铺路。
4. **诚实的边界陈述**：当前官方 wheel 的 no-STL 缺口、支持矩阵、两架构类与 parity 的真实状态全部如实可查，不会被虚假 PASS 误导。

—— 以上每条结论均可在 `release-provenance/raw/p15_*/`、两个 PR 的 live diff、以及 `docs/release-closure/P15_*.md` 中核对原始证据。
