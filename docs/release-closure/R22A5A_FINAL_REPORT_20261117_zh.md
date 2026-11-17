# R22A.5A 最终报告 — 官方 Stable 发布就绪与 CPU-only 预检闭环(2026-11-17)

- 任务:R22A.5A(CPU-only Stable release preflight);本报告为任务 §16 要求的
  最终中文报告的仓库存档版本。
- 性质:与 R22A.4.1 冻结记录相同的 commit-stable 契约 —— 本文件固化**内容与
  验证方法**;报告提交本身产生的新集成 HEAD 及其独立 CI 证明在对应 PR 描述中
  外部记录(文件内无法包含自身提交后的 SHA)。
- 判定组合:**`R22A5A_CPU_PREFLIGHT_READY / OFFICIAL_STABLE_BLOCKED_RELEASE`**
  (任务 §15 明确:这是 R22A.5A 的成功结果;不是工程失败,更不是
  OFFICIAL_STABLE_PASS)。

## A. 执行判定 (Executive Verdict)

| 判定项 | 结论 |
|---|---|
| CPU 预检 | **R22A5A_CPU_PREFLIGHT_READY**(8/8 门禁全绿;`python scripts/r22a5a/release_preflight.py --offline` exit 0) |
| 官方发布判定 | **OFFICIAL_STABLE_BLOCKED_RELEASE**(外部发布阻塞未解除,如实上报) |
| R22A.5A 总体 | **成功**(工程准备完成 + 外部阻塞如实披露) |
| 剩余 P0/P1 | 工程侧 **0**;外部 P0 = AMD 修复轮未发布(rocm-libraries#15862 无 assignee);外部 P1 = issue #14 受邀测试者未接受(OPEN / 0 评论,2026-11-17 复核) |

## B. 精确 Git 状态(工具与工件合并时点)

| 项 | 值 |
|---|---|
| 起始 SHA | `0b91aa92d3206402f8d66e235c1fb588ea9abdaf`(R22A.4.1 冻结集成 HEAD) |
| 任务分支 | `release/r22a5a-stable-preflight`(直接基于集成 HEAD;无 force-push、无历史改写) |
| PR | [#20](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/pull/20),3 个逻辑提交(工具链+测试+CI / 溯源工件 / 契约文档),MERGED |
| PR HEAD | `36c34f08e3bacf6932c58c25f003c7f9f13f8cd0` |
| 合并提交 | `89cee97cfbb1f450b901dccae16cf2fe1379b605`(parents `0b91aa9` + `36c34f0`) |
| 最终集成 HEAD(工件合并后) | `89cee97cfbb1f450b901dccae16cf2fe1379b605`(本报告提交后的新 HEAD 见 PR 描述) |
| PR-HEAD CI | run [43993562615](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/actions/runs/43993562615) @ `36c34f0` — success(含新增 scripts/r22a5a 编译步骤) |
| exact-HEAD CI(独立 workflow_dispatch,R22A.4.1 先例) | run [43993785861](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/actions/runs/43993785861) @ `89cee97` — success;重复触发 run 43993765555 同 head 亦 success |
| `main` | 未改动,`f9f745e4089621505e174b54a3f86ceb5b2f9ef2` |
| 工作树 | 干净(仅两个任务前即存在的未跟踪遗留:`bus.jpg`、`windows-golden-path/reports/r22a-gfx1151/SHA256SUMS`,未提交) |

## C. 既有基础设施复用(无重复工程)

- **原样复用(零修改)**:`discover_official_wheels.py`(渠道索引层直接 import)、
  `resolve_package_set.py`、`verify_provenance.py`、`verify_miopen_nostl.py`、
  `supplemental_acceptance.py`、`acceptance-contract.json`、
  `compatibility-matrix.yaml`、`golden-path/*`、`verify_release_closure.py`、
  197 项基线测试文件(字节不变)。
- **新增(薄适配,`scripts/r22a5a/`)**:`r22a5a_lib.py`(故障关闭分类器:
  冻结锚点按 wheel/DLL SHA 复用、家族前沿支配、仅发布渠道集合继承;安全
  wheel ZIP 检查:零安装/零解压/零执行 + 路径遍历拒绝;计划分层;隐藏需求
  扫描)、`scan_official_releases.py`(Phase A)、`audit_wheel_provenance.py`
  (Phase B,输出 schema 与 `verify_provenance --ancestry-evidence` 兼容)、
  `gen_install_plan.py`(Phase C)、`g9_preflight.py`(Phase D)、
  `release_preflight.py`(Phase H,--offline 零网络 / --live 不触 GPU 不装包)。
- 证据链:PR 描述 + `R22A5A_INITIAL_GAP_MATRIX.md`(§复用决策记录)。

## D. 官方 wheel 清单(2026-11-17 实时扫描)

| 渠道 | 前沿集合 | 分类 | 依据 |
|---|---|---|---|
| multi-arch (GA) | torch 2.12.0+rocm7.14.1 / sdk-lib 7.14.1 | OFFICIAL_PRE_FIX | 冻结锚点(DLL `e97891df…` marker 0 + R21-D1 行为证据) |
| stable whl-next | torch 2.14.0+rocm10.1.0 / sdk-lib 10.1.0 | OFFICIAL_PRE_FIX | 冻结锚点(wheel `0c34bafb…` P14/P15/P16 三次字节一致) |
| rc whl-next | torch 2.15.0+rocm10.2.0rc2 | OFFICIAL_PRE_FIX | 冻结锚点(compare diverged,behind_by=92:合并后构建日期、修复前源码) |
| nightly | sdk-libraries 10.3.0a20261116 | PRE_RELEASE_CANDIDATE | 本次新鲜审计(见 §E);gfx1100 设备轮自 11-15 缺失状态**已出现** |
| dev | 10.3.0.dev0+git…(前沿 a20261027) | NEW_ARTIFACT_PROVENANCE_PENDING | 移动渠道,逐构建审计原则 |
| TheRock releases | 最新仍 therock-10.1(2026-10-05) | 最新 5 tag 全 PRE_FIX_SOURCE | compare API(behind_by 19441~27743),零日期推断 |
| download.pytorch.org | — | 无任何 ROCm Windows wheel | 实时抓取 |

机器可读清单:`release-provenance/r22a5a/latest_official_windows_candidates.json`
(信封 + 183 条确定性排序前沿候选:103 NO_NEW_ARTIFACT / 72 OFFICIAL_PRE_FIX /
7 PENDING / 1 PRE_RELEASE_CANDIDATE)。

## E. MIOpen 修复溯源

- 源码链(冻结证据工具化复用):`f0a5d266` ← TheRock #9359(`d875648`
  behind_by=0)← TheRock main(`9ea8cfc5` behind_by=0)。
- 本次新鲜二进制审计(有界下载 1 次、仓库外缓存复用、仅 ZIP 检查、零安装):
  nightly `rocm_sdk_libraries-10.3.0a20261116`,wheel SHA256
  `b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0`,
  内嵌 MIOpen.dll `f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6`
  (519,806,464 字节,`3.6.3.25f28906`),marker=2,compare **ahead_by=1074 /
  behind_by=0** → POST_FIX_LIBRARIES(筛选信号 + 源码谱系双阳性)。
- 缺失证明/限定:阳性溯源判定**不是**物理 GPU PASS(G1 no-STL 运行时门禁属
  R22A.5B);marker 单独永不足够(负向测试钉死:伪造 marker + diverged →
  PRE_FIX;正确命名但哈希不符 → 不继承冻结判定)。
- 限定状态:stable 候选不存在;nightly 为 OFFICIAL_DEV 层级,永不标 Stable。

## F. 包兼容性(gfx1100 / gfx1151)

| 架构 | 官方支持地位 | 工程可行性 | 当前计划 |
|---|---|---|---|
| gfx1100(RX 7900 XTX) | AMD ROCm 文档列名(安装时以官方矩阵为准) | 已证(DEV 物理训练 PASS) | stable=UNQUALIFIED;nightly=OFFICIAL_DEV(集合齐备) |
| gfx1151(Radeon 8060S) | UNKNOWN(不在已发布 Windows 支持矩阵,如实记录) | 已证(DEV PASS + 官方 7.14.1 MODE B 实测) | 同上 |

规则全部可测(family 混装 / ABI / 设备轮 / vendor / 集合冲突按 SDK 锚集合
消歧);历史 `golden-path/requirements-lock.txt` 未改动,另建
`candidate_lock_template.json`。文档:`R22A5A_PACKAGE_COMPATIBILITY_MATRIX.md`。

## G. Golden Path 就绪度

- **现已可执行**:`g9_preflight.py`(stable → BLOCKED_RELEASE exit 3,拒绝对
  预修复轮发放验收——防"Build Tools 掩盖缺陷"假成功);`release_preflight.py
  --offline/--live`;no-STL 失败契约**静态设计验证**(10/10 要素在已提交
  验证器字节中;"空 scratch 重定向证明 STL 真不可达,非清变量"的负控设计)。
- **须等修复轮**:stable 通道全部 U1–U10 场景、G9 CLEAN_WINDOWS_INSTALL、
  R22A.5B 全部 GPU 门(契约文档固化:四层证据模型、检查点完整性、AMP 五态
  分类、可靠性矩阵、每架构独立判定——绝不跨 GPU 强制相同更新计数)。

## H. CPU 测试

| 项 | 结果 |
|---|---|
| 既有测试 | 197(R22A.4.1 基线,文件字节不变) |
| 新增测试 | **47**(`test_r22a5a_cpu.py`,钉死任务 §10 全部 20 项强制负向行为) |
| PASS/FAIL/SKIP | **244 / 0 / 0**(本地 + exact-HEAD CI 双重确认) |
| 对抗测试 | 47 新增 + 冻结套件既有对抗类 + 验证器 22/22 自测 |
| 证据验证器 | **902 检查 / 0 违规** |
| 编译 | compileall 干净(windows-golden-path + scripts/r22a5a;CI 新增一步,无既有步骤削弱) |

## I. 安全与证据完整性确认

- `evidence/raw/**` 零变更(diff=0);`main` 未动;无 tag / 无发布 / 无 PyPI。
- 零新 GPU 执行、零 `torch` import(新代码 grep + 测试双验证)、零 GPU 初始化。
- 零 DLL 替换、零自建包安装(唯一下载:nightly wheel 一次有界取件至仓库外
  缓存,仅 ZIP 检查)。
- 零上游变更(#15862 未评论未关闭;交接文档为内部草案未投递)。
- 密钥扫描 CLEAN;下载仅限官方主机 allowlist + TLS;离线单元测试零网络依赖。

## J. 剩余任务(依赖排序)

| # | 任务 | 前置 | 环境 | 验收标准 |
|---|---|---|---|---|
| 1 | AMD 修复轮发布 | #15862 获 owner + 携带 `f0a5d266` 谱系的 cut | AMD 侧 | stable 渠道出现 >10.1.0(或 .postN)且 compare behind_by=0 |
| 2 | R22A.5B Stable 双架构物理验证 | 任务 1 | 本机 gfx1100 + gfx1151 | 5 步管道(扫描→审计→锁→G9 预检→G0–G9 门)全绿,每架构独立 STABLE_SUPPLEMENTAL_PASS |
| 3 | G9 干净 Windows 验证 | 任务 2 | 新装/受控镜像 | CLEAN_WINDOWS_INSTALL:无历史缓存/无宿主 STL/无 DLL 替换/无 HIPRTC 注入 |
| 4 | 独立开发者验收 | 任务 2 + #14 接受 | 独立机器 | 按 STABLE_ACCEPTANCE_GUIDE 全绿回报 STABLE_USER_ACCEPTANCE_PASS |
| 5 | R23 最终发布 | 任务 3 + 4 | — | 仅在物理 Stable 验证后发布 |

**结语**:当修复轮出现时,下一位工程师只需执行已固化的一条管道;
`release_preflight.py --live` 会自动把结论从 OFFICIAL_STABLE_BLOCKED_RELEASE
切换为 CANDIDATE_FOUND_PENDING_PHYSICAL_VALIDATION —— 绝不自动晋级、绝不自动
启动 R22A.5B、绝不以 CPU 结论冒充物理验证。
