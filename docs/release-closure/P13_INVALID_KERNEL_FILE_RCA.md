# P13.2 — hipErrorInvalidKernelFile RCA(混合 MIOpen 栈)

日期:2026-11-15 · 执行:MISSION P13 TRACK B · 状态:**原 P9 根因假设被部分推翻;崩溃当前不可复现;真实根因 UNRESOLVED(两个候选收敛中)**

## 1. 历史失败(P9,2026-11-14T16:20–16:50Z,已存档)

ENV B 混合栈(官方 rocm 7.14.1 wheel 包 + 源码构建 MIOpen 3.6.2 f0a5d266 DLL,hash `ed7c67a9…`)上,8.4.197+ 新 check_amp 探针:

```
torch.AcceleratorError: CUDA error: invalid kernel file
Search for `hipErrorInvalidKernelFile' ...
  File ".../torch/nn/modules/conv.py", line 560, in _conv_forward   ← F.conv2d
```

证据:`windows-training-validation/raw/g3_checkamp84212_ENV_B_patched.json`(default + warm 两 mode,900s KILLED_AFTER_NO_RESULT — 异常抛出后子进程在 HIP teardown 挂起,stderr_tail 内含完整 traceback);commit ed9a29c 记录 "3/3 deterministic"。

## 2. 本轮(P13)受控实验矩阵 — 同一 ENV B、同一 DLL hash、同一 default 缓存

| # | 实验 | 配置 | 结果 |
|---|---|---|---|
| E1 | 最小原语 4 阶段(隔离全新缓存) | fp32 conv / **fp16 conv fwd** / fp16 conv bwd / fp16 BN train fwd+bwd | **4/4 PASS**(`p132_minconv_20261114T235834Z.json`) |
| E2 | 插桩逐层探针(隔离全新缓存) | 复刻 compare_amp,yolo26n 全部 128 个 Conv2d/Attention 逐层 fp16 重算 + 5% 范数检查 | **128/128 PASS**,数值全 close(`p132_probe_20261114T235942Z.json`) |
| E3 | 真实 check_amp(带守卫 @124de39,**default 缓存**) | 同 P9 default mode 配置 | **True,11.2s,无异常**(`p132_checkamp_real_20261115T000107Z.json`) |
| E4 | 精确复刻 P9 harness 调用(子进程+PYTHONPATH+yolo26n.pt) | 同 P9 逐项 | (结果见 raw `p132_ec_*`) |

**结论:崩溃在当前状态下不可复现**(至少 3 种独立调用方式 × 2 种缓存模式)。

## 3. 对 P9 假设的三个修正(证据)

P9 假设:"混合 bin 目录 fdb 不可读 → 运行时编译产生坏 kernel 对象"。

1. **"unreadable" = 文件不存在,不是权限/损坏**。两环境 `_rocm_sdk_libraries\bin` 均无任何 `.fdb.txt`(ENV A 20 项、ENV B 21 项全列核验;MIOpen 源码 `readonlyramdb.cpp::Prefetch` 在 `MIOPEN_EMBED_DB=OFF` 时对缺失文件打警告)。源码构建树 C:\b58m 也无 FDB。
2. **ENV A(官方 3.5.2,全 PASS)从不发起此查找**(全日志 0 条 ParseAndLoadDb 警告;ENV B 6 条)— 这是 **3.6.2 源码构建行为差异**(版本耦合),不是打包损坏。
3. **该警告非致命**:E2 在警告持续存在的情况下 128/128 层重算 + 数值检查全通过 → "缺 FDB ⇒ invalid kernel file" 因果链**被否定**。

## 4. 剩余候选(按当前证据强度)

| 候选 | 支持证据 | 待判别 |
|---|---|---|
| C1:HIP 程序/代码对象缓存瞬态(DxCache 类)在冷编译期与 teardown 挂起的僵尸进程交互 | P9 崩溃运行自身 hang 在 teardown;今日同缓存同 DLL 全 PASS,仅时间窗不同 | 需要重建 P9 时刻状态(不可得,见 §5) |
| C2:iGPU 共享内存/并发 GPU 状态(P9 时 4 个 ~2GB ghost 进程 + 批次 2 长训残留) | ghost 在 P9 崩溃前后均存在(14:55–15:43Z 创建),今日仍存在且 PASS → 削弱 | 重复 E3 于高内存压力下(可做) |
| C3:混合栈真缺陷(3.6.2 codegen × 7.14.1 官方 HIPRTC 运行时)仅在特定冷编译序列触发 | E2 冷编译 128 形状全过 → 削弱 | **E5:ENV B 换官方 DLL 单组件对照**(被 DLL ghost 锁阻塞) |

**观测到但未定性的伴随异常**:E2 通过运行中再次出现 `EvaluateInvokers 负计时(solver_finders.cpp:535, elapsed<=0)` — 与 #15861 同型,见 P13.7。

## 5. 证据保全限制(如实记录)

- default 缓存 `gfx115128.HIP.3_6_2_f0a5d266.ufdb.txt` 在 E3 前后 size 一致(757321 B,pre-run hash 已存 `p132_default_cache_state_before.json`),但 E3 运行刷新了 mtime — P9 时刻的精确缓存状态无法完整重建。
- P9 的 `raw/checkamp84212_envB_logs/` 目录在仓库工作树中不存在(ca88a11 只提交了 harness);完整 stderr 尾部保留在 `g3_checkamp84212_ENV_B_patched.json` 的 stderr_tail 字段(两 mode 各 2000 字符,含完整 traceback 关键段)。

## 6. 下一步(按优先级)

1. **E5 单组件对照**(ghost 解锁后):envb_dll_swap restore → ENV B 官方 DLL → 复跑 E2/E3 → 隔离"源码构建 3.6.2 DLL"是否为必要成分。
2. C2 判别:并发 2×2GB GPU 占用下复跑 E3(可脚本化,不污染证据)。
3. 若 E5/E-C 仍不可复现:RCA 维持 UNRESOLVED,把 C1/C2/C3 三候选 + 已否定假设归档;对上游不提交任何"修复"(禁止无复现的补丁)。
4. #15862 若发布新官方 wheel:在"全官方一致环境"重验(§6.3 of mission)。

## 7. 与 GATE 的关系

本缺陷**不阻塞** GATE 1(ENV A 官方栈全 PASS、AMP 可用);GATE 3/4 的阻塞独立存在(BLOCKED_RELEASE)。P9 的 "ENV B 混合态确定性崩溃" 表述应降级为:"P9 会话状态窗口内 3/3 崩溃(已存档),P13 复验不可复现,根因 UNRESOLVED" — P13.8 文档对账时执行此修正(不重写历史 raw,只改 verdict 层)。
