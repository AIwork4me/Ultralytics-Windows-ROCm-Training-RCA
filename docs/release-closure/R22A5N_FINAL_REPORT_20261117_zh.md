# R22A.5N 最终任务报告 — 官方 Nightly 物理预合格(2026-11-17)

- 任务:R22A.5N · Official Nightly Physical Prequalification
- 硬件:AMD Radeon 8060S(gfx1151)· Windows 11(build 10.0.26200.9974)· 驱动 32.0.22032.6002
- 候选:AMD Official Nightly `10.3.0a20261116` 家族 + 发布版 Ultralytics 8.4.214
- 运行 ID:`R22A5N-GFX1151-20261117-A`

## A. 最高裁决

**`R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS`** — 无阻塞项。全部 8 个门
(PKG/G0/G1/G2/G3/G4/G5/G7)由纯函数验收引擎从嵌入事实重算并通过。

核心问题(任务 §17)**已解答:是**——官方含修复(f0a5d266)的 Nightly
MIOpen DLL(3.6.3.25f28906)在物理 Windows Radeon 8060S 上,**无任何手工
workaround**(VCToolsInstallDir 重定向至空目录、INCLUDE 清空、冷缓存、无
HIPRTC shim)的情况下,彻底消除了缺宿主 STL 的 BatchNorm/HIPRTC 编译失败,
且最小 YOLO 训练生命周期(训练/AMP/验证/保存/重载/断点续训)全部真实工作。

本结论为 **Nightly 预合格**,上限即 `*_CANDIDATE_PASS`。不构成 Stable、
双架构或干净安装认证。

## B. Git 状态

| 项 | 值 |
|---|---|
| 起点 SHA | `ff52f87393d66f5773e95b70c1721550d8065b0b`(= origin 集成分支 HEAD,与任务书一致) |
| 任务分支 | `validation/r22a5n-gfx1151-official-nightly` |
| 最终分支 SHA | 见 PR 描述(commit-stable 惯例:报告不含自身提交 SHA) |
| Draft PR | 目标 `work/windows-rocm-training-release-closure`(URL 见 PR,不自动合并) |
| 精确 HEAD CI | `cpu-contract` workflow_dispatch 于合并后集成 HEAD(见 PR 描述) |
| 工作树 | 干净(仅任务新增文件;两个预先存在的 untracked 文件 `bus.jpg`、`windows-golden-path/reports/r22a-gfx1151/SHA256SUMS` 未触碰) |
| 证据路径 | `reports/r22a5n/R22A5N-GFX1151-20261117-A/`(29 文件,SHA256MANIFEST.json 覆盖) |

## C. 包身份

| 项 | 值 |
|---|---|
| 官方源 | `https://nightly.repo.amd.com/rocm/whl-next/` |
| torch | `2.16.0a0+rocm10.3.0a20261116`(cp313,SHA `e1495611…`) |
| torchvision | `0.30.0a0+rocm10.3.0a20261116` |
| rocm-sdk-core / libraries / device-gfx1151 | `10.3.0a20261116` |
| amd-torch-device-gfx1151 / amd-torchvision-device-gfx1151 | `2.16.0a0+…` / `0.30.0a0+…` |
| ultralytics | `8.4.214`(发布版 PyPI wheel,本地哈希锁定安装) |
| sdk-libraries wheel SHA256 | `b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0` = 冻结值(字节级一致,复用 R22A.5A 已验证缓存) |
| 加载的 MIOpen.dll SHA256 | `f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6` = 冻结值(wheel 内成员独立重算 + GPU 子进程内实际加载验证) |
| MIOpen 构建 | `3.6.3.25f28906`,修复标记 ×2 |
| 源谱系 | `f0a5d266…25f28906`:ahead_by=1074,behind_by=0(本次任务经 GitHub compare API 独立重算) |
| 依赖状态 | 46 个发行版全部 SHA 锁定本地安装;`pip check` 零破损;单一 ROCm 10 家族;AMD 栈全部来自官方 nightly 源(仅 rocm-bootstrap 来自既定 PyPI 白名单) |

