# Golden Path — Windows 安装指南(MODE B:官方渠道,首次用户)

写作原则:每条命令都在验收机(AMD Radeon 8060S / gfx1151,Windows 11 26200)上实测执行过;官方来源;不含任何开发期补偿手段(无手动 DLL、无私有 wheel、无 editable fork)。

## 1. 前置

| 项 | 要求 | 实测基准 |
|---|---|---|
| 硬件 | 受支持 Radeon GPU | AMD Radeon 8060S(gfx1151,iGPU) |
| 驱动 | AMD 官方 Adrenalin(支持 ROCm 的版本) | 本机现有驱动(与 ROCm 7.14 wheel 兼容) |
| OS | Windows 11 | 26200 |
| Python | 3.10–3.13(官方安装器或 conda) | 3.13 |

## 2. 安装(全部官方渠道)

```text
pip install torch --index-url https://repo.amd.com/rocm/whl-multi-arch/
pip install ultralytics
```

官方轮版本参考(2026-11-15 实测组合,见 `requirements-lock.txt`):torch 2.12.0+rocm7.14.1 / torchvision 0.27.0+rocm7.14.1 / ultralytics 8.4.182。

安装时长参考(验收机):官方 torch wheel ~2.3 GB,视网络数分钟;首次训练前 MIOpen 会编译 kernel 缓存(首步较慢,属正常)。

## 3. 环境验证

```text
python verify_environment.py
```

PASS 判据(脚本逐条检查并写 JSON):检测到真实 AMD GPU(非 CPU-only);`torch.version.hip` 非 None;官方包版本记录;**任何一条不满足即退出码 2 并给出修复指引** —— 绝不静默回退 CPU。

## 4. 训练 / 验证 / 保存 / 重载 / 续训

见 `README.md` 快速开始。要点:

- `train.py` 显式 `device=0`,绝不依赖静默设备选择
- **best.pt** = 训练产生的最佳验证权重;**last.pt** = 续训用的恢复点;`resume=True` 恢复的是优化器/调度器状态,不是重开模型
- 真实中断流程:训练 ≥1 个 epoch 后杀死进程(taskkill /PID <pid> /F 或 Ctrl+C),**新开一个终端/进程**跑 `resume.py` —— 跨进程续训才算数

## 5. 已知问题与排错

| 现象 | 原因 | 处置 |
|---|---|---|
| 首训练步报 `HIPRTC_ERROR_COMPILATION ... fatal error: 'type_traits' file not found`,随后 `miopenStatusUnknownError` | 官方 MIOpen wheel 尚未包含 #13437 修复(BLOCKED_RELEASE,#15862),且机器无 MSVC Build Tools | 官方修复轮发布前:安装 MSVC Build Tools(含 C++ 工具集)即可让 HIPRTC 找到宿主 STL,训练可正常进行;或在无 Build Tools 的机器上等待官方修复轮 |
| `torch.cuda.is_available()` False | 装了 CPU-only torch 或驱动过旧 | 重装官方 ROCm wheel(§2);更新 AMD 驱动 |
| AMP 日志出现 `checks failed ... AMP will be disabled` | AMP 探针未通过(可能是数值异常或后端异常) | 训练会以 FP32 继续;若 FP32 也报同样错误,问题在后端/驱动而非 AMP |
| 训练中断后 resume 报 epoch 不对 | 用错检查点 | resume 必须用 `last.pt`(不是 best.pt);确认是同一 run 目录 |
| GPU 显存不足 | 批量过大 | 减小 `batch` 或 `imgsz` |

## 6. 验收记录

一次完整验收(1–4 + 中断续训)应把 `acceptance_manifest.json` 按实际结果填写并留存;逐字段含义见 `acceptance_report.schema.json`。
