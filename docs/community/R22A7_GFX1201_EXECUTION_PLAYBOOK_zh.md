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

## 6. 真正的中断恢复：不能用训练结束后剥离的 last.pt 伪造

最低测试要求：7 个 task 各自的 nano + 至少一个大模型 x（不少于 8 个真实中断实验）。如要宣称 35/35 resume，则必须 35 个逐个做。对每个模型：

1. 新进程启动训练，确保未结束时可靠落盘 checkpoint。
2. 真正训练子进程仍运行时计算 last.pt SHA、epoch、optimizer、scaler 可用的实际序列化状态。
3. 只终止该任务已知 PID 及其拥有的子进程，保留 PID、退出码、原始 stdout/stderr。不得杀其他用户进程。
4. 新 Python 进程加载该可恢复 last.pt，使用 resume=True，检查源 checkpoint 哈希与训练起点的 epoch 连续性。
5. 证明 resume 后实际更新了模型参数且梯度有限、optimizer state 非空。
6. 重新 val、独立 reload、GPU predict，保存后续 last/best 哈希、原始日志和可解释的状态连续性。

不要把正常完成训练并被 Ultralytics strip 了 optimizer 的 last.pt 当成真中断检查点。现有 R22A.5N.2 的 verify_checkpoint_resume_v2.py 可作为设计参考，但它如果只支持 detect/n，则必须对任务适配后真机重跑，不能复制一个 detect receipt 证明 35 个。

区分 SERIALIZED 与 RESTORE_VERIFIED。Scheduler 在某些 Ultralytics 版本不作为完整对象序列化；GradScaler 键的存在也不保证已恢复，缺证据时仅报 RESUME_PASS_CORE_STATE_VERIFIED。对坏 checkpoint / 丢失 optimizer / epoch 错误必须负对照 FAIL。

## 7. AMP、真实 optimizer updates 与 workers=8 专项

单靠 train 成功或 amp=True 不能宣称 FP16 成功。run_case.py 正式标出 amp_low_precision_observed=NOT_INSTRUMENTED。每个 task 至少 n + 一个最大显存压力 x 模型需要独立审计：
- 采集真实 backbone output torch.float16/bfloat16 dtype，而不是配置布尔值。
- 记录 GradScaler 每个 step 的 scale、found_inf、inf skip 后 backoff。
- 记录 optimizer=auto 选择的实际优化器类别；默认不一定在所有任务均为 AdamW。
- 用真实参数 sentinel delta 证明 step 有效、无效 step 与 tensor 不变一致，有限梯度才算有效更新。
- 比较 workers=0 与 workers=8 的真实 Windows DataLoader 训练，不能因为命令行写了 workers=8 就认定生成了 8 个 worker；须采集同一时刻 parent-child live census、每 worker PID/PPID/spawn_main 命令行、envelope 归属、任务前 baseline 和结束后 orphan 重算。
- 运行 bounded cold/warm 多次、损坏 checkpoint、坏数据/空数据、OOM 等负向测试。出现可复现 FAIL 必须保留。

请参考整合分支里已审计的 audit_adamw_amp.py / r22a5n1/nightly_acceptance.py 的证据定义；不允许误将 detect 任务的数学或 optimizer 假设用于 pose、semantic、depth 等其他任务。

## 8. 资源、计时和隐私

RX 9070 XT 通常是 16 GB 显存，必须以真实设备属性为准。逐模型只允许独立串行运行（不与其他任务争用 GPU），收集 wall-time、每项 torch.cuda.max_memory_allocated、数据集哈希、batch/imgsz/epochs、sample 输入哈希、GPU index、driver、torch/ROCm package lock、模型预训练权重哈希。

PyTorch max_memory_allocated 仅反映 allocator peak，不等于系统全局 GPU VRAM 峰值；外部显存占用需另配可验证采集器，否则标 NOT_MEASURED。低 imgsz 训练准确率不能与官方高分辨率大数据集的结果比较。CI 只能重算原始证据，不能代替真机性能数据。

禁止上传 token/SSH key/机器私人路径/个人文件/有许可证限制的 Cityscapes、ImageNet 原图。日志如需脱敏，保存原始文件到有权限的持久存储，提交明确的派生转换说明；不能在公开 GitHub 伪造经过处理的日志为原始字节。

## 9. 独立验收器、SHA256 manifest 和证据格式

本 repo scripts/r22a7_gfx1201/verify_submission.py 是 CPU-only 结构性验收器，检查每个 attempt 的 config/envelope/child_result + stdout.raw/stderr.raw 的真实性、hash 绑定、gfx1201 runtime、train/val/reload/predict/epoch/checkpoint 收据；它不能证明完整 AMP 与 optimizer 数值审计。

    & $PY scripts\r22a7_gfx1201\verify_submission.py --evidence-root C:\r22a7\evidence\cases --out C:\r22a7\evidence\matrix_gap_audit.json --report-only

