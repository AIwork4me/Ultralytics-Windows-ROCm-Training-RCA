# P14 三视角对抗性复审记录(任务书 §12)

日期:2026-11-15 · 对象:P14 全部重要变更(wheel 审计 / PR #27198 精修 / golden-path 套件 / 安全处置)

## REVIEWER A — Ultralytics 维护者视角

- PR diff 最小聚焦(vs main 2 文件 +156/−22);测试文件去重主动对齐官方指南;Google docstring;AGPL 头;ruff clean;CLA 已签;无平台偏好分支(CPU/MPS 早退路径不动,NVIDIA CI 绿)
- catch-all Exception 的辩护成立:契约 = 返回 bool("AMP 可用与否");KeyboardInterrupt/SystemExit 传播有测试;消息不再错误归因
- **结论:无未决缺陷;状态 = 等待人工复审(外部方)**
- golden-path 套件仅存在于 RCA 仓库,未误称上游文档构建(docs/en 未动)✓

## REVIEWER B — ROCm 运行时/数值正确性视角

- 溯源链完整:版本串 → 构建 commit(API 核验日期)→ 修复标记(双向校准)→ 运行时复现;无仅凭版本号/时间戳的推断
- 无虚假 AMP PASS:仅 `AMP: checks passed`(真启用)记 AMP_PASS;权重增量 + mAP 曲线为参数更新实据
- 无静默 FP32/CPU 回退:verify/train 双重拒绝(exit 2 实测)
- **结论:无未决缺陷;BLOCKED_RELEASE 判定证据充分且未越权升级 GATE**

## REVIEWER C — 首次 Windows Radeon 开发者视角

- 安装→验证→训练→验证→保存→重载→中断→续训每条命令在本机实测;错误消息可操作(CPU 拒绝/缺数据集/坏检查点三项实测,其余 NOT_RUN 如实标注)
- last.pt/best.pt/resume=True 概念区分明确;known blocker(无 Build Tools 机器 HIPRTC 失败)给出症状/原因/处置
- 缺口如实披露:安装时长未重测(给参考值);第二台干净机器不可能(独立测试 BLOCKED);requirements-lock 为"实测组合"非"最低版本"
- **结论:无未决缺陷;独立验收仍 BLOCKED_INDEPENDENT_USER_TEST(外部方)**

## 缺陷处置汇总

| 发现 | 处置 |
|---|---|
| 异常日志错误归因(本会话自审发现) | FIXED_IN_CODE(090e378) |
| 健康测试与既有覆盖重复 | FIXED_IN_CODE(090e378) |
| P13 报告不可执行表达式 | FIXED_IN_CODE(修订注记 + golden-path 套件) |
| 21 证据文件密钥泄漏 | FIXED_AT_HEAD(e3398d4)+ scan_secrets 防护;**历史 blob → owner 轮换密钥(已上报)** |
| 官方修复轮缺失 | BLOCKED_RELEASE(owner:AMD 发布链;证据已供 #15862) |
| 独立测试缺失 | BLOCKED_INDEPENDENT_USER_TEST(owner:@LZ-QWQ 回应或换人) |
| GPU CI 缺失 | BLOCKED_RUNNER(维持设计,人工实机证据如实标注) |

无 summary-only closure:每项缺陷均 FIX(有证据)或 BLOCKED(有 owner 与解锁动作)。
