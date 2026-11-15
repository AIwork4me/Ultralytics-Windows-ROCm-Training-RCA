# P14 最终工程报告(MISSION P14 全量收口)

日期:2026-11-15 · 分支 `work/windows-rocm-training-release-closure` @ **`01aaa0a`+GO_NO_GO 追加提交**(origin 已推)· 上游 PR #27198 分支 @ **`090e378`**(origin 已推)

## 1. Git SHA 与仓库变更清单

| 仓库 | 分支/HEAD | 变更 |
|---|---|---|
| AIwork4me/Ultralytics-Windows-ROCm-Training-RCA | `work/windows-rocm-training-release-closure`:c5043b4 → 64c149c(P14.0–2)→ e3398d4(安全)→ 2a47055(Golden Path)→ 01aaa0a(P14.4–7)→ GO_NO_GO 追加 | 新增 `docs/release-closure/P14_*` 8 份 + `golden-path/` 十件套 + 证据归档 + `scripts/scan_secrets.py`;21 证据文件密钥脱敏 |
| AIwork4me/ultralytics(fork,PR #27198) | `checkamp-guard-probe-exceptions`:eca13ba → **090e378** | checks.py 异常日志真实化(9 行级)+ 测试去重(−15 行) |
| ultralytics/ultralytics、ROCm/rocm-libraries | 未改动代码;#15862 新增 1 条证据评论;#27198 新增 1 条说明评论 | 未合并任何上游 PR |

## 2. 复现的 bug / 确认的根因 / 被推翻的假设

- **复现**:whl-next 10.1.0 官方轮 no-STL BatchNorm 失败,与历史 #3956 签名**逐字一致**(LEG B)
- **确认根因**:whl-next Windows SDK 的 MIOpen.dll = 构建点 `39d8d603`(2026-09-16)早于 #13437 合并(2026-10-19)→ 修复未进入任何官方 Windows 轮(双通道)
- **被推翻的假设**:① P13"官方通道无更新 Windows 轮"(whl-next 存在 2.13.0/2.14.0 win 轮);② "新版本号=含修复"(2.13.0/2.14.0 均为 PRE-FIX,任务书已预警)
- **不可复现维持**:invalid-kernel-file 崩溃(P13.2 起);ENV B ghost 锁(P14 重核验仍锁定,证据 `p14_ghost_recheck.json`)

## 3. 修复的代码 / Before-After 对照

| 项 | Before | After |
|---|---|---|
| 探针异常日志 | 错误归因"AMP 数值异常…可能 NaN/零 mAP" | 真实陈述:异常类型+预防性禁用+FP32 关联诊断(实机逐字验证) |
| 测试文件 | 7 测试(含与 test_cuda.py::test_amp 重复的健康控制) | 6 个不重复的故障注入测试 |
| P13 Golden Path 表达式 | `m.save("best.pt") / YOLO("best.pt")` 不可执行 | `golden-path/` 可执行套件 + 修订注记 |
| 证据安全 | 21 文件含密钥实值 | HEAD 全脱敏 + 常设扫描器 |

## 4. 测试执行与结果(本会话实测)

| 测试 | 结果 |
|---|---|
| 证据 verifier | 575 checks / 0 violations / exit 0 |
| PR #27198 测试(6 CPU 故障注入) | 6/6 PASS |
| 实机(gfx1151)健康控制 + 故障注入 | True / False+新消息 PASS |
| no-STL 三腿 | A FAIL / B FAIL / C PASS(exit 1/1/0) |
| Golden Path 全腿(验证/冒烟/20ep/val/检查点/中断续训) | 全 PASS;mAP 0.4919→0.5603;续训自 epoch 15(调度器恢复) |
| 错误 UX(CPU 拒绝/缺数据集/坏检查点) | exit 2 + 可操作信息 |
| 上游 CI @ 090e378 | **15 pass / 6 skip / 0 fail**(skip 不计 PASS) |

## 5. 官方贡献指南合规

Fork 分支工作 ✓ 最小聚焦 diff(+156/−22 vs main)✓ 已有测试复用/去重 ✓ Ruff(repo 规则集)clean ✓ Google docstring ✓ AGPL 头 ✓ CLA(owner 本人,2026-11-14)✓ 本地测试先行 ✓ 向后兼容(torch≥1.13 保护沿用;py3.8 腿 CI 绿)✓ 上游文档未动(无虚假 docs 构建声明)✓

## 6. 上游状态与维护者评审实况

| 项 | 状态 |
|---|---|
| PR #27198 | open / **REVIEW_REQUIRED** / 未合并;bot MEDIUM 已修;无人工评审;P14 精修评论已发 |
| rocm-libraries PR #13437 | merged(2026-10-19,f0a5d266)—— 但尚未进入任何官方 Windows 轮 |
| rocm-libraries #15862 | open;P14 双通道+运行时证据评论已发,含路由问题 |
| rocm-libraries #15861 | open;无新进展(P14 未重复实验,ghost 锁仍阻塞) |
| RCA Issue #14 | open;**零回应** |

## 7. 官方 Windows wheel 清单 / #13437 是否在测得二进制中 / no-STL 结果

- whl-multi-arch:torch 2.9.1–**2.12.0+rocm7.14.1**(win)→ **PRE-FIX**
- whl-next:torch 2.11.0+rocm10.0.0 – **2.14.0+rocm10.1.0**(win)+ rocm_sdk_* 10.0.0/10.1.0 → **PRE-FIX**(2.14.0 依赖同一 10.1.0 SDK)
- no-STL:LEG A FAIL / **LEG B(新候选轮)FAIL** / LEG C PASS → **无任何含修复的官方 Windows 轮**

## 8. GPU 架构覆盖 / AMP 真实性 / 学习与续训证据

- gfx1151 实测 4 组(轮审计/三腿/Golden Path/PR 实机);gfx1100、gfx1200/1201 **BLOCKED_HARDWARE**(不冒充)
- AMP:两次训练 `checks passed` = 真启用;权重增量(−0.001226)+ mAP 曲线证明真实参数更新;无 AMP_DISABLED→AMP_PASS 混报
- 续训:真实 kill(taskkill 不可用进程级证据 + Stop-Process PID)→ 新进程自 epoch 15 续至 20,lr0=0.000119 证明调度器状态恢复

## 9. Golden Path 首次用户结果 / 独立贡献者状态

- MODE B 全流程 PASS(细节 `P14_GOLDEN_PATH_EXECUTION_REPORT.md`);已知阻塞(无 Build Tools 机器)如实写入 WINDOWS_SETUP.md §5
- @LZ-QWQ:零回应、零贡献 → 无署名、无权限、无 CLA 代发;BLOCKED_INDEPENDENT_USER_TEST 维持

## 10. 剩余阻塞与责任人

| 阻塞 | Owner | 解锁动作 |
|---|---|---|
| **密钥轮换(紧急)** | repo owner(AIwork4me) | 轮换 ZHIPU_API_KEY;可选历史改写 |
| 官方修复轮发布 | AMD/TheRock 发布链(#15862 已供切点证据) | develop ≥ f0a5d266 的 Windows SDK 切片;RCA 可数小时内复验 |
| #27198 人工复审 | ultralytics 维护者 | 等待;不催促合并 |
| #15861 负计时 | RCA + MIOpen | 需 unblocked 环境;实验计划已挂 issue |
| ENV B ghost 锁 | 环境 | 重启机器(保存现场后)可解;E5 待此 |
| GATE 4 | @LZ-QWQ 或新测试者 | 回应 Issue #14 → 用 golden-path/ 套件验收 |

## 11. 最终门禁(证据支持,未升级)

| GATE | 状态 | 依据 |
|---|---|---|
| G1 工程正确性 | ✅ PASS(条件:gfx1151) | P9/P13/P14 全链 |
| G2 上游维护 | ⏳ IN_PROGRESS | #13437 已合;#27198 open 未合 |
| G3 官方分发 | ❌ **BLOCKED_RELEASE** | 双通道二进制+运行时证据 |
| G4 独立开发者成功 | ❌ **NOT_MET** | Issue #14 零回应;MODE B 为本人验收 |

**结论:PROJECT NOT COMPLETE。工程与文档侧已把"官方修复轮发布日"的验收成本压到最低(套件即验收脚本);剩余门禁全部在外部方(AMD 发布链 / 上游维护者 / 独立测试者)手中,另有 owner 动作:密钥轮换。**
