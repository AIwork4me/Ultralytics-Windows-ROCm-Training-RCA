# R22A.5N gfx1100 官方 Nightly 物理预鉴定 — 最终报告(中文)

任务:R22A.5N-GFX1100 Official Nightly Physical Prequalification
运行 ID:`R22A5N-GFX1100-20261117-A` · 报告时间:2026-11-17(UTC)

---

## A. Executive Verdict(最高正当裁定)

**`R22A5N_GFX1100_NIGHTLY_EVIDENCE_AUDITED_PASS`**(单架构允许的最高裁定)

9 个门禁(PKG / LK / G0 / G1 / G2 / G3 / G4 / G5 / G7)全部由
`scripts/r22a5n1100/nightly_acceptance.py`(引擎版本 `r22a5n1100-acceptance-v1`)
从本次物理证据独立重算通过,原始裁定见
`09_acceptance/nightly_acceptance.json`。

- 无阻断项。
- 阻塞 Stable 认证的外部条件不变:AMD Stable 渠道(10.1.0)仍为 pre-fix
  (rocm-libraries#15862 未发布),G9 clean-Windows 验收仍未开放。
- 本裁定**不是** `OFFICIAL_STABLE_PASS`,也不构成双架构 Stable 主张。

## B. Exact GitHub State(精确 GitHub 状态)

| 项 | 值 |
|---|---|
| 仓库 | `AIwork4me/Ultralytics-Windows-ROCm-Training-RCA` |
| 任务分支 | `validation/r22a5n-gfx1100-official-nightly` |
| 分支基点 | PR #22 HEAD `568981db3d1ed4f3ef3fd068623603aee0111fb4`(OPEN,未合并) |
| PR #22 head 与本地基点一致性 | 已核实(origin == 本地 == 任务锚点) |
| 集成分支 HEAD | `ff52f87393d66f5773e95b70c1721550d8065b0b`(审计锚点,未动) |
| PR 形态 | **Stacked Draft PR**,base = `validation/r22a5n-gfx1151-official-nightly`(PR #22 head 分支),明确声明依赖 PR #22 |
| 最终 SHA / PR URL / CI URL | 见 PR 描述(推送与 exact-HEAD CI 后回填;本地工作树状态在推送时干净) |

## C. Hardware/Software Identity(硬件/软件身份)

| 项 | 值 |
|---|---|
| GPU | AMD Radeon RX 7900 XTX(Navi31,24.0 GB,multiproc 48;torch 实测 total_memory 24.0 GB) |
| GFX target | `gfx1100`(torch 设备名 → gfx 映射 + CIM 适配器交叉核对) |
| Windows | Windows 11 10.0.26300(26H2 内部版本线) |
| 驱动 | 32.0.21030.2001 |
| 多 GPU 主机说明 | 同时存在 Intel UHD 770 核显与 GameViewer 虚拟显示器适配器;G0 子进程实测 `device_count=1` 且设备名为 RX 7900 XTX,无身份歧义 |
| Python | 任务 venv `C:\r22a5n1100\venv`,CPython 3.12.16(**cp312**,按 gfx1100 安装计划) |
| torch | `2.16.0a0+rocm10.3.0a20261116`(cp312 win_amd64) |
| torchvision | `0.30.0a0+rocm10.3.0a20261116` |
| ROCm SDK | core/libraries/device-gfx1100 全部 `10.3.0a20261116` |
| ultralytics | `8.4.214`(正式 PyPI 包,只读安装) |
| 隔离 | 新短路径 `C:\r22a5n1100\`;未触碰系统驱动/全局 Python/历史环境/MSVC;SAC 已由用户于 2026-11-13 关闭(本任务预检 recorded policy state=0) |
| 零 workaround | 全程 `env -u HIPRTC_COMPILE_OPTIONS_APPEND` 运行;无 DLL 手工替换、无 header 注入、无 shim、无 CPU 回退、无错误吞并;用户级持久化 shim 变量保持原样(仅在任务进程中剥离) |

## D. Binary Provenance(二进制溯源)

- 官方渠道:`https://nightly.repo.amd.com/rocm/pytorch/whl-next/` +
  `/rocm/core/whl-next/` + PyPI(ultralytics 及第三方纯 Python 依赖)。
- 依赖锁:`01_package_provenance/resolved_wheel_lock_nightly_gfx1100.json`
  — 46 个包,`pip install --dry-run --report` 精确元数据解析,pip 依赖闭包,
  全部 wheel 下载并记录 SHA256;SDK 包显式 pin 到 **20261116**(索引已出现
  20261117,为与 gfx1151 可比性按任务 §2.2 固定快照)。
- 混装规则重算:ROCm family 单一(10)、device wheel 齐
  (`rocm-sdk-device-gfx1100` + `amd-torch-device-gfx1100` +
  `amd-torchvision-device-gfx1100`)、torch 为 AMD HIP 官方渠道构建、
  ABI cp312 全兼容、来源政策零违规。
- **共享 MIOpen 候选身份(与 gfx1151 字节一致,独立再验证)**:
  - SDK Libraries wheel SHA256
    `b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0` ✓
  - 内嵌 MIOpen.dll SHA256
    `f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6`,
    build `3.6.3.25f28906`,PR#13437 标记 `miopen_initializer_list` ×2 ✓
  - 源码谱系(活体 GitHub compare API):`f0a5d266…→25f28906`
    ahead_by=1074,**behind_by=0**(修复为祖先)✓
  - 本机下载字节即安装字节即子进程加载字节(wheel 审计与 venv 安装同源,
    G0/G1/G2/G3 回执内的 in-child SHA 逐一等于上值)。
- 安装后差异:installed-vs-lock 差异为**空**;`pip check` 无损坏依赖;
  完整 distribution manifest 见 `installed_manifest.json`(47 dist)。

## E. Physical No-STL Validation(G1 物理验证)

- **正例 ×2(独立冷启动)**:`verify_miopen_nostl.py --leg official
  --expect CANDIDATE --channel nightly`,两次独立子进程
  (PID 5424 / 11924)、两个互不相同的冷缓存 scratch 家目录;
  `nn.BatchNorm2d(100)`,输入 `(20,100,35,45)`,forward+loss+backward+
  synchronize,输出与梯度全部有限;exit 0;分类
  `OFFICIAL_CANDIDATE_PASS`;无 HIPRTC shim;in-child MIOpen SHA
  = `f9312c3e…`(子进程实际加载,非父进程推断)。原始日志:
  `03_nostl_candidate/raw/candidate_trial{1,2}_leg.log`(无 pre-fix 签名)。
- **负对照(pre-fix 官方栈)**:使用本机既有、经独立审计的官方 pre-fix
  环境 `C:\P18\venv`(torch `2.12.0+rocm7.14.1`,repo.amd.com
  whl-multi-arch 官方渠道;venv 自带 pre-fix MIOpen.dll
  SHA `e97891df…`,marker=0 —— 与 gfx1151 审计过的 pre-fix 对照 DLL
  **字节相同**):exit 1,失败签名 `MIOpenBatchNormFwdTrainSpatial.cpp` /
  `HIPRTC_ERROR_COMPILATION (6)` / `'type_traits' file not found`
  (原始日志中出现 2 次);**at-failure 子进程 DLL 身份**已捕获
  (`e97891df…`,非候选字节);分类 `OFFICIAL_PRE_FIX_EXPECTED_FAIL`。
  原始日志:`04_nostl_negative_control/raw/negctrl_leg.log`。
- 科学边界(如实声明):正负对照为不同软件版本组合(7.14.1 vs
  10.3.0a20261116),非严格单变量实验;结论强度为
  "源码谱系 + 二进制溯源支持下的强行为回归证据"。

## F. Core GPU Operations(G2)

`05_gpu_primitives/torchvision_ops.json`:9/9 门禁 PASS ——
cuda_available、device_identity(gfx1100)、FP32 GEMM、FP16 GEMM、
autograd、Conv2d 前后向、BatchNorm 前后向、**torchvision GPU NMS**
(amd-torchvision-device-gfx1100 已装,未触发 invalid device function)、
tensor lifecycle。数值明细全部有限;`cpu_fallback_used=False`;
加载 DLL SHA = `f9312c3e…`;exit 0。

## G. YOLO and AMP(G3/G4)

- 配置:YOLO26n + COCO128,3 epochs,imgsz 256,batch 8,**workers 0**,
  optimizer **auto**,AMP 默认,nbs 默认,device 自动选择 → 实测
  RX 7900 XTX;COCO128 数据集 YAML SHA 已入回执。
- 结果(全部由验收引擎从 `per_step_events` 原始序列重算,与存储计数对账):
  - 优化器:auto → **AdamW**(fused);48 个 batch 完成。
  - AMP:`autocast_dtype_observed=float16`;stem-conv dtype 直方图
    `{float16: 96}`(96/96 低精度);autocast 前向采样 48/48 enabled。
  - 优化器步:尝试 **11**,有效更新 **7**(sentinel 参数位移>0 且梯度有限),
  found_inf 跳过 **4**;GradScaler scale 历史 11 点、退避 4 次,
    逐点对账(每次 inf 跳过后 scale 下降,无漏退避)。
  - 参数变化:248 个张量位移 >1e-9,全部有限;checkpoint 存在。
  - mAP50(B) 逐 epoch:0.48331 / 0.47806 / 0.47440 / 0.48426。
  - 训练壁钟 101.2 s;exit 0;`ADAMW_AMP_MULTISTEP_PASS`。
  - 回执内加载 MIOpen SHA = `f9312c3e…`;wheel-lock 绑定
    (SHA + channel + gfx + runtime 版本)经 `verify_lock_binding` 通过。
- gfx1151 的 11/7/4 只是参考;gfx1100 数值为本机独立观测,非目标对齐。

## H. Checkpoint Resume(G5)

`07_checkpoint_resume/checkpoint_resume.json`(`verify_checkpoint_resume_v2`):

1. 独立训练进程启动(4 epochs,batch 4);epoch 1 完整落盘后受控终止。
2. kill 时 checkpoint SHA256 `4e20658a…4bec5`(先哈希再杀);
   `has_optimizer_state=True`,ckpt epoch=0。
3. **新进程** `resume=True`:exit 0,`RESUME_DONE`;
   `start_epoch=1`;恢复后优化器 state 条目 **366**(非空,证明真恢复);
   恢复后有效更新 **8/8**(sentinel 位移);
   epochs 行 2→5,`last_epoch_value=4`(连续性由数字事实重算,非布尔)。
4. 第三进程加载 best.pt GPU 推理:exit 0,`INFER_OK`。
5. 最终 last.pt SHA `f614a39b…`、best.pt SHA `63827604…`;
   **实际字节已提交**于 `07_checkpoint_resume/bytes/`(5.5 MB ×2,
   SHA 与回执一致,审阅者可直接复哈希)。
6. 状态类(gfx1100 独立观测,非复制 gfx1151 结论):model/EMA、optimizer、
   epoch、best_fitness、train_args、GradScaler(scaler)**已序列化**;
   **LR scheduler 未被上游序列化**(`NOT_SERIALIZED_BY_UPSTREAM`,
   resume 时由 train_args 重建)。
   → 按加固语义,裁定为 **`RESUME_PASS_CORE_STATE_VERIFIED`**,
   不主张 `FULL_TRAINING_STATE_RESTORE_PASS`(限制如实披露;
   加固后引擎仅当 scheduler 真实序列化并恢复时才允许 FULL)。

## I. Workers and Reliability(G7)

- 第一次尝试(已保留并披露):训练本体 PASS(11/6/5),census 记录
  16 个同时子进程,但快照 cmdline 截断为 160 字符,导致本任务加固引擎
  无法从原始快照重认 trainer 身份(venv 重定向拓扑下真实 trainer 的
  脚本名落在截断之外)→ 引擎正确拒绝。事件与修复记录:
  `08_workers_reliability/attempt1_incident_census_truncation.md`。
- 第二次尝试(修复 capture 至 400 字符后,规范回执):
  - workers=8 训练:`ADAMW_AMP_MULTISTEP_PASS`,exit 0,
    11 尝试 / 6 有效 / 5 inf-skip(引擎从 per-step 重算并对账)。
  - 训练中活体 CIM 快照:peak 快照(单一时刻)trainer
    pid 与存储一致;**16 个同时子进程,16/16 cmdline 含
    `multiprocessing.spawn_main`,PPID 全部等于 trainer PID,
    PID 唯一**;非 spawn 子进程单列不计数。
  - trainer↔envelope 链:venv 重定向链
    envelope→worker_stage→…→trainer 从原始快照重走验证一致。
  - 退出后孤儿检查:baseline 披露 [2492,4428,7788,16324];
    重算 leftover=[](**CLEAN**,存储 verdict 仅被 diff,不作依据);
    本任务进程树无遗留。
  - 原始 stdout/stderr 与 envelope 全部入库
    (`08_workers_reliability/raw/` + `stage_logs/`)。

## J. Resource Usage(资源使用,如实计量)

- 物理 GPU 尝试次数:10 个 envelope attempt(G0 1、G1 3、G2 1、
  G3/G4 2(1 次失败:相对路径误用,未触及 GPU)、G5 1、G7 2),
  全部保留于 `stage_logs/`。
- GPU 活跃时间(粗粒度,由各阶段 duration_s 汇总):G0 ≪1 min;
  G1 三腿各 ~0.2–0.5 min;G2 ~0.4 min;G3/G4 101.2 s;G5 全生命周期
  (4+3 epochs 两段训练 + 恢复 + 推理)~3 min;G7 两次各 ~2.5 min。
- 下载:46 个官方 wheel 共 **1529.1 MB**(本地 wheels 目录 1459 MiB);
  venv 解包后 4880 MiB;任务前后 C: 剩余 ~566–607 GB(无压力)。
- GPU 显存实测:24.0 GB total;单卡训练占用未逐一采样(未发明指标)。
- 网络:nightly.repo.amd.com / PyPI 稳定;gh api 正常;未触发 github.com
  中断。

## K. Evidence Completeness(证据完整性)

`reports/r22a5n/R22A5N-GFX1100-20261117-A/`(78+ 项,SHA256SUMS +
SHA256MANIFEST 覆盖,producer git SHA 记录):

- 00_preflight(宿主/设备/SAC/锚点 SHA)
- 01_package_provenance(discovery、46-wheel lock、requirements-lock、
  wheel_audit_gfx1100、install log、installed_manifest)
- 02_runtime_identity(G0 回执 + 子进程原始日志)
- 03_nostl_candidate(2 试次回执 + 原始 leg 日志)
- 04_nostl_negative_control(回执 + 原始日志)
- 05_gpu_primitives(9 门禁数值明细)
- 06_yolo_training_amp(回执 + results.csv + envelope 原始 stdout/stderr)
- 07_checkpoint_resume(回执 + 三阶段子进程原始日志/脚本 + 源码 +
  lifecycle envelope + **checkpoint 实际字节**)
- 08_workers_reliability(规范回执 + census + orphan + envelope +
  attempt1 全套 + 事件报告)
- 09_acceptance(独立验收 JSON,exit 0)
- stage_logs/(全部 10 次 envelope 尝试,含失败与重试)
- SHA256MANIFEST.json / SHA256SUMS.txt、对比文档、本报告、交接草稿

## L. Adversarial Audit(对抗审计,CPU)

- 新增 `windows-golden-path/tests/test_r22a5n1100_cpu.py`:**61 项**,
  覆盖任务 §13.1 全部伪证类:gfx1151 回执冒充 / gfx1151 device wheel 混入 /
  错误 ABI / 错误家族 / 错误 wheel SHA / 错误 lock SHA / 错误 DLL /
  伪造 no-STL PASS(shim、错 DLL、复用 PID、复用缓存)/ 缺负对照 /
  缺原始日志 / per-step 计数矛盾 / FP32 冒充 AMP / 无有效更新报 PASS /
  GradScaler 历史矛盾 / checkpoint SHA 错 / epoch 事实缺失(fail-closed)/
  scheduler 未恢复宣称 FULL(封顶)/ 假 worker PID / 错 PPID /
  假 spawn_main / 跨时刻 PID 拼接 / 伪造孤儿 CLEAN / Nightly 晋级 Stable /
  gfx1151 验收 JSON 整体复制 / **PPID 环数据不使引擎死循环**等。
- 历史 gfx1151 测试全部原样通过:全仓 CPU 套件 **372/372 PASS**
  (311 历史 + 61 新增)。
- 仓库级证据审计 `scripts/verify_release_closure.py`:**902 检查 / 0 违规**
  (含新增证据树之后的整库一致性)。

## M. gfx1100 vs gfx1151(跨架构对比)

详见 `R22A5N_GFX1100_VS_GFX1151_COMPARISON.md`。要点:同一 2026-11-16
官方 Nightly 字节(b11baad9 / f9312c3e / behind_by=0)在两架构各自物理
主机通过全部门禁;workers=0 的 GradScaler 形状同为 11/7/4(观测非目标);
mAP50 轨迹接近但不相同(0.48331↔0.48349 起,0.48426↔0.48451 收);
G5 语义差异(gfx1151 旧引擎 FULL vs gfx1100 加固封顶 CORE)与 G7
census 截断缺陷均已如实披露。双架构功能可移植性成立:
`NIGHTLY_DUAL_ARCH_FUNCTIONAL_EVIDENCE_COMPLETE`(待 owner 对两包
独立复核后使用);**不是** `OFFICIAL_STABLE_PASS`。

## N. Release Engineering Handoff(交接草稿)

见 `RELEASE_ENGINEERING_HANDOFF.md`(面向 owner 审阅后转 Scott Todd 的
简明事实简报:修复标识、双架构证据、渠道状态、Stable 阻塞点、G9 前提)。

## O. Next Actions(下一步)

1. gfx1100 Nightly 证据已可交 owner 审阅(本 Draft PR;依赖 PR #22)。
2. 仍被 AMD Stable 发布阻塞:Stable 渠道(10.1.0)MIOpen 仍为 pre-fix;
   需上游将含 #13437 的 rocm-libraries 发布进 Stable 后重跑
   R22A.5B/Stable 门禁(gfx1151 + gfx1100 + clean-Windows 三线)。
3. G9 clean-Windows 验收前提:无 shim/无手动 DLL/全新 Windows + 全新
   venv 的最终用户路径;建议在 Stable 候选发布后以
   `release-provenance/r22a5a/g9_preflight_*.json` 契约执行。
4. 建议 owner 复核 gfx1151 包 G5 的 FULL 措辞(见 M 节语义差异)。
