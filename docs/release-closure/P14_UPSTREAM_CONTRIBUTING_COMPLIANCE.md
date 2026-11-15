# P14 — 官方贡献指南合规审计(P14_UPSTREAM_CONTRIBUTING_COMPLIANCE)

日期:2026-11-15 · 依据:`https://docs.ultralytics.com/help/contributing` + `https://docs.ultralytics.com/help/CLA`(P14.0 基线冻结时读取当前线上版本,不以历史/记忆版本为准)

审计对象:

- **上游贡献**:ultralytics PR #27198(fork `AIwork4me/ultralytics`,分支 `checkamp-guard-probe-exceptions`,head `090e378`)
- **RCA 自有仓库**:本仓库 `work/windows-rocm-training-release-closure` 分支的提交与证据工作流(仅对照适用条款)

## 1. 二十条规则合规矩阵(任务书 §1 STRICT RULES)

| # | 规则 | 状态 | 证据(本会话实测,标注测量方式) |
|---|---|---|---|
| 1 | Fork 相关仓库 | PASS | `git remote -v`:origin=`AIwork4me/ultralytics`(fork),upstream=`ultralytics/ultralytics` |
| 2 | 明确命名分支 | PASS | `checkamp-guard-probe-exceptions`(语义化,单一目的) |
| 3 | editable 开发安装 `python -m pip install -e .` | PASS | 专用环境 `p14_mode_a_dev`(Python 3.13 / torch 2.15.0+cpu):`pip install -e .` → `Editable project location: C:\Users\rocm\Desktop\YOLO_AMD\upstream_ultralytics`;导入解析 cwd 无关指向 fork 源码;PR 测试套件在该环境 6/6 PASS(2026-11-15 实测)。历史说明:P14.2 期间以 checkout-cwd 导入方式开发;本审计补做正式 editable 安装,**未污染** `yolo_amd`(8.4.174)与 `pm13437_official`(8.4.182)的记录身份 |
| 4 | 文档改动装 dev 依赖 + `python docs/build_docs.py` | N/A | PR diff 仅 `ultralytics/utils/checks.py` + 1 个测试文件(`gh pr files` 实测),无 docs/en 改动 → 不适用 |
| 5 | 遵循仓库当前 Ruff 规则 | PASS | `ruff format` / `ruff check`(repo 规则集)clean;本机全局 ruff 配置过期的 gotcha 以 `--isolated` 规避并以仓库 CI 为准(CI 绿) |
| 6 | Google 风格 docstring(括号内类型) | PASS | 新测试模块 docstring 与函数 docstring 按此风格;AGPL-3.0 头保留(文件头实测) |
| 7 | 最小聚焦实现 | PASS | `checks.py` +18/−7(vs 当前 upstream/main,merge-base diff 实测):try/except 包裹探针路径,无新抽象、无新依赖 |
| 8 | 避免多余函数参数 | PASS | 函数签名零变更(diff 实测) |
| 9 | 不重复既有逻辑 | PASS | 健康路径正控制复用既有 `tests/test_cuda.py::test_amp`,不复制 |
| 10 | 复用既有测试 | PASS | 同上 |
| 11 | 小聚焦回归优先加现有测试文件 | PASS(有依据的新文件) | `tests/test_check_amp_probe_exception.py`(144 行)为独立回归面:6 个 CPU 故障注入用例(构造/传输×2/前向/重复/中断),现有文件无等价覆盖;每个保留用例对应明确回归防线;未为缩短篇幅删除有效负控制(任务书 §5.4);健康正控制不新建(避免重复) |
| 12 | 上游提交前本地测试 | PASS | CPU 注入 6/6;实机 gfx1151 健康控制 `check_amp → True` / 注入故障 `→ False`+新消息(逐字验证);本次 editable 环境复跑 6/6 |
| 13 | 向后兼容 | PASS | `torch.cuda.OutOfMemoryError` 以 `hasattr` 守护(torch<1.13 兼容);CI 3.8–3.15 矩阵绿 |
| 14 | 简洁描述性提交 | PASS | `3f6076c`(标题+正文:目的/机制/范围/测试说明)、`eca13ba`、`090e378` 均语义化 |
| 15 | PR 说明目的与范围 | PASS | PR body 4329 字符,含目的/根因/最小复现/前后对照/范围声明 |
| 16 | CI 通过 | PASS | **15 pass / 6 skip / 0 fail**(2026-11-15 `gh pr checks` 实测,head `090e378`;skipping 一律不计 PASS) |
| 17 | bug 提供最小复现示例 | PASS | PR body 含 MRE(实测 bodyHasRepro=true;无 STL HIPRTC 复现器归 #15862 侧证据链) |
| 18 | 尊重 Code of Conduct 与评审者 | PASS | 评审线程逐条回复,UltralyticsAssistant MEDIUM(probe 生命周期)已在代码中处置并答复 |
| 19 | CLA 要求 | PASS | OWNER 本人签署(2026-11-14T23:47Z);CI CLA check = pass |
| 20 | 评审视为工程而非形式 | PASS | 线程状态标注纪律(FIXED_IN_CODE/REPLIED/OUTDATED/RESOLVED/APPROVED 不混淆);当前 REVIEW_REQUIRED,**未合并、不自合并**,等待维护者决定 |

## 2. §11 门 A(贡献指南合规)逐项核对

| 门 A 条目 | 结论 | 证据落点 |
|---|---|---|
| 正确仓库/分支 | PASS | 规则 1/2 |
| 最小聚焦变更 | PASS | 规则 7/8,`P14_PR27198_UPSTREAM_READINESS.md` |
| 兼容实现 | PASS | 规则 13 |
| 正确 docstring | PASS | 规则 6 |
| Ruff clean | PASS | 规则 5 |
| 适用测试套件绿 | PASS | 规则 12/16 |
| CLA 状态正确 | PASS | 规则 19 |
| 源码/许可证处理恰当 | PASS | AGPL-3.0 头保留;无第三方源码引入(diff 仅 2 文件) |

## 3. RCA 自有仓库侧(仅适用条款)

- **诚实性边界**:golden-path 与各 P14 报告为本仓库文档;未在任何上游 issue/PR 中声称上游 docs build 未发生之事(任务书 §6.7)。
- **证据纪律**:验证器 `scripts/verify_release_closure.py` 本会话复跑 **575 checks / 0 violations / exit 0**(2026-11-15);SKIP 不计 PASS、PASS 需二进制+GPU 溯源的规则未改动。
- **自有分支推送**:本仓库分支推送属授权范围(`upstream-submission-boundaries` 纪律),未 merge 任何上游 PR。

## 4. 结论

- 上游贡献侧:20 条规则 **18 PASS + 1 N/A(规则 4)+ 1 PASS-with-justification(规则 11)**,无未处置偏差;规则 3 于本审计中由 cwd-import 升级为正式 editable 安装并复验。
- 判定:**COMPLIANT**,PR #27198 保持 `SUBMITTED_AWAITING_MAINTAINER_REVIEW`。