## D. Windows 与 GPU 事实

- 主机:ASUS ProArt PX13 HN7306EA;Windows 11 `10.0.26200.9974`
- GPU:AMD Radeon(TM) 8060S Graphics,驱动 `32.0.22032.6002`,device_count=1
- gfx 身份:`gfx1151`(capability [11,5];G0/G2/G3/G5 回执一致)
- Python:miniconda 3.13.13 建 venv(cp313 与 wheel ABI 匹配),隔离于 `C:\r22a5n\venv`
- 设备初始化:子进程内真实选中 Radeon 8060S,BN 前反向有限 → G0 PASS

## E. 无-STL 根因验证(G1 — 全任务最关键)

**候选腿**(nightly bytes,新进程,全新 USERPROFILE 冷缓存,
VCToolsInstallDir→空 scratch,INCLUDE="",无 shim):
`nn.BatchNorm2d(100)` × `(20,100,35,45)` 前向+损失+反向+同步+有限检查 →
exit 0,`out_finite=True grad_finite=True loss=0.999990`,16.5s(含 MIOpen
kernel 冷编译)→ **`OFFICIAL_CANDIDATE_PASS`**。

**负对照腿**(`pm13437_official`,官方 pre-fix torch 2.12.0+rocm7.14.1,
其自带 MIOpen.dll `3.5.2.cd957402` 修复标记=0,进程内加载路径已核实为该
环境自有 DLL,等价无-STL 隔离):exit 1 →
**`OFFICIAL_PRE_FIX_EXPECTED_FAIL` / `MIOPEN_HIPRTC_COMPILATION`**,完整
原始 #3956 签名:`MIOpenBatchNormFwdTrainSpatial.cpp` →
`HIPRTC_ERROR_COMPILATION (6)` →
`miopen_type_traits.hpp:151: fatal error: 'type_traits' file not found`。

科学解释:正(候选通过)+ 负(pre-fix 失败)在同一隔离环境下构成配对
因果证据——失败确实由缺宿主 STL 引起,且确实被官方 Nightly 修复消除。

**过程披露(v1 对照无效事件)**:首次负对照误用 `p16_testenv` 意外通过 →
按契约判 INCONCLUSIVE 并调查:该 venv 无自有 MIOpen.dll,Windows 加载器经
搜索路径加载了 `pm13437_merged` 的合并源自建 DLL(3.6.2.f0a5d266,标记=2,
本身已含修复)——即"对照跑的不是 pre-fix 字节"。已换用确证的
`pm13437_official` 重跑(v2)。v1 证据与完整调查保留于
`03_nostl_negative_control/`(亦为本开发主机记录了一条环境教训:无自有
MIOpen.dll 的 venv 会静默继承外来 DLL)。

## F. GPU 算子验证(G2)

全部 PASS 于 gfx1151 真实设备(无 CPU 回退):FP32 GEMM、**FP16 GEMM**、
autograd、Conv2d 前反向、BatchNorm2d 前反向、**torchvision NMS(GPU)**、
张量生命周期;capability [11,5]。P18/P19 类拆轮故障
(hipErrorInvalidDeviceFunction)未出现——amd-torchvision-device-gfx1151 在位。

## G. YOLO 训练与 AMP(G3/G4)

单次短训(框架自身默认,仅限定资源):YOLO26n · COCO128 · 3 epochs ·
imgsz 256 · batch 8 · device=-1(实际选中 GPU 0)· workers=0 · optimizer=auto
· AMP 默认 · nbs 默认。

- 训练损失:box 2.111→1.988→1.897(单调下降);每 epoch 验证均出指标
  (mAP50 ≈ 0.48);48/48 batch 完成;`best.pt`+`last.pt` 产生
- 优化器:请求 `auto` → 框架自选 **AdamW**(fused;114+126+126 参数组)
- AMP:**观测 dtype=float16**(stem conv 96/96 个输出为 FP16,非假设标签)
- 尝试步 / 有效更新 / inf 跳过:**11 / 7 / 4**;每次确认更新时梯度全有限
  (366 张量逐对检查);sentinel 参数位移>0 方计有效(fused AdamW 内核内
  跳过不被计为更新)
