# Golden Path — Stable 验收指南(独立开发者执行包)

状态(2026-11-17):**BLOCKED_RELEASE 等待官方修复轮**。本指南面向**从未参与本
RCA 项目**的独立 Windows 开发者:当官方发布包含 MIOpen 修复
(rocm-libraries#13437)的 Windows wheel 后,按本指南独立完成验收并回报结果。
在此之前,`g9_preflight.py` 会以 BLOCKED_RELEASE 拒绝进入 Stable 验收——
这是设计行为,不是故障。

## 0. 你需要什么

| 项 | 要求 |
|---|---|
| 硬件 | AMD Radeon GPU(RX 7900 XTX / gfx1100,或 Radeon 8060S / gfx1151 为本套件实证过的两型;其他型号如实记录 gfx) |
| 驱动 | AMD 官方 Adrenalin(无需任何开发组件) |
| OS | Windows 11 |
| Python | 3.12 或 3.13(官方安装器) |
| 不要装 | Visual Studio Build Tools / C++ 工具集(Stable 验收的前提就是不需要它) |

## 1. 预检(决定官方包是否合格 — 必须先跑)

```text
python scripts/r22a5a/g9_preflight.py --plan release-provenance/r22a5a/install_plan_<你的gfx>.json --channel stable
```

- 输出 `BLOCKED_RELEASE`(退出码 3)= 官方修复轮尚未发布或尚未通过溯源审计
  → **停止,回报 BLOCKED**,不要继续安装。
- 输出 `PROCEED_CANDIDATE`(退出码 0)= 官方候选已合格 → 按 §2 安装。
- 任何其他退出码 = 预检本身异常 → 回报具体输出。

(维护者注:预检的输入 `install_plan_<gfx>.json` 由
`scripts/r22a5a/release_preflight.py --live` 重新生成;独立开发者只需使用
仓库中已提交的最新版本。)

## 2. 安装(全部官方渠道,无任何手工步骤)

仅当 §1 给出 PROCEED_CANDIDATE 时,按其打印的命令安装(形如):

```text
python -m pip install --index-url <官方渠道URL> "torch==<锁定版本>" ... 
python -m pip install ultralytics
```

版本与 `--hash` 锁定以 `release-provenance/r22a5a/` 中由
`resolve_package_set.py` 生成的锁定文件为准。**不要**自行混装更新版本。

## 3. 验收步骤(每步都记录精确版本)

| # | 步骤 | 命令 | PASS 判据 |
|---|---|---|---|
| 1 | 环境验证 | `python verify_environment.py` | 真实 AMD GPU、`torch.version.hip` 非 None;失败即退出码 2 |
| 2 | 冒烟训练 | `python train.py --smoke` | 有限损失、GPU 真实选中 |
| 3 | 代表训练 | `python train.py --representative` | 学习曲线下降,`last.pt`/`best.pt` 产生 |
| 4 | 验证 | `python validate.py` | best.pt 在 GPU 上出指标 |
| 5 | 检查点核验 | `python verify_checkpoint.py` | 权重相对预训练确有更新 |
| 6 | 真实中断 | 训练数 epoch 后 taskkill / Ctrl+C | 进程死亡,无损坏 |
| 7 | 跨进程续训 | 新终端 `python resume.py --run-id <id>` | epoch 连续、不重置、继续更新 |
| 8 | 无-STL 回归(可选但强烈建议) | 维护者协助运行 `verify_miopen_nostl.py --leg official` | 修复轮上 BatchNorm 前反向通过且梯度有限 |

## 4. 回报格式(三态,绝不二义)

每个步骤回报 `PASS` / `FAIL` / `BLOCKED` 之一,附:

- 机器:gfx 型号、驱动版本、Windows build、Python 版本
- 包身份:torch/torchvision/ultralytics 精确版本(含本地段)
- 证据:各步产生的 JSON(`verify_environment.py` 起每个脚本都会写)
- 失败时:完整终端输出 + `runs/` 目录留档,不删任何东西

回报到 issue #14(受邀测试)或新开 issue。

## 5. 判定语义(维护者与独立开发者共用)

| 结论 | 含义 |
|---|---|
| `BLOCKED_RELEASE` | 官方修复轮未发布/未合格 —— 当前状态 |
| `STABLE_CANDIDATE_PENDING_GPU_VALIDATION` | 候选合格,物理验证进行中 |
| `STABLE_USER_ACCEPTANCE_PASS` | 独立开发者在干净环境按本指南全绿(只有本态可进入 R23) |

## 6. 禁止事项(为保证证据有效)

- 不要设置 `HIPRTC_COMPILE_OPTIONS_APPEND`、`MIOPEN_*`、`VCToolsInstallDir`
  等任何环境变量(预检 `--env-scan` 会检测并记录)。
- 不要替换 DLL、不要装私有 wheel、不要用 editable ultralytics。
- 不要为了"跑通"而安装 MSVC Build Tools —— 修复轮的意义就是不需要它;
  装了它会让无-STL 缺陷被掩盖。
- 不要删除或改写任何失败记录;失败证据与成功证据同等重要。
