# P14.6 — CI 与回归防护报告

日期:2026-11-15

## LAYER A — 普通 CPU 可运行 CI(PR #27198 维持上游 CI 为主战场)

**PR #27198 @ `090e378`(P14 新 head,GitHub Actions run 43666464309,实测)**:

- 14 pass(CLA / Docs / Assets / actions / codecov / IsolatedExports / Tests×6(含 windows-latest py3.13、ubuntu py3.8+torch1.8.0 兼容腿)/ Benchmarks×3)
- 6 skipping(GPU、AMD_GPU、RaspberryPi、SlowTests、Conda、NVIDIA_Jetson)—— **skipping 一律不计 PASS**
- 0 fail;ubuntu-26.04-arm Tests 在取证时点 pending(最终状态以远端为准,P14 收尾时复验)
- **收尾复验(2026-11-15,`gh pr checks 27198` 实测)**:最终 **15 pass / 6 skip / 0 fail** —— pending 的 ubuntu-26.04-arm Tests 已通过;skipping 集合不变,0 fail 维持
- Ruff:本会话实测 repo 默认规则集下 clean(注意:本机全局 ruff 有过期配置会误报 BLE001/S110,须 `ruff check --isolated` 或 CI 为准)

**本仓库 Layer A 新增**:

- `scripts/scan_secrets.py` —— 密钥泄漏回归防护(P9 证据曾把 ZHIPU_API_KEY 带入公开仓库,P14 已在 HEAD 层修复;扫描器防止复发;`--redact` 支持就地修复)。当前实测 CLEAN
- 证据 verifier `verify_release_closure.py`:P14 复跑 **575/0/exit 0**(证据文件未被本次工作改动,除密钥脱敏外)

## LAYER B — 可信物理 Windows Radeon GPU runner

状态:**BLOCKED_RUNNER(维持)** —— 无可用持久 GPU CI 主机;替代证据为人工实机执行(gfx1151,本会话 4 项,见 P14_GPU_SUPPORT_AND_VALIDATION_MATRIX.md),如实标注"人工实机证据 ≠ 自动化硬件 CI"。

设计要点(继承 P13,重申):不运行任意 fork PR 代码于特权常驻 GPU 主机;GPU 测试脚本无仓库 secrets;硬件 job 需维护者审批;**失败硬件检查不得转为 skip**;skipped GPU 测试不得报为 GPU PASS。

## 密钥事件(P14 新增,重要)

P14.0 基线核验时发现:P9 时代的 `windows-training-validation/raw/*.json` 环境快照把宿主 env 的 `ZHIPU_API_KEY` 实值带入 21 个已推送至公开仓库的证据文件。处置:

1. HEAD 全量脱敏(21 文件 + 1 个过期 JWT)+ 提交推送(`e3398d4`);scan_secrets.py 作为常设防护
2. **git 历史中旧 blob 仍在** —— 已向 owner 报告:必须轮换该密钥(轮换是唯一彻底措施);历史改写(可选)需 owner 决定,未擅自执行
3. 本次 P14 新增证据在落盘前先检查,无密钥