- GradScaler:标度史 65536→32768→16384→8192→4096(4 次退避后 6 步稳定)
  ——退避次数从逐步序列计数,非端点推断
- 参数变化:加载视图 248/366 张量 >1e-9(raw trainer 视图 366/366)全有限
- 训练进程内加载的 MIOpen.dll SHA = 冻结候选值(回执记录)
- 裁决:**`NIGHTLY_YOLO_TRAINING_PASS` + `AMP_PASS`**(两独立事实;
  未沿用 DEV 基线计数作判据)

## H. 保存 / 重载 / 续训(G5)

受控生命周期(真实多进程):训练子进程 epoch 1 完成且 last.pt 落盘稳定后
硬终止(TerminateProcess,仅杀本测试自有进程)→ **新进程** `resume=True`
续训 → 第三个进程加载 best.pt 做 GPU 推理。

- checkpoint 哈希:`last.pt=c7b4e593…`、`best.pt=3bc57f7b…`
- 可续性:checkpoint 内 optimizer 状态在位(`has_optimizer_state=True`);
  resume 语义为训练态恢复,非仅载权重
- epoch 连续:终止于 epoch 1(行 2)→ 续训日志
  "Resuming training … from epoch 2 to 3",无重置;终态 rows=4,末 epoch=3
- 续训后继续真实参数更新并完成验证;第三进程重载推理 exit 0
- 裁决:**`NIGHTLY_CHECKPOINT_RESUME_PASS`**

## I. 资源账目(实测)

- GPU 运行进程:10 个(G0×1、G1 候选×1、G1 对照×2、G2×1、G3/G4×1、
  G5×3[训练/续训/推理]、G7×2)
- harness 实测 GPU 活跃墙钟合计:**471.1s ≈ 7.9 分钟**(单次最长 157.6s=G5)
- GPU 峰值显存:未测量(报告如实;无编造)
- 下载:持存 wheels 目录 ≈1.26 GB(46 文件;复用 R22A.5A 已验证的 142MB
  sdk-libraries wheel 零重复下载);pip dry-run 另有元数据获取(进 pip
  缓存,未单独计量)
- 磁盘:任务根 `C:\r22a5n`(venv+runs+scratch)+ 仓库内证据 4.4 MB;开始时
  C: 余 202 GB,全程无磁盘压力
- 重试 4 次,全部留档:① resolver 未传 --torch-version 时标签选择缺陷 →
  按设计传版本重跑(零代码改动);② 安装 MAX_PATH 失败 → 迁移 venv 至
  短路径重装(测试基础设施,详见 01_package_provenance/
  install_incident_maxpath.md);③ 负对照 v1 环境污染 → 换 pm13437_official;
  ④ G7 v1 1-epoch 过短致 GradScaler 退避未收敛 → 3-epoch 重跑

## J. 证据与安全确认

- 冻结 DEV/R22A.5A 证据零改动(`git diff -- evidence/` 空;266 CPU 测试
  全绿含基线 244)
- 全局驱动 / 系统 ROCm / 全局 Python / 既有 venv / 既有 MIOpen 安装:未触碰
- 无 DLL 替换(候选环境安装后 G0 子进程验证加载即冻结字节);无源码自建库;
  无 HIPRTC_COMPILE_OPTIONS_APPEND;无 MIOpen 头注入;未装 MSVC Build Tools;
  无手动 STL 路径;未改已装 torch/ultralytics;非 editable ultralytics;
  无跨环境 kernel 缓存(各腿全新 USERPROFILE 冷缓存)
- 包来源:AMD 栈 100% 官方 nightly 索引 URL + SHA 锁定本地字节安装;纯
  Python 依赖本地锁定;rocm-bootstrap 出自仓库既定 PyPI 白名单;sdist
  `rocm`(元包)构建期 setuptools 来自 pypi.org(安装器既定重试路径,已披露)
