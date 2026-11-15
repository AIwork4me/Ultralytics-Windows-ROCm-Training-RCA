# P14.5 — Windows GPU 支持与实测矩阵

日期:2026-11-15 · P14 会话新增实测(其余继承 P9/P13 证据)

## 实测矩阵

| 架构 | 设备 | Windows 实测状态 | P14 会话新证据 | 官方轮含 #13437 修复 |
|---|---|---|---|---|
| gfx1151 | Radeon 8060S(iGPU) | **PASS(多轮)** | ① whl-next torch 2.13.0+rocm10.1.0 全新安装 + 真实 GPU 计算;② Golden Path MODE B 全流程(冒烟/20ep 代表训练/验证/续训/错误 UX);③ PR #27198 6+2 测试(6 CPU + 2 实机);④ no-STL 三腿对照 A/B/C | 否(双通道均 PRE-FIX) |
| gfx1100 | RX 7900 XTX | **BLOCKED_HARDWARE** | 无(本机无此硬件;不借用 Linux 结果冒充 Windows) | —(按依赖推断同 SDK → 同为 PRE-FIX,但未实测) |
| gfx1200/1201 | RDNA4 | **BLOCKED_HARDWARE** | 无 | —(whl-next 有对应 device 包存在,未实测) |

## gfx1151 本会话证据明细

1. **官方双通道 wheel 审计**(P14_OFFICIAL_WINDOWS_WHEEL_AUDIT.md):whl-multi-arch 最新 7.14.1(PRE-FIX);whl-next 最新 2.14.0+rocm10.1.0(PRE-FIX,构建点 39d8d603 = 2026-09-16)
2. **no-STL 三腿**(P14_NO_STL_COMPARISON.json):A/B FAIL(逐字同签名)/ C PASS
3. **Golden Path MODE B**(P14_GOLDEN_PATH_EXECUTION_REPORT.md):全腿 PASS,AMP 真实启用,mAP 0.4919→0.5603,跨进程续训 epoch 15→20
4. **PR #27198 实机验证**(P14_PR27198_UPSTREAM_READINESS.md):健康控制 True;故障注入 False + 新真实消息
5. **续训兼容性正面发现**:torch 2.13.0+rocm10.1.0(hip 7.16.26385)在现有驱动下可用 —— 官方修复轮发布后,新通道可直接作为基座

## 不做的事(如实)

- 不把 Linux gfx1100 结果标为 Windows PASS(P13 已定纪律)
- 不假设 RDNA3/RDNA4 行为一致;gfx1200/1201 仅记录"官方 device 包存在、无硬件实测"
- BLOCKED_HARDWARE 项不编造;官方修复轮发布后,矩阵刷新的最小成本 = `golden-path/` 套件在新卡上跑一遍
