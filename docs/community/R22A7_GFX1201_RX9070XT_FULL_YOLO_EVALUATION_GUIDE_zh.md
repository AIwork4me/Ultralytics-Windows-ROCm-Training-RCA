# R22A.7 — RX 9070 XT gfx1201 × AMD Official Nightly PyTorch × Ultralytics YOLO 真机评测

执行者：[@LZ-QWQ](https://github.com/LZ-QWQ)。状态：**TEST PLAN / NOT_RUN**。本指南并不宣称 AMD 已正式支持 Windows ML training，也不包含任何新 gfx1201 实测结果。

## 0. 目标、边界与严禁事项

在 Windows 11 Radeon RX 9070 XT 16GB（gfx1201）上，使用独立确认的 AMD 官方 Nightly ROCm/PyTorch/torchvision/设备轮 + PyPI 正式发布的 Ultralytics，实测 YOLO 模型的真正 GPU training / validation / best+last 保存 / 独立 reload / GPU predict / 跨进程中断恢复。证明或证伪无需特殊 Ultralytics 分支、DLL 替换、HIPRTC 头文件注入与私有 wheel 的 Golden Path。

**注意：AMD Windows 7.2.1 限制说明仍明确写有 No ML training support。** 此次是社区工程实测，不是 AMD 官方 Stable/G9 训练认证。官方矩阵列出 gfx1201 但不等于保证所有模型训练成功。

官方信息：
- https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html
- https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/limitations/limitationsrad.html
- https://nightly.repo.amd.com/rocm/pytorch/whl-next/
- https://nightly.repo.amd.com/rocm/core/whl-next/
- https://docs.ultralytics.com/models/yolo26
- https://docs.ultralytics.com/integrations/amd

禁止：GPU CPU fallback 冒充 GPU PASS；使用 gfx1100/1151 设备轮；ROCｍ 7.x/10.x 混装；复制/覆盖 MIOpen.dll；手工加 type_traits；开启 HIPRTC workaround；私自修改 Ultralytics；删除失败记录；把 GitHub CPU-only CI 当作真机 GPU 验证；把 Nightly 声称 Stable。所有修改 Windows 安全配置和长路径设置的实验必须留原始失败及变更对照，作为 WORKAROUND_REQUIRED，不计入零手工修改 Golden Path。

## 1. 模型清单：35 必测 + 15 扩展

完整机器可读清单：validation/gfx1201-rx9070xt/yolo26_model_matrix.json。

| 任务 | 官方 5 款权重（n/s/m/l/x） | 小数据集 | 个数 |
|---|---|---|---|
| Detect | yolo26{n,s,m,l,x}.pt | coco8.yaml | 5 |
| Instance segment | yolo26{n,s,m,l,x}-seg.pt | coco8-seg.yaml | 5 |
| Semantic segment | yolo26{n,s,m,l,x}-sem.pt | cityscapes8.yaml | 5 |
| Depth | yolo26{n,s,m,l,x}-depth.pt | depth8.yaml | 5 |
| Classify | yolo26{n,s,m,l,x}-cls.pt | imagenet10 | 5 |
| Pose | yolo26{n,s,m,l,x}-pose.pt | coco8-pose.yaml | 5 |
| OBB | yolo26{n,s,m,l,x}-obb.pt | dota8.yaml | 5 |

35 个 pretrained .pt 都必须逐项留状态；FAIL/OOM/NOT_RUN 不能从分母删除。15 个 optional：5 个 semantic ADE20K checkpoint（合法数据许可前置），10 个 P2/P6 YAML-only detection 架构（从零初始化；不是 pretrained .pt）。YOLOE-26、YOLO11、YOLOv8/YOLO12 等不同代需另建官方模型 inventory；不得把 35 个 YOLO26 声称全世界历史 YOLO 的所有版本。

官方小数据集只是管道 smoke，不代表 COCO/Cityscapes/ImageNet 正式精度指标。若数据集不可用或许可证不允许，记 BLOCKED_DATASET，不能伪造准确率/掩盖错误。

## 2. 代码基线、参与贡献与物理硬件

Repository: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA

父 Draft PR head: validation/r22a7-gfx1201-rx9070xt-community-yolo-matrix

base: work/windows-rocm-training-release-closure（冻结起点 78098c59ad7f89951a0fe99d4b39e2752b803932，PR #22/#23 已合并）。

@LZ-QWQ 目前对上游仓库只有 read 权限。Fork 上游→基于本 Draft PR head 建 evidence/r22a7-gfx1201-YYYYMMDD → 在自己 fork 提交所有真实证据 → 建独立 evidence PR，base 选择本 Draft PR 的 head 分支（可用 compare across forks）。Owner 审阅后将证据 PR 合并到父 Draft PR，再决定是否转 Ready。不能未经授权直接 push 上游，也不得 force-push 原始证据。

Git 命令：

    git clone https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA.git
    cd Ultralytics-Windows-ROCm-Training-RCA
    git fetch origin
    git switch --track origin/validation/r22a7-gfx1201-rx9070xt-community-yolo-matrix
    git rev-parse HEAD
    git status --short

必录：Windows 11 build、driver、CPU、RAM、物理 RX9070XT gfx1201、PyTorch 实际 device index（可能有 iGPU/虚拟设备）、GPU 内存、Python ABI、HIP、Ultralytics、SDK 与真实子进程加载 MIOpen.dll 的 SHA256/source ancestry。任何假设备、CPU fallback、未知 DLL 均 fail-closed。