--report-only 即使 exit=0 也只是 GAP 报告，不是模型 PASS。全部 35 个主模型 train/val/save/reload/predict 真实记录齐全、无未解释的证据违例，非 report-only 模式才可能 exit 0。恢复、AMP、worker 专项门禁需要独立结论。

建议将全部**允许公开**的证据放入：

    reports/r22a7-gfx1201/<REAL_RUN_ID>/
      00_preflight/ GPU + Windows + driver + true DLL identity
      01_packages/ wheel discovery + full lock + installed manifest + pip check
      02_g1/ 2 cold positive + real negative or CONTROL_UNAVAILABLE
      03_ops/ GEMM FP32/FP16, Conv/BN, GPU NMS
      cases/<MODEL_ID>/<ATTEMPT>/
          config.json, envelope.json, child_result.json, stdout.raw, stderr.raw
          training results, raw metrics, model and checkpoint hashes
      04_resume/ actual interruption and continuation
      05_amp/ real dtype, scaler history, per-step optimizer deltas
      06_workers/ actual PID/PPID/ancestry live census + orphan
      07_audit/ submission audit, negative controls, exceptions
      SHA256MANIFEST.json
      FINAL_REPORT_zh.md

运行前沿任务使用的 SHA256 工具：

    & $PY scripts\r22a5n1\evidence_pack.py gen --root C:\r22a7\evidence --run-id R22A7-GFX1201-<REAL_DATE>
    & $PY scripts\r22a5n1\evidence_pack.py verify --root C:\r22a7\evidence --run-id R22A7-GFX1201-<REAL_DATE>

<REAL_DATE> 必须替换成真实日期。若大 checkpoint 数十 GB 不适合 Git，记录 filename、size、SHA256、模型、真实可下载持久 artifact URL、retention、审阅权限；GitHub 内不能只有一个无法访问的本机 C:\ 路径。保留所有 FAIL、OOM、超时、第一次重试、环境变更，绝不可只提交最后成功的 JSON。

## 10. 什么时候可以声称 PASS

- BLOCKED_OFFICIAL_ARTIFACT：官方 Nightly 组件缺失、不匹配或不可信，不能改用第三方 wheel。
- BLOCKED_GPU_IDENTITY：真正的 RX9070XT/gfx1201 无法建立，不能用任何 CPU/假设备数据取得 GPU PASS。
- NIGHTLY_GFX1201_PRIMITIVES_PASS：冷缓存 No-STL、真实 GPU operators 与二进制来源独立审计，若负对照缺失则 G1 的因果声明必须受限。
- NIGHTLY_GFX1201_YOLO26_35_TRAIN_MATRIX_PASS：35 个 mandatory 各自真实 GPU train、val、checkpoint 存档、reload、predict 皆 PASS，没有删掉 FAIL/NOT_RUN。
- NIGHTLY_GFX1201_YOLO26_35_RESUME_COVERAGE_PASS：全部 35 个独立跨进程中断续训；只有 7 nano + 1 x 不得称 35/35。
- NIGHTLY_GFX1201_AMP_AUDITED_PASS：至少为明确定义的任务/模型子集采集真实低精度 + 参数更新 + scaler；不可外推没有测试的 35 项。
- NIGHTLY_GFX1201_EVIDENCE_AUDITED_PASS：其**实际宣称的子集**可独立重复哈希和数值审计；不是 Stable、G9 或全业务生产认证。
- OFFICIAL_STABLE_PASS / CLEAN_WINDOWS_G9：本 Nightly 任务无权使用。

35 个 tiny-dataset 训练成功不代表高质量业务图片、不代表官方排行榜，也不代表 35 个模型长期稳定。证据不足必须 INCONCLUSIVE。

## 11. 交接给 AIwork4me 的 GitHub evidence PR

@LZ-QWQ 在自己的 fork 中提交 evidence/r22a7-gfx1201-YYYYMMDD 分支，使用 GitHub compare across forks，base 选择上游 validation/r22a7-gfx1201-rx9070xt-community-yolo-matrix。请不要直接向 main 合并。若 GitHub UI 不支持该 base，先提交 evidence PR 指向 integration 并明确说明，维护者决定安全整合方式。

PR 描述应有实际 GPU/Windows/driver、Nightly exact torch/torchvision/SDK/Ultralytics version + lock SHA、35 项各 task/size 状态、所有失败重试日志、G1/G2、AMP dtype+steps、checkpoint restore、workers、manifest 验证、CI 和未完成项。

最终中文报告：A executive verdict; B exact Git/CI; C hardware and official package provenance; D source/DLL ancestry; E No-STL positive/negative; F GPU primitives; G 35 模型表；H optional matrix；I AMP/optimizer；J checkpoint/resume；K workers/orphans；L OOM/负向失败；M 时长/显存口径；N SHA/fresh clone；O 下一步与范围边界。

Maintainer 在真实物理证据到达且独立审阅前让本父 PR 保持 Draft。**真实失败证据比没有来源的全绿表格更有价值。**
