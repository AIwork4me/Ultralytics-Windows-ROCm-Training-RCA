# P16 FINAL ENGINEERING REPORT (2026-11-15)

Mission P16 — Windows Radeon YOLO three-milestone closure. Chinese summary per mission §11; raw evidence per §10 conventions.

## 1. 实际 Git HEADs

- PR #27198 分支 `checkamp-guard-probe-exceptions`:`fc72b4e`(未再改代码;仅 PR 描述修正)。
- PR #27203 分支 `checkamp-gpu-gates-hip-fallback`:远程 `8ef3e96f` = `d0672bc`(fallback 契约加固)+ `8ef3e96f`(披露式 util 语义修正);本地等内容提交 `66aee88`/`674c893`(API 推送序列化致对象 SHA 不同,tree/blob 逐字节一致)。
- RCA 仓库 `work/windows-rocm-training-release-closure`:本次提交(见 git log)。
- 上游 rocm-libraries #15862 / issue #14 / TheRock releases:无变化(基线冻结见 `P16_BASELINE.md`)。

## 2. 仓库变更

- ultralytics fork:#27203 两个新提交(`ultralytics/utils/autodevice.py` + `tests/test_python.py`);#27198 仅描述。
- RCA 仓库:P16 文档 12 件(本文件 + 11 份 §10 交付物)+ HANDOFF.md §7 附录。

## 3. 修复实现(#27203,15 用例契约审计结论)

- `cuda_device_count()`:nvidia-smi 缺失 → 回落 `torch.cuda.device_count()`(7.14.1/10.1.0 轮子在 gfx1151 上 test_cuda SKIP→PASS 的根修复,CI 已验)。
- `select_idle_gpu()` no-NVML fallback(P16 修复):
  - `min_memory_fraction` 用 `torch.cuda.mem_get_info` **真实强制**(HIP/CUDA 通用;gfx1151 实测 free/total=0.998);
  - 非零 `min_util_fraction` 无法测量 → **显式警告"该判据未验证"后继续选择**(不再静默忽略;严格"不选择"语义会让上游 test_cuda.py 自身的 0.3/0.3 判据在 AMD 上重新全 SKIP — 自审抓出并修正);
  - `indices` 存在性/去重校验(NVML 路径镜像),空列表=合法空限制;
  - 日志与 NVML 路径镜像(Selected/No GPUs met criteria)。

## 4. 复现与验证(全部真实硬件/真实包)

| 验证 | 结果 |
|------|------|
| #27198 两个回归测试(gfx1151 主机) | 2/2 PASSED |
| #27198 健康路径 `check_amp` @ fc72b4e(真实 HIP) | True(且 FDB 警告同现 → P13 共现性结论当场再证) |
| #27203 `test_cuda.py::test_amp`(真实 HIP,修正后 head) | PASSED 12.3s(PR 前 = SKIPPED) |
| #27203 新 no-mock 测试 + test_select_device 回归 | PASSED |
| 端到端 `parse_device("-1")` @ CVD=0(gfx1151) | 警告→mem_get_info 校验→Selected [0],重解析幂等 |
| CPU-only 主机等价性 | 与 CI CPU 路径一致(空/越界/0.2/0.5 全部如实) |
| ruff(format + E4/E7/E9/F) | 全绿 |
| 上游 CI(fc72b4e / d0672bc / 8ef3e96f) | 15/6/0 全绿 ×3 |
| RCA 证据合同 `verify_release_closure.py` | 575 checks / 0 violations |

## 5–7. 根因 / 前后对照 / 阴阳对照

- 根因(P13-P15 已闭,#27198 描述已按 P13 否证结论修正):PR #26967 移除探针异常守卫 → 后端错误炸训练;P16 描述修复消除"缺 FDB ⇒ invalid kernel file"的过时因果暗示(实测:警告在场 + probe PASS)。
- 阴性对照:官方 7.14.1/10.1.0 轮子 no-STL FAIL(P14/P15 归档,今日 SHA 逐字节一致故继承);阳性对照:合并源码构建 PASS;`test_amp` PR 前 SKIP/PR 后 PASS 对照;严格 util 语义→SKIP 回归(自审阴性发现)→披露语义→PASS。

## 8–11. PR 状态与 CI

- #27198:OPEN,PR_READY;CLA ✅;CI 15/6/0;无未决评审线程;待人工评审。
- #27203:OPEN,PR_READY;CLA ✅;CI 15/6/0(两个新 head);bot 空索引发现已修复并有根因评论;待人工复审 d0672bc/8ef3e96f。

## 12–13. 官方轮子溯源与 no-STL

见 `P16_OFFICIAL_WHEEL_BINARY_AUDIT.md` / `P16_NO_STL_RELEASE_ACCEPTANCE.md`:**BLOCKED_RELEASE 维持**(渠道无新轮;SHA 逐字节一致;marker=0;缺 2026-10-19 后的发布切片)。

## 14–18. M3 各腿

见 `P16_TWO_GPU_WINDOWS_MATRIX.md`(class A 硬件在场但官方路径 BLOCKED_RELEASE;class B BLOCKED_HARDWARE)、`P16_NVIDIA_UX_PARITY_RESULTS.md`(BLOCKED_HARDWARE,零虚构)、`P16_INDEPENDENT_USER_ACCEPTANCE.md`(issue #14 无人响应 → BLOCKED_INDEPENDENT_USER_TEST)。

## 19. 用户文档

见 `P16_WINDOWS_USER_GUIDE_READINESS.md`:官方文档现状如实(Linux-only);指南草稿就绪,发布门槛 = M2 解锁 + class-A 官方腿 PASS + 独立验收,当前不向 Ultralytics 提交(否则为虚假声明)。

## 20. 遗留阻塞与 owner(全部)

| 阻塞 | Owner | 下一步 |
|------|-------|--------|
| M1 两 PR 合并 | ultralytics 维护者 | 等待人工评审;有实质新发现再 ping |
| M2 无修复版官方包 | AMD/TheRock 发布链 | 切 post-fix 发布切片;#15862 证据待命 |
| class B / NVIDIA 主机 | 用户提供硬件 | 平台模板已就绪 |
| 独立测试者 | @LZ-QWQ / 公开邀请 | M2 解锁后可执行 |
| GPU CI runner | 上游/基础设施 | fork 无 AMD Windows runner;BLOCKED_RUNNER |
| 本机 7 个不可杀 HIP 僵尸进程(6 个 11-14 日 + 1 个 12:51)+ teardown 高频挂死 | 用户 | 重启清除;不影响新进程 GPU 工作 |

## 21–22. 三里程碑判定与开发者可见改善

- **M1: IN_PROGRESS(PR_READY,BLOCKED_MAINTAINER)** — 两 PR 技术就绪、CI 终绿、零未决线程、真实硬件证据。
- **M2: BLOCKED_RELEASE** — 今日密码学级重证。
- **M3: NOT_MET**(阻塞如上,精确到 owner)。
- **总体:NO-GO(端用户视角)/ 源码侧工程全部完成并验证。**
- 开发者可见改善(合入后生效):Windows AMD HIP 用户 `torch.cuda.is_available()` 门打开、GPU 测试不再被 NVIDIA-only 门整体 SKIP、`device=-1` 在无 NVML 主机可用且判据如实披露、check_amp 探针异常降级 FP32 不炸训练。
