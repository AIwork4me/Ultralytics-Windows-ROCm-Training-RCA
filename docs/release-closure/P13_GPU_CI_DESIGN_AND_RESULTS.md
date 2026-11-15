# P13.6 — GPU 回归 CI 设计与执行状态

日期:2026-11-15 · 状态:Layer A **已在上游生效**;Layer B 设计+脚本就绪,实机 CI 执行 **BLOCKED_RUNNER**

## Layer A — 普通 runner(无 GPU;已在上游 PR #27198 生效)

- 语法/lint:docs CI `ruff --extend-select F,I,D,UP,RUF,FA`(P13.1 修复 D103 后 **success**)
- CPU 语义/异常策略/故障注入:`tests/test_check_amp_probe_exception.py` 6 用例(构建/搬移[RuntimeError+OOM]/forward/重入/中断传播)— **在 win/ubuntu/macos/arm、py3.8–3.15 全矩阵 PASS**(14/15 checks success,唯一失败 torch1.8 兼容已修复推送)
- 证据完整性:`verify_release_closure.py` 575 checks(本仓库自验,exit 0)
- 设计原则:故障注入用例 **CPU 可跑且必须真跑**(不准 SKIP 计入 PASS);SKIP 仅允许出现在需真硬件的正控(且本仓库持有 gfx1151 实机正控归档)

## Layer B — Trusted Windows Radeon runner(设计;执行 BLOCKED_RUNNER)

触发:自托管 runner(Owner Action Required — P8 审计同项)。

安全约束(硬性):runner 不持 secrets/特权;PR 代码先在 Layer A 过检 + 维护者审批后才可触达 GPU host;GPU host 跑固定 manifest 集合而非任意 PR 脚本。

Step 集(每步产物强制):
1. `identity`:GPU/驱动/wheel 包清单 + in-process MIOpen.dll SHA256(JUnit+JSON)
2. `primitives`:HIP/MIOpen 原语(=G1 子集,no-STL 回归)
3. `training_smoke`:yolo26n 3ep,验证参数更新数>0(=t16 缩编)
4. `amp_policy`:健康正控 True + 故障注入 False(真机)
5. `lifecycle`:save/reload/resume(G2 子集)
6. `package_integrity`:轮内 DLL SHA 与 G0 manifest 对账

判定:任一 required step SKIP ⇒ 总体 **FAIL**(禁止绿 SKIP);原始日志+JUnit+artifact SHA256 全量归档。

可复现性:harness 即本仓库 `windows-training-validation/scripts/g{1,2,3,4}_runner.py`(已在本机gfx1151 反复使用),CI 只是加 runner 包装;清单命令见 RELEASE_LINEAGE §4。

## 当前执行状态(如实)

| 层 | 状态 |
|---|---|
| Layer A(上游 ultralytics CI) | ✅ 真实执行中(本 PR 的 win/ubuntu/macos/arm/py3.8 矩阵) |
| Layer A(本仓库 verifier) | ✅ 本机执行 575/575 |
| Layer B 实机 CI | ❌ **BLOCKED_RUNNER**(无自托管 GPU runner;本机手动等效执行已覆盖全部 Step 集,证据见 raw/) |
