# Golden Path — Windows Radeon YOLO 训练验收套件

日期:2026-11-15(P14.3)· 状态:**EXECUTABLE / 本机 gfx1151 实测通过(官方栈 MODE B)/ GATE 3-4 仍 BLOCKED_RELEASE**

## 这是什么

面向"从未参与本 RCA 的 Windows Radeon 开发者"的可执行验收套件:官方渠道安装 → GPU 验证 → 训练(真实学习证据)→ 验证 → 保存/重载 → 真实中断/跨进程续训 → 结果复现。全部脚本只用 Ultralytics 公开 API + 官方发布包,**无隐藏开关、无手动 DLL、无私有构建**。

## 两种模式(不可混用)

| 模式 | 用途 | 环境 |
|---|---|---|
| **MODE B — 首次用户验收**(本套件的验收对象) | 官方驱动 + 官方 ROCm/PyTorch wheel + **已发布 ultralytics 包** | 本机实证:`pm13437_official`(torch 2.12.0+rocm7.14.1,ultralytics 8.4.182 PyPI wheel) |
| MODE A — 上游开发 | 开发/测试 PR #27198 等上游改动 | editable checkout + dev 依赖,**不是**验收 |

## 快速开始(MODE B)

```text
# 0. 前置:AMD 官方驱动 + Windows 11 + Python 3.13(见 WINDOWS_SETUP.md)
# 1. 官方 PyTorch(现行官方 index)
pip install torch --index-url https://repo.amd.com/rocm/whl-multi-arch/
# 2. 官方 Ultralytics
pip install ultralytics
# 3. 环境验证(拒绝 CPU-only 安装;输出运行时身份 JSON)
python verify_environment.py
# 4. 冒烟训练(COCO8,2 epochs,约 2 分钟)
python train.py --smoke
# 5. 代表性训练(COCO128,20 epochs,真实学习曲线,约 3 分钟)
python train.py --representative
# 6. 验证 + 检查点核验(权重相对预训练确有更新)
python validate.py
python verify_checkpoint.py
# 7. 真实中断 + 跨进程续训(见 WINDOWS_SETUP.md §resume)
python train.py --representative --run-id resumetest   # 窗口 1,数 epoch 后 Ctrl+C 或 taskkill
python resume.py --run-id resumetest                    # 窗口 2,新进程 resume=True 续训
```

## 文件清单

| 文件 | 作用 |
|---|---|
| `WINDOWS_SETUP.md` | 官方安装、驱动、已知阻塞与排错 |
| `requirements-lock.txt` | 本机实证通过的官方包版本组合(锁定参考) |
| `verify_environment.py` | GPU/HIP/包版本验证,记录运行时身份,拒绝 CPU-only |
| `train.py` | 训练入口(device=0 显式;记录 AMP 真实状态与学习曲线) |
| `validate.py` | 加载 best.pt 跑 val |
| `resume.py` | 新进程从 last.pt resume=True 续训 |
| `verify_checkpoint.py` | 检查点哈希 + 相对预训练的权重增量核验(证明真实参数更新) |
| `acceptance_manifest.json` | 一次验收运行的证据清单(run-id、包/DLL/驱动身份、结果) |
| `acceptance_report.schema.json` | manifest 的 JSON Schema |

## 已知阻塞(如实,2026-11-15)

- **BLOCKED_RELEASE**:目前**没有任何官方 Windows wheel**(whl-multi-arch 与 whl-next 双通道)的 MIOpen.dll 包含 #13437 修复。未装 MSVC Build Tools 的机器在首次训练时会遇到 HIPRTC `'type_traits' file not found`(见 WINDOWS_SETUP.md §已知问题)。装了 Build Tools 的机器(如本验收机)不受影响。
- GATE 3(官方分发)/ GATE 4(独立开发者成功)保持 NOT MET,直到官方修复轮发布并通过本套件验收。
