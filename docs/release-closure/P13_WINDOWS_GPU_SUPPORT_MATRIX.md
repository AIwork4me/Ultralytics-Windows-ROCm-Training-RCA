# P13.5 — Windows GPU 支持矩阵

日期:2026-11-15 · 状态:gfx1151 实证;其余 **BLOCKED_HARDWARE**

| 架构 | 代表 GPU | Windows ROCm 官方轮 | 实证状态 | 阻塞 |
|---|---|---|---|---|
| gfx1151 | Radeon 8060S (iGPU) | torch-2.12.0+rocm7.14.1(repo.amd.com) | ✅ **本文唯一实机已验**:G0–G4 全套 + P13 新探针守卫 7/7(ENV A)+ P13.2 三配置判别(ENV B) | — |
| gfx1100 | RX 7900 XTX | index 有 cp313 win_amd64 wheel | **BLOCKED_HARDWARE**(无实体卡接入;Linux W7900 结果不得替代 Windows gfx1100 验收) | 硬件 |
| gfx1150 | Radeon 8050S | 同上 | BLOCKED_HARDWARE | 硬件 |
| gfx1200/gfx1201 | RDNA4 系列 | **待查:官方支持矩阵确认后才可测**(不以 torch 识别名字为准) | BLOCKED_HARDWARE + 支持矩阵未确认 | 硬件 |
| 其他 | — | — | BLOCKED_HARDWARE | 硬件 |

跨架构验收命令(接入即跑,模板同 `platform-matrix/*`):G0 溯源 → G1 原语 → G2 生命周期 → G3 AMP(含 P13.1 新守卫回归 7 用例)→ G4 30ep+断点续训;每步 in-process DLL probe + SHA256。

**P13.1 新增的跨架构红利**:`tests/test_check_amp_probe_exception.py` 的 6 个故障注入用例 **CPU 可跑** — 任何 runner(含非 AMD)都能验证守卫策略;仅健康正控需真硬件。上游 CI 的 AMD_GPU job 硬件门控 skip 时,守卫策略仍被普通 CI 覆盖(不违反"SKIP 不得计入 PASS"——SKIP 的只有健康正控,且本仓库有 gfx1151 实机正控证据)。
