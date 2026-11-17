# P14.0 — 任务开工基线冻结与实时状态核验

日期:2026-11-15 · MISSION P14 开工基线(所有远程状态为本会话经 GitHub API 实时核验,非沿用记录值)

## 仓库状态

| 项 | 值 |
|---|---|
| 主仓库 | `AIwork4me/Ultralytics-Windows-ROCm-Training-RCA` |
| 分支 / HEAD | `work/windows-rocm-training-release-closure` @ `c5043b4b21c092eb8c636ebd1cd448aec7cbddeb`(P13 最终点,与任务书一致;与 origin 同步) |
| 工作树 | 干净(基线时刻) |
| 证据 verifier | `scripts/verify_release_closure.py` → **575 checks / 0 violations,exit 0**(2026-11-15 实测复跑;与 P13 权威计数一致,未改动任何证据文件) |

## Windows 测试环境(本会话实测)

### ENV A — `pm13437_official`(官方轮)

- MIOpen.dll sha256 `e97891df7ea0…`(OFFICIAL_WHEEL 身份 ✓,本会话重新哈希确认)
- torch 2.12.0+rocm7.14.1、Python 3.13、Radeon 8060S (gfx1151)、Windows 11 26200

### ENV B — `pm13437_merged`(混合:官方包 + 源码构建 MIOpen)

- **本会话实测态:仍为 SOURCE_BUILT_PATCHED**(`ed7c67a9…`,独占写打开探测 → `ERROR_SHARING_VIOLATION(32)`,ghost 持锁状态与 P13 记录一致,未发生任何 DLL 替换)
- 进程枚举(2026-11-15T02:00Z):无可见 python 进程持锁 → 锁持有者为 P13 已记录的 HIP teardown 内核清理残留(非活进程句柄可见类);维持"不安全不替换"纪律
- 还原命令就绪:`windows-training-validation/scripts/envb_dll_swap.py --action restore`;P14 内 ENV B 仅用于历史失败配置复证,不与官方栈实验混用

### 新增隔离环境 — `p14_whlnext`(P14.1 官方 whl-next 候选轮,全新 conda env)

- 用途:官方 whl-next 10.1.0 候选轮的干净安装与 no-STL 负对照(LEG B);不触碰 ENV A/ENV B/yolo_amd
- 安装源:官方索引 `https://stable.repo.amd.com/rocm/whl-next/`(下载 wheel SHA256 清单见 P14_OFFICIAL_WINDOWS_WHEEL_AUDIT.md)

## 上游实时状态(P14.0 快照,经 GitHub API 核验 2026-11-15T01:45–02:00Z)

| 项 | 实测状态 |
|---|---|
| ultralytics PR #27198 | **open / REVIEW_REQUIRED / 未合并**;head `eca13bab7f5cc1edbdf07c3ddfefa2ca4b58f9ef`(与本地分支一致);CI 14 pass / 6 skip / **0 fail**(GPU、AMD_GPU、RaspberryPi、SlowTests、Conda、NVIDIA_Jetson 为 skipping,不得记为硬件 PASS) |
| RCA Draft PR #13 | open / draft;head `c5043b4`(与本地一致) |
| 独立测试邀请 Issue #14 | open;**评论数 0** — @LZ-QWQ 未回应 → `BLOCKED_INDEPENDENT_USER_TEST` 维持,不得假设接受 |
| rocm-libraries #15862 | open;仅 RCA 1 条证据评论(2026-11-14),无维护者回应 |
| rocm-libraries #15861 | open;仅 RCA 1 条评论(2026-11-15T00:23Z 源码分析+实验计划),无维护者回应 |

## 官方 Windows wheel 通道(P14.1 首要发现,详见 P14_OFFICIAL_WINDOWS_WHEEL_AUDIT.md)

**通道矩阵(实测)**:

| 通道 | 最新 Windows torch wheel | 状态 |
|---|---|---|
| `repo.amd.com/rocm/whl-multi-arch/`(P13 已知) | torch 2.12.0+rocm7.14.1 | 与 P13 一致,未前进 |
| `stable.repo.amd.com/rocm/whl-next/`(**P14 新发现,P13 未覆盖**) | torch 2.13.0+rocm10.1.0、2.14.0+rocm10.1.0(cp310–cp314 win_amd64)+ `rocm_sdk_libraries-10.1.0` win | **存在更新的官方 Windows 轮** → 触发 P14.1 完整审计 |

**二进制溯源初步结论(实测)**:whl-next `rocm_sdk_libraries-10.1.0` win 包内 `MIOpen.dll`(sha256 `266d716b…`,496,074,240 B):

- 版本串 `3.6.1.39d8d603` → 构建 commit `39d8d60365d22…` 日期 **2026-09-16**(GitHub API 核验)< 修复合并 `f0a5d266`(**2026-10-19**)
- 修复标记 `miopen_initializer_list`:轮内 DLL = **0**,与两块已知未修复 DLL(官方 7.14.0 `74b4ee03` / 7.14.1 `e97891df` = 0)一致;已修复参照(源码构建 `ed7c67a9`,版本串 `3.6.2.f0a5d266`)= **2**
- 结论:whl-next 10.1.0 Windows 轮为**修复前二进制** → `BLOCKED_RELEASE` 维持;运行时 no-STL 负对照(LEG B)进行中以取得运行时证据

## GATE 状态(继承 P13,不升级)

| GATE | 状态 |
|---|---|
| G1 工程正确性 | PASS(条件:gfx1151,P9/P13 证据) |
| G2 上游维护 | IN_PROGRESS(PR #27198 open,未合并) |
| G3 官方分发 | NOT YET VERIFIED → P14.1 审计中(初步:新通道仍为修复前二进制) |
| G4 独立开发者成功 | NOT MET(Issue #14 无回应) |
