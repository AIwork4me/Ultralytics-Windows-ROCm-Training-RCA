# P14.3 — 可执行 Golden Path 执行报告(MODE B 实测)

日期:2026-11-15 · 环境:Radeon 8060S (gfx1151) / Windows 11 26200 / **ENV A `pm13437_official`**(官方 torch 2.12.0+rocm7.14.1 + **已发布 ultralytics 8.4.182 PyPI wheel**,非 editable、非手动 DLL)· 运行目录 `C:\Users\rocm\Desktop\YOLO_AMD\golden_path_p14`

## 1. 套件交付(全部可执行,`golden-path/`)

README.md / WINDOWS_SETUP.md / requirements-lock.txt / verify_environment.py / train.py / validate.py / resume.py / verify_checkpoint.py / acceptance_manifest.json / acceptance_report.schema.json —— 替代并修复 P13 报告中不可执行的 `m.save("best.pt") / YOLO("best.pt")` 表达式(该行已由 P14 修订注记更正)。所有脚本:显式 `device=0`、`if __name__ == "__main__"`、拒绝 CPU-only、无隐藏开关。

## 2. 实测结果(逐腿)

| 步骤 | 命令 | 结果 | 关键证据 |
|---|---|---|---|
| 3 环境验证 | `verify_environment.py` | **PASS** | 真实 GPU + ROCm wheel + HIP 7.14.60850 + 真实 GPU 矩阵乘;MIOpen 身份如实记录 `3.5.2.cd957402`(并 WARN 无 #13437 修复);`environment_identity.json` |
| 4a 冒烟 | `train.py --smoke`(COCO8,2ep) | **PASS** | `AMP: checks passed`(真 AMP,非降级);2 epochs 完成 |
| 4b 代表性训练 | `train.py --representative`(COCO128,20ep,seed=0) | **PASS** | **mAP50-95 0.4919 → 0.5603(真实学习曲线)**;results.csv SHA256 `cd0ca530…` |
| 5 验证 | `validate.py` | **PASS** | best.pt val:mAP50-95 0.5591 / mAP50 0.7393;`golden_val_metrics.json` |
| 5b 检查点核验 | `verify_checkpoint.py` | **PASS** | 权重相对预训练确有更新(sum_sq 相对差 −0.001226 ≠ 0);best.pt 可重载;best.pt sha256 `029f8b04…` |
| 6 真实中断+跨进程续训 | `train.py --run-id resumetest` → **Stop-Process -Force PID 44076**(epoch 14 完成后,last.pt 已落盘)→ 新进程 `resume.py` | **PASS** | `Resuming … from epoch 15 to 20`;**调度器状态恢复(lr0=0.000119,原始 0.01)**;续完 6 epochs;results.csv 共 20 行(SHA256 `e44a5d7d…`) |

全部原始证据(含 results.csv、JSON、日志、checkpoint 文件)归档于 `release-provenance/raw/p14_golden_path/`,SHA256 清单见各 JSON。

## 3. 错误体验注入(安全方式,未破坏工作安装)

| 注入 | 行为 | 判定 |
|---|---|---|
| GPU 不可用(`CUDA_VISIBLE_DEVICES=""`) | `[FAIL] … refusing CPU-only training` 类明确输出 + **exit 2**(实测复验),不静默回退 | **PASS** |
| 缺失数据集 | `RuntimeError: Dataset '…' error … does not exist` | **PASS**(可操作) |
| 坏检查点路径 | `FileNotFoundError: … 'definitely_not_here.pt'` | **PASS**(原始但指向明确) |
| 错误 PyTorch wheel / 缺 ROCm 组件 | NOT_RUN(需破坏工作安装;verify_environment 的 +rocm/HIP 检查为替代防线) | NOT_RUN |
| 显存不足 | NOT_RUN(78GB 共享 iGPU 无法安全逼出) | NOT_RUN |
| invalid kernel file | NOT_RUN(P13.2 起不可复现,见 P13_INVALID_KERNEL_FILE_RCA.md) | NOT_RUN |
| AMP 不兼容 | 由 PR #27198 故障注入套件 + 实机故障注入覆盖(P14.2) | COVERED |

## 4. 状态

- MODE B 全流程(安装→验证→训练→验证→保存→重载→**真实中断→续训**→错误处理)在本机官方栈实测 **PASS**
- AMP 真实性:两次训练 `AMP: checks passed` = AMP 启用执行(非 AMP_DISABLED 冒充)
- **GATE 4 仍 NOT MET**:本验收是 RCA 团队本人执行;独立开发者验收 `BLOCKED_INDEPENDENT_USER_TEST`(issue #14 无回应)
- GATE 3 仍 BLOCKED_RELEASE:官方轮 MIOpen 仍无 #13437 修复(无 Build Tools 的机器不可复现本报告 §2 第 4b 步;本机装有 Build Tools,已在 WINDOWS_SETUP.md §5 如实注明)