- 无凭据/令牌/私人路径入证据;LongPathsEnabled 注册表保持 0(未改系统)
- 环境泄漏扫描(g9_preflight --env-scan):空

## K. GO/NO-GO 矩阵

| 门 | 结果 | 证据(rel. to run dir) |
|---|---|---|
| NIGHTLY_PACKAGE_SET_VERIFIED | PASS | `01_package_provenance/*`(lock+audit 交叉+manifest) |
| G0 运行时身份 | PASS | `02_runtime_identity/g0_child_identity.json`(子进程内 DLL=冻结) |
| NIGHTLY_NO_STL_PASS | PASS | `02_nostl_candidate/` + `03_nostl_negative_control/`(配对因果) |
| NIGHTLY_CORE_GPU_PASS | PASS | `04_gpu_primitives/torchvision_ops.json` |
| NIGHTLY_YOLO_TRAINING_PASS | PASS | `05_yolo_training_amp/adamw_amp.json` + `raw/` |
| NIGHTLY_AMP_PASS | PASS | 同上(dtype 观测+有效更新+scaler 序列) |
| NIGHTLY_CHECKPOINT_RESUME_PASS | PASS | `06_checkpoint_resume/checkpoint_resume.json` |
| workers 0/8 有界 | PASS | `07_reliability/*`(16 spawn 子进程实测+孤儿 CLEAN) |
| **整体** | **R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS** | `08_acceptance/nightly_acceptance.json` |

验收引擎:`scripts/r22a5n/nightly_acceptance.py`(fail-closed 纯函数,
存储 PASS 永不作权威);对抗测试 22/22(伪 PASS、错哈希、混家族、FP32 冒充
AMP、错架构、缺恢复态、孤儿树、Stable 越级等全部被拒)。

## L. 上游交接摘要(本地文档,未外发)

给 Scott Todd / AMD Release Engineering 的要点(全文见
`upstream-handoff-r22a5n.md`,仅本地):
官方 nightly `rocm-sdk-libraries 10.3.0a20261116`(MIOpen 3.6.3.25f28906,
f0a5d266+1074/−0)在 Windows gfx1151(Radeon 8060S,Adrenalin 32.0.22032.6002)
无宿主 STL 环境下通过 BN 回归与配对 pre-fix 负对照;YOLO26n 训练/AMP/断点
续训全绿;仍未决:Stable 通道(7.14.1)仍 pre-fix、rc 10.2.0rc2 pre-fix、
多 ABI/多架构覆盖、G9 干净安装。另附两条打包观察:① `rocm-sdk-device-gfx1151`
内嵌 >203 字符深路径,`LongPathsEnabled=0` 的默认 Windows 上 site-packages
前缀 >57 字符即无法安装;② sdist `rocm` 元包离线安装需索引取 setuptools。

## M. 下一步(均未完成,不因 Nightly 通过而标记)

1. **第二架构(gfx1100)Nightly 验证** — 证据就绪度:中(本引擎/工具链
   直接复用;需 RX 7900 XTX 主机执行)
2. **AMD Stable wheel 发布验证(R22A.5B)** — 未就绪:Stable 通道最新
   10.1.0 仍 OFFICIAL_PRE_FIX,BLOCKED_RELEASE 不变(等待 rocm-libraries#15862)
3. **G9 干净安装验证** — 未就绪:需修复 Stable 轮 + 受控干净镜像;
   本开发主机只能如实记 HOST_REUSE_FRESH_VENV
4. **独立用户测试** — 部分就绪:`golden-path/STABLE_ACCEPTANCE_GUIDE.md`
   流程已就绪,但仅当 Stable 修复轮发布后 PROCEED_CANDIDATE 才会放行;
   Nightly 爱好者可按本报告的锁定清单(01_package_provenance/lock)先行自担试用

## 附:与冻结 DEV 基线的关系

L1 冻结 DEV 证据未被触碰、未混入;本次全部物理观测为独立 L3 记录。
DEV 基线 gfx1151 计数(7 有效/11 尝试/4 退避)与本次恰同形,属巧合性
一致——验收从不以计数相等为判据(引擎按语义重算)。
