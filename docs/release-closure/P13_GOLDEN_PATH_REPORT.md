# P13.4 — Windows Radeon Golden Path 报告

日期:2026-11-15 · 状态:**PROCEDURE_READY / 实机验证有限 / BLOCKED_INDEPENDENT_USER_TEST**

> **P14 修订(2026-11-15)**:§1 原第 26 行 `m.save("best.pt") / YOLO("best.pt")` 不是可执行的保存/重载序列(ultralytics 的 `train()` 自动落盘 best.pt/last.pt,无需手动 save;重载用 `YOLO("best.pt")`)。可执行替代与全部自动化脚本见 `golden-path/`(P14.3,已在本机 MODE B 实测全流程通过):`verify_environment.py → train.py → validate.py → verify_checkpoint.py → resume.py`;resume 用 **last.pt + resume=True**(恢复优化器/调度器状态),与重开成品模型区分。

## 1. Golden Path 程序(写给从未参与本项目的开发者)

前提(仅官方渠道,无任何手动 DLL/编译器补偿):

```text
1. 硬件:受支持 Radeon GPU(本文实证:Radeon 8060S / gfx1151)
2. 安装 AMD 官方驱动 + Windows 11
3. Python 3.13(官方安装器)
4. 按官方 ROCm-on-Windows 文档安装 PyTorch:
   pip install torch --index-url https://repo.amd.com/rocm/whl-multi-arch/   # 现行官方 index
5. pip install ultralytics
```

标准工作流(全部为 Ultralytics 公开 API,无隐藏开关):

```python
from ultralytics import YOLO
m = YOLO("yolo26n.pt")                      # C. 加载
m.info(); import torch; print(torch.cuda.get_device_name(0))   # A/B. GPU 检测
r = m.train(data="coco8.yaml", epochs=10, device=0)            # D/E. GPU 训练(AMP 自动协商)
metrics = m.val()                                              # I. 验证
m.save("best.pt") / YOLO("best.pt")                            # J/K. 保存/重载
# L/M/N/O:训练中断 → 回调抛异常保存可 resume checkpoint → resume=True 跨进程续训(P9 已实证)
```

### 本会话新增的上游级保障(P13.1)

AMP 探针任一阶段(构建/搬移/forward)的后端异常 → 记日志、AMP 降级 FP32、训练继续;Ctrl+C 不被吞(见 `P13_PR27198_CLOSURE.md`)。

## 2. 实证覆盖(哪些步骤有 raw 证据)

| 步骤 | 证据(ENV A 官方栈,gfx1151) |
|---|---|
| A/B GPU+runtime 检测 | G1(`windows-training-validation/reports/G1_*.json`) |
| D–I 训练/梯度/参数更新/AMP 有效/验证 | t16 = 24 次真实参数更新(`g2_detect_amptrack_*.json`)+ imagenette FP32-vs-AMP 对照(P9 §4.4)+ G3 AMP 语义 |
| J/K 保存/重载 | G2 7 任务生命周期(`raw/g2_*.json`) |
| L–O 中断/续训 | G2 resume 腿 + P9 harness 回调中断法(8.4.182 行为注记见 HANDOFF §2.3) |
| 30-epoch 稳定 + A/B 配对 | G4 ENV A/B(`raw/g4_long_run_ENV_*_p9.json`) |

## 3. 错误 UX 实测(已注入并归档的失败)

| 注入 | 观察行为 | 分类 |
|---|---|---|
| 探针期后端异常(ENV B 混合栈,P9 实机) | 旧代码:训练崩溃(已由 PR #27198 修复为降级+日志);新代码:False+日志 | 已修复 |
| HIPRTC no-STL(无 MSVC 官方轮) | 首训练步 kernel 编译失败,报 HIPRTC 错误 — **官方轮修复 BLOCKED_RELEASE(#15862)** | 外部阻塞 |
| 缺失 FDB 警告(3.6.2 行为) | 警告但执行正确(P13.2 E2 128/128) | 良性(已归档) |
| 训练中断(harness kill) | 可 resume checkpoint 落盘(G2/P9) | ✅ |

## 4. 未满足的验收项(如实)

- **7.1 全新机器安装**:本会话无法提供第二台干净 Windows 机器;所有实证来自本机两 env。**首次安装时长/安装期错误样本:未采集。**
- **7.5 独立操作员测试**:**BLOCKED_INDEPENDENT_USER_TEST**(无可用的未参与 RCA 的测试者;不模拟)。
- 官方轮验收(GATE 3/4):BLOCKED_RELEASE。

## 5. 门禁映射

GATE 4 前置 = GATE 3(BLOCKED_RELEASE)。本交付把"官方包可用那天"的验收成本降到最低:程序 §1 即验收脚本,验收套件 = `scripts/verify_release_closure.py` + G0–G4 runner(RELEASE_LINEAGE §4 清单)。
