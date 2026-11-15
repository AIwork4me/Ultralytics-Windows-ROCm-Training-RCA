# P14.2 — PR #27198 上游就绪状态与对抗性复审

日期:2026-11-15 · 分支 `checkamp-guard-probe-exceptions` @ **`090e378`**(P14 新增,推至 fork)

## 实时上游状态(本会话 GitHub API 核验)

| 项 | 状态 |
|---|---|
| PR 状态 | **OPEN / REVIEW_REQUIRED / 未合并**;P13 后无人工维护者评审 |
| CI(eca13ba 时点) | 14 pass / 6 skip / 0 fail(GPU/AMD_GPU 等为 skipping,不得记硬件 PASS) |
| CLA | 已签(OWNER 本人,2026-11-14T23:47Z) |
| 评审线程 | UltralyticsAssistant MEDIUM(probe 生命周期)已在 P13 修复并答复;本会话无新评审 |

## P14.2 对抗性复审结论(§5.1 问题逐项)

| 问题 | 结论 |
|---|---|
| catch-all 是否符合 check_amp 契约 | 符合:返回 bool = "AMP 是否可用",探针任何失败 → False 是契约内行为;KeyboardInterrupt/SystemExit 不属于 Exception,继续传播(有测试) |
| 失败是否真是 AMP 特有 | **不一定** —— 这是 P14 发现的主要缺陷:旧消息断言"检测到 AMP 异常…可能导致 NaN/零 mAP",对后端异常(如 invalid kernel file)是错误归因;后端异常通常同样破坏 FP32 |
| 部分构造的探针对象/钩子泄漏 | 无模块级状态:`m` 为局部变量,钩子随对象 GC 回收;`close` 局部列表;no_grad 上下文正常退出。OOM 情形下提前 `del m` 收益边际,不值得增加分支(考虑过,拒绝) |
| OOM 处理 | 被捕获 → AMP 禁用;若真实内存耗尽,后续训练步会以明确 OOM 报错(未被掩盖) |
| 重试 | 无状态(每次调用新建 close 列表);重复调用测试覆盖 |
| NVIDIA/MPS/CPU 回归 | 无:try 仅包住探针路径;CPU/MPS 在此之前已提前返回;CI 多平台绿 |
| 返回 False 掩盖致命后端故障 | **部分缓解(通过措辞)**:新消息明确"若 FP32 同样失败,问题在 GPU 后端/运行时而非 AMP" — 不再把致命故障伪装成"AMP 已禁用所以一切正常"。将 check_amp 改为向上抛异常会回归首要目标(train 不因探针崩溃),维持 degrade+truthful-log |

## P14 变更(head `090e378`,净 −5 行 vs `eca13ba`)

1. **异常分支日志改为真实陈述**(不再复用数值异常文案):报告真实异常类型/信息 + "AMP 作为预防被禁用" + "若 FP32 同样失败则问题在后端/运行时"。
2. **删除与健康控制重复的测试**:`test_cuda.py::test_amp` 已在任何 CUDA-capable 设备(含 AMD GPU runner)覆盖健康路径正控制;保留 6 个 CPU 可运行的故障注入测试(构造/传输×2/前向/重复/中断),每个对应明确的回归防线。
3. 代码注释同步更新(为何 degrade、为何 truthful log)。

## 验证证据(本会话实测,gfx1151 实机)

- `ruff format` / `ruff check`(repo 默认规则集):clean
- `pytest tests/test_check_amp_probe_exception.py`:**6/6 PASS**(CPU 故障注入)
- 实机健康控制:`check_amp(model.cuda()) → True`
- 实机故障注入(探针 forward 注入 simulated hipErrorInvalidKernelFile):`→ False`,日志输出新消息(逐字验证)
- torch<1.13 兼容性:transfer 异常类型表 import 时 hasattr 保护(继承自 eca13ba)

PR 评论:https://github.com/ultralytics/ultralytics/pull/27198#issuecomment-6887751679

## 官方贡献指南合规(§11 门 A)

- 最小聚焦 diff(vs main `d0cfceaf`):2 文件,+156/−22(实现 9 行级 + 测试)
- 无新依赖、无 API 变更、无平台偏好分支;Google docstring 风格;AGPL 头保留
- 测试:新文件仅含与既有覆盖不重复的故障注入;正控制复用既有 test_cuda.py::test_amp
- CI:推送后以远端实际结果为准(P14.6 报告)

## 状态与等待项

- STATUS: **SUBMITTED_AWAITING_MAINTAINER_REVIEW**(工作完成;合并与否由维护者决定,禁止自合并)
- 若维护者提出新意见:按线程逐条处理,标注 FIXED_IN_CODE / REPLIED / OUTDATED / RESOLVED / APPROVED,不混淆状态
