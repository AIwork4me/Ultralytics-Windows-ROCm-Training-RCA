# R22A.7 · @LZ-QWQ Windows gfx1201 真机执行手册

这是 RX 9070 XT 的任务书，不是 GPU 已实测报告。请先读同目录 FULL_YOLO_EVALUATION_GUIDE_zh.md，并在 Windows PowerShell 运行。所有正负尝试都保存。

## 1. 新建隔离 Python，发现 AMD 官方 Nightly wheel

使用短目录，勿覆盖现有 venv：

    py -3.12 -m venv C:\r22a7\resolver
    $PY = 'C:\r22a7\resolver\Scripts\python.exe'
    & $PY -m pip install --upgrade pip setuptools wheel
    & $PY scripts\r22a7_gfx1201\package_tools.py discover --out-dir C:\r22a7\discovery --channels nightly

从 C:\r22a7\discovery\candidate_matrix.json 确认真实 torch、torchvision、sdk、amd-torch-device-gfx1201、amd-torchvision-device-gfx1201、rocm-sdk-device-gfx1201 的版本和 ABI。检查 Py3.12 cp312 是否可用。不得依据 gfx1100/gfx1151 的 20261116 结论假定 gfx1201 同版必有。

将以下占位符换成索引中真实存在且依赖完整的一组版本：

    $TORCH_VERSION = '<REAL_OFFICIAL_NIGHTLY_TORCH_VERSION>'
    & $PY scripts\r22a7_gfx1201\package_tools.py resolve --discovery C:\r22a7\discovery\wheel_discovery.json --out C:\r22a7\lock-gfx1201-nightly.json --python $PY --channel nightly --torch-version $TORCH_VERSION --wheels-dir C:\r22a7\wheels --include-ultralytics 8.4.214 --set-name r22a7-gfx1201-nightly

注意：如果 Nightly 的 torch、torchvision、SDK/device 是不同构建快照，利用原 resolver --pin NAME==VERSION 绑定，或保存 BLOCKED_OFFICIAL_ARTIFACT；禁止绕过解析器。必须保存每个 package URL/SHA256 和真实安装日志。

    powershell -ExecutionPolicy Bypass -File .\windows-golden-path\scripts\install_official.ps1 -LockJson C:\r22a7\lock-gfx1201-nightly.json -VenvDir C:\r22a7\venv -BasePython $PY -LogDir C:\r22a7\install-logs
    $TRAINPY = 'C:\r22a7\venv\Scripts\python.exe'
    & $TRAINPY -m pip check

禁止使用通常的 pip install torch 无版本约束覆盖 AMD wheel。Ultralytics 从正式 PyPI 安装、记录原始版本。已有 venv 不可重复覆盖。

## 2. 必须证明真实物理 gfx1201，而非 CPU fallback

    & $TRAINPY scripts\r22a7_gfx1201\preflight.py --wheel-lock C:\r22a7\lock-gfx1201-nightly.json --device-index 0 --out C:\r22a7\evidence\00_preflight\gpu_identity.json

若有其他 GPU，先用 torch.cuda.get_device_properties 找到 9070 XT 真正 index，并在全部模型跑同一个 index。preflight 硬性检查 gfx1201、PyTorch HIP、真实 GPU autograd、整套已安装 package lock 版本。未通过禁止进入下一步。

使用现有 verify_gpu_child_identity.py、verify_provenance.py（先查看 --help）在实际执行算子的子进程核实 loaded MIOpen.dll SHA/build/source lineage。还需独立测试 FP16/FP32 GEMM、Conv+BN forward/back、torchvision GPU NMS。两个不同 cold-cache 的无宿主 STL BatchNorm 正对照和合法官方 pre-fix 负对照，无法建立就写 CONTROL_UNAVAILABLE，不得模拟 type_traits 错误。

## 3. 固定小数据集与输入图像

逐任务核验当前正式版本支持的 coco8.yaml、coco8-seg.yaml、cityscapes8.yaml、depth8.yaml、imagenet10、coco8-pose.yaml、dota8.yaml；以真实 dataset hash、图像数和标签格式记录。小数据仅测软件兼容，不比较真实算法质量。

    New-Item -ItemType Directory C:\r22a7\samples -Force
    Invoke-WebRequest https://ultralytics.com/images/bus.jpg -OutFile C:\r22a7\samples\bus.jpg
    Get-FileHash C:\r22a7\samples\bus.jpg -Algorithm SHA256

不要上传任何不允许公开的原始数据。

## 4. 先做 7 个 nano pilot

运行示例：

    & $TRAINPY scripts\r22a7_gfx1201\run_case.py run --model yolo26n --phase train --preflight C:\r22a7\evidence\00_preflight\gpu_identity.json --wheel-lock C:\r22a7\lock-gfx1201-nightly.json --sample-image C:\r22a7\samples\bus.jpg --out-root C:\r22a7\evidence\cases --device 0 --batch 1 --epochs 3 --workers 0 --timeout-seconds 3600

逐个改 --model：

    yolo26n
    yolo26n-seg
    yolo26n-sem
    yolo26n-depth
    yolo26n-cls
    yolo26n-pose
    yolo26n-obb

每项必须实际 GPU train 至 epochs、独立 val、保存 best.pt/last.pt 并 hash、reload、predict，保留 stdout.raw/stderr.raw、envelope.json、config.json、child_result.json。模型从官方 Ultralytics 源获取，记录原始下载 URL 和权重 SHA。Runner 如果输出 NOT_LOCALLY_IDENTIFIED，要补足权重下载来源证据。

失败后另建新 attempt，不能覆盖/删除失败；如 x/sem/depth GPU OOM，保留原参数和 OOM，再在新 attempt 用较小 imgsz/batch=1 重跑，标实际配置。禁止 CPU 或禁用 AMP 后声称原路径 PASS。

## 5. 完整主矩阵 35 行

读取 validation/gfx1201-rx9070xt/yolo26_model_matrix.json；它明确列出 35 个 ID、task、size、数据集和小规模 imgsz。每次独立 Windows Python 进程、每模型至少 train/val/save/reload/predict；串行、不要把多个 x 同时跑到 16 GB 显存里。15 个 optional 单独报告，不得充当缺失的 mandatory 项。

所有任务要求真实 3 epoch 记录，这只是兼容性 smoke，不是官方 mAP benchmark。保持固定 seed/data/hash，跨模型性能比较时强制对齐 imgsz/batch/metric 口径，否则只报告配置对应的运行情况。
