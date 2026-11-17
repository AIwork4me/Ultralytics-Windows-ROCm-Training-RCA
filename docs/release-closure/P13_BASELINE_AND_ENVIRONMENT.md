# P13.0 — 基线冻结与环境状态

日期:2026-11-15 · MISSION P13 开工基线

## 仓库状态

| 项 | 值 |
|---|---|
| 主仓库 | `AIwork4me/Ultralytics-Windows-ROCm-Training-RCA` |
| 分支 / HEAD | `work/windows-rocm-training-release-closure` @ `ed9a29c`(P9 最终点,任务书一致)→ P13 批次提交中 |
| 证据 verifier | `scripts/verify_release_closure.py` → **575 checks / 0 violations,exit 0**(2026-11-15 实测;565 为 P9 wave-3 中间校准值,575 为权威计数 — 旧文档由 P13.8 对账) |
| 工作树 | 干净(提交前) |

## Windows 测试环境(P13 会话开始时)

### ENV A — `pm13437_official`(官方轮)

- MIOpen.dll sha256 `e97891df7ea0…`(OFFICIAL_WHEEL 身份 ✓)
- torch 2.12.0+rocm7.14.1、Python 3.13、Radeon 8060S (gfx1151)、Windows 11 26200
- 写锁:LOCKED(ghost 进程持锁,仅阻塞 DLL 替换,不影响运行)— 内容正确,可用于全部 GPU 验证

### ENV B — `pm13437_merged`(混合:官方包 + 源码构建 MIOpen)

- **会话开始态:SOURCE_BUILT_PATCHED**(`ed7c67a9…`,state-file 最后动作 swap-in @2026-11-14T15:17Z)
- **还原到 OFFICIAL_WHEEL 被阻塞**:HIP teardown ghost(PID 34416 等 4 个,创建于 2026-11-14 14:55–15:43Z,taskkill 报"无此任务"= 已退出卡内核清理)锁住 MIOpen.dll 写替换(WinError 32/13 同型)
- 处置记录:`release-provenance/raw/p130_zombie_kill_record.json`;还原命令就绪:`python windows-training-validation/scripts/envb_dll_swap.py --action restore --state-file windows-training-validation/environment/ENVB_DLL_STATE.json`
- 影响评估:混合态恰为 P13.2 RCA 的历史失败配置(保留使用);GATE 无新增阻塞

### 隔离纪律

- 本会话所有 MIOpen 缓存实验均用 `MIOPEN_USER_CACHE_PATH` 重定向到 `g2_work/raw/cache_homes/<run_id>`(run-id 隔离);default 缓存仅 E3 一次按原样使用(前置状态快照已存 `p132_default_cache_state_before.json`)
- DLL 双向哈希验证由 `envb_dll_swap.py` 承担;本会话未发生 DLL 替换

## 上游实时状态(P13.0 快照,经 GitHub API 核验)

| 项 | 状态 |
|---|---|
| ultralytics PR #27198 | open;P13.1 重建后 head `124de39`(见 P13_PR27198_CLOSURE.md) |
| rocm-libraries #15862 | open,0 维护者评论;P13.3 已补发布链切点证据评论 |
| rocm-libraries #15861 | open(EvaluateInvokers);本会话 E2 再次观察到同型负计时(复现环境:ENV B 通过运行中) |
| 官方 Windows wheel | 最新仍 `torch-2.12.0+rocm7.14.1`(2026-11-15 复扫;TheRock 最新 tag 10.1=2026-09-25 < 修复合并 2026-10-19)→ **BLOCKED_RELEASE 维持** |

## P13 批次内新增基线提交

- `8a349c8` P13.1 交付(P13_PR27198_CLOSURE.md + 测试证据 + 僵尸处置记录)
- P13.2/P13.3 交付随后提交(raw 证据:`p132_minconv_*`、`p132_probe_*`、`p132_checkamp_real_*`、`p132_default_cache_state_before.json`)
