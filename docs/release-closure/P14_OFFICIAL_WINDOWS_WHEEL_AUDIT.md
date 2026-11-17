# P14.1 — 官方 Windows wheel 审计(通道矩阵 + 二进制溯源 + no-STL 运行时对照)

日期:2026-11-15 · 执行环境:Radeon 8060S (gfx1151) / Windows 11 26200

## 结论(TL;DR)

1. **P13 的"官方通道无更新 Windows 轮"结论已被部分推翻**:`stable.repo.amd.com/rocm/whl-next/` 是 P13 未覆盖的第二个官方索引,现提供 Windows win_amd64 包:torch 2.11.0+rocm10.0.0 → **2.14.0+rocm10.1.0**(cp310–cp314),及配套 `rocm_sdk_libraries/core/device-gfx1151` 10.0.0/10.1.0、`rocm-bootstrap`、`rocm`(meta sdist)。
2. **但新轮仍是修复前二进制**:whl-next `rocm_sdk_libraries-10.1.0` win 包内 MIOpen.dll(sha256 `266d716b…`)版本串 `3.6.1.39d8d603` → 构建 commit `39d8d603` 日期 **2026-09-16**,早于 PR #13437 合并 `f0a5d266`(**2026-10-19**);修复标记 `miopen_initializer_list` = 0(已修复参照 = 2)。torch 2.14.0+rocm10.1.0 依赖 `rocm[libraries]~=10.1.0` → 同一未修复 SDK。
3. **运行时证据(三腿 no-STL 对照,同 GPU 同会话)**:LEG A(官方 7.14.1 旧轮)FAIL、**LEG B(whl-next 10.1.0 新轮)FAIL(与历史 #3956 签名逐字一致)**、LEG C(工程参照,合并源码构建)PASS。→ **BLOCKED_RELEASE 维持,现覆盖全部已知官方通道,并升级为运行时证据**。
4. **正面发现**:whl-next torch 2.13.0+rocm10.1.0 在本机(Radeon 8060S + 现有驱动)**可正常完成真实 GPU 计算**(`torch.version.hip=7.16.26385`,`cuda.is_available()=True`,GPU 张量运算有限值)。一旦 SDK 携带修复,该通道即可作为新 Golden Path 基座。

## A. 通道矩阵(2026-11-15 实测)

| 通道 | Windows torch 版本 | 配套 SDK | 自 P13 变化 |
|---|---|---|---|
| `repo.amd.com/rocm/whl-multi-arch/` | 2.9.1+rocm7.13.0 … **2.12.0+rocm7.14.1** | rocm_sdk(7.x 系) | 无 |
| `stable.repo.amd.com/rocm/whl-next/` | 2.11.0+rocm10.0.0 … **2.14.0+rocm10.1.0** | rocm_sdk_libraries/core/device 10.0.0/10.1.0 + rocm-bootstrap 0.3.0 + rocm meta sdist | **新发现** |

安装依赖链(torch 2.13.0+rocm10.1.0 实测 METADATA):`torch → rocm[libraries]~=10.1.0 + rocm-bootstrap`;`amd-torch-device-gfx1151 → torch==2.13.0+rocm10.1.0 + rocm-sdk-device-gfx1151~=10.1.0`。pip 从 whl-next 索引即可完整解析安装(实测成功)。

## B. 二进制溯源(§4.2 逐项)

下载 wheel SHA256 与包内 DLL 身份:`P14_WHEEL_BINARY_PROVENANCE.json`(含索引页快照,存 `release-provenance/raw/p14_wheel_audit/`)。

- 包内 `MIOpen.dll`:496,074,240 B,sha256 `266d716bab4aaf4ec3bb7492d35f6b65473982bc38f22b14235863a15c1429b4`,版本串 **`3.6.1.39d8d603`**
- GitHub API 核验:`39d8d60365d2272a5366f76ccb3bfba24b219eaf` = 2026-09-16(hipblaslt 修复 commit)< `f0a5d266`(2026-10-19,#13437 squash 合并)
- 标记校准(方法:PR #13437 引入 freestanding 头 `miopen_initializer_list.hpp` 等,修复后二进制内嵌 HIPRTC 源码含该头文件名):

| 二进制 | 版本串 | `miopen_initializer_list` | 状态 |
|---|---|---|---|
| 官方 7.14.0 轮(yolo_amd) | — | 0 | 未修复 |
| 官方 7.14.1 轮(ENV A) | 3.5.2.cd957402 | 0 | 未修复 |
| **whl-next 10.1.0 轮(p14_whlnext)** | **3.6.1.39d8d603** | **0** | **未修复** |
| 合并源码构建(ENV B,参照) | 3.6.2.f0a5d266 | 2 | 已修复 |

注:`miopen_type_traits` 单独出现**不是**判别器(未修复二进制中也有 12 次);有效判别器为 `miopen_initializer_list`。

## C. no-STL 运行时负对照(§4.3 三腿)

复现器:原始 MIOpen Issue #3956 最小复现(BatchNorm2d(100) forward+backward);no-STL 技术:`VCToolsInstallDir → 空目录`(P13437 已验证;仅清 INCLUDE/PATH 无效);每腿 USERPROFILE 重定向 → 全新 MIOpen 缓存;顺序执行无 GPU 实验并发。

| 腿 | 环境 | torch / MIOpen | 结果 | 签名 |
|---|---|---|---|---|
| A(历史官方轮,未修复) | pm13437_official | 2.12.0+rocm7.14.1 / 3.5.2.cd957402 | **FAIL(exit 1)** | `HIPRTC_ERROR_COMPILATION (6)` → `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found` → `miopenStatusUnknownError` |
| **B(官方新候选轮,whl-next 10.1.0)** | p14_whlnext | **2.13.0+rocm10.1.0 / 3.6.1.39d8d603** | **FAIL(exit 1)** | **与 A 逐字一致** |
| C(工程参照,非发布物) | pm13437_merged | 2.12.0+rocm7.14.1 / 3.6.2.f0a5d266 | **PASS(exit 0)** | loss=0.999990,y/grad 有限值 |

证据:`P14_NO_STL_COMPARISON.json`;原始日志 `release-provenance/raw/p14_wheel_audit/leg{A,B,C}_*.log`(SHA256 见 JSON)。

真实 PASS 判定 = 原缺失宿主 STL 失败消失 + GPU 计算有效。LEG B 未满足 → 不升级 GATE 3。

## D. 对上游 #15862 的影响(§4.4)

已发布证据更新(见本仓库评论存档):新通道存在、二进制与运行时双重证据表明仍未修复、发布链切点升级(39d8d603 → 3.6.1 轮)。BLOCKED_RELEASE 结论不变;不重复开 issue;路由建议不变(修复在 rocm-libraries develop,轮子打包由 TheRock/AMD 发布链负责)。

## E. 隔离纪律执行记录

- 全新 conda env `p14_whlnext` 独立安装,未触碰 ENV A / ENV B / yolo_amd
- 未执行任何原地 DLL 替换;ENV B 仍为 P13 记录的 SOURCE_BUILT_PATCHED 锁定态(仅作 LEG C 参照读取)
- 无.gpu 并发实验;每腿独立缓存目录
