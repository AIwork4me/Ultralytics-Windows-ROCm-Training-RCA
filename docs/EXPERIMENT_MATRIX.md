# Experiment Matrix (Phases 1–9)

All runs 2026-10-07 (UTC+8), same shell, same interpreter
(`C:\Users\rocm\miniconda3\python.exe`, stack per `docs/ENVIRONMENT.md`).
Raw logs under `evidence/raw/` (paths in table). Machine state was not
modified between runs (no installs, no global env changes; the only
intentional child-process toggles are marked in the Env column and were
scoped to that child process only).

| ID | Experiment | Device | Mode / env | Result | Exception / signature | Exit | Raw evidence |
|---|---|---|---|---|---|---|---|
| P1 | 4096² fp32 GEMM `x@x` | cuda:0 | default | **PASS** | mean=0.015937, isfinite, result on cuda:0 | 0 | `gpu-control/gemm.txt` |
| P2 | `yolo predict yolo26n.pt bus.jpg device=0` | cuda:0 | default | **PASS** | 4 persons + 1 bus, 11.1 ms inference | 0 | `ultralytics/predict.txt` |
| P3 | `yolo detect train coco8 epochs=1 imgsz=640 device=0 workers=0` | cuda:0 | default | **FAIL** | `MIOpenBatchNormFwdTrainSpatial.cpp` → `HIPRTC_ERROR_COMPILATION (6)` → `'type_traits' file not found` → `miopenStatusUnknownError` | 1 | `ultralytics/train_gpu.txt` |
| P3b | Same with `amp=False` | cuda:0 | amp off | **FAIL** | identical signature to P3 | 1 | `ultralytics/train_gpu_amp_off.txt` |
| P3c | Same with `device=cpu` | cpu | default | **PASS** | 1 epoch + validation completed | 0 | `ultralytics/train_cpu.txt` |
| P4 | Pure `nn.BatchNorm2d(16)`, (8,16,64,64), `.train()` | cuda:0 | default | **FAIL** | identical signature to P3 (no Ultralytics involved) | 1 | `batchnorm/minimal.txt` |
| P4b | `nn.BatchNorm2d(100)`, (20,100,35,45) [#3956 shape] | cuda:0 | default | **FAIL** | identical signature | 1 | `batchnorm/minimal_issue3956.txt` |
| P4c | `nn.BatchNorm2d(16)`, (16,16,320,320) [YOLO-like] | cuda:0 | default | **FAIL** | identical signature | 1 | `batchnorm/minimal_yololike.txt` |
| A | GEMM control (isolated subprocess) | cuda:0 | default | **PASS** | — | 0 | `batchnorm/matrix.txt` |
| B | `BatchNorm2d` | cpu | `.train()` | **PASS** | mean=-0.000000 | 0 | `batchnorm/matrix.txt` |
| C | `BatchNorm2d` | cuda:0 | `.eval()` + no_grad | **FAIL** | `MIOpenBatchNormFwdInferSpatial.cpp` → same HIPRTC/type_traits chain → `miopenStatusUnknownError` | 1 | `batchnorm/matrix.txt`, `batchnorm/matrix_results.json` |
| D | `BatchNorm2d` | cuda:0 | `.train()` | **FAIL** | `MIOpenBatchNormFwdTrainSpatial.cpp` → same chain | 1 | `batchnorm/matrix.txt` |
| E | `BatchNorm2d` | cuda:0 | `.train()`, `torch.backends.cudnn.enabled=False` (child-proc diagnostic toggle) | **PASS** | native non-MIOpen BN path used | 0 | `batchnorm/matrix.txt` |
| F | `Conv2d` only | cuda:0 | `.train()` | **PASS** | MIOpen conv path OK (first-call compile 16.8 s) | 0 | `batchnorm/matrix.txt` |
| G | `Conv2d + BatchNorm2d` | cuda:0 | `.train()` | **FAIL** | fails at BN, `MIOpenBatchNormFwdTrainSpatial.cpp` | 1 | `batchnorm/matrix.txt` |
| H | `Linear` + `sum()` + `backward()` | cuda:0 | `.train()` | **PASS** | grad_norm=8347.24 (autograd healthy) | 0 | `batchnorm/matrix.txt` |
| P8 | Minimal BN with `MIOPEN_ENABLE_LOGGING=1`, `MIOPEN_ENABLE_LOGGING_CMD=1`, TEMP redirected (child process) | cuda:0 | logging | **FAIL** | API trace: `miopenBatchNormForwardTrainingActivation_V2`, bn_mode=1 (spatial), NCHW; MIOpenDriver-equivalent command logged; same compile failure; comgr temp dir auto-removed after failure | 1 | `miopen/minimal_bn_miopen_logging.txt`, `miopen/temp_tree_inventory.txt` |
| P9 | Host toolchain probe | — | read-only | see below | no `cl`/`clang`/`gcc`/`vswhere`/`dumpbin` on PATH; no Visual Studio dirs; **no `type_traits` found anywhere searched** (MSVC roots, LLVM, conda, wheel tree); `INCLUDE`/`LIB`/`CPATH` unset | — | `toolchain/toolchain_probe.txt` |
| P9b | Wheel STL sweep + clang triple (post-review supplement) | — | read-only | **0** hits for `type_traits`/`cstddef`/`utility`/`cstdint` in both wheel trees; clang resource dir ships only HIP/CUDA builtin headers; triple `x86_64-pc-windows-msvc` | see left | — | `toolchain/wheel_stl_sweep.txt` |
| P10b | MIOpen.dll embedded sources (post-review supplement) | — | read-only grep | all 4 BN kernel `.cpp` names + `#include <type_traits>`×2, `<utility>`×3, `<limits>`×2, `<cstdint>`, `<initializer_list>` embedded in DLL | see left | — | `miopen/miopen_dll_embedded_sources.txt` |
| P10c | No-STL shim gate in embedded `miopen_type_traits.hpp` (post-review) | — | read-only grep | `#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` ×2 → shim off for HIP ≥ 7.0 (ours 7.14) → real `<type_traits>` required | see left | — | `miopen/miopen_dll_shim_gate.txt` |
| P10d | MIOpen user kernel DB lineage (post-review) | — | read-only listing | 3.5.1 cache: `MIOpenBatchNormFwdInferSpatial.cl.obj` (OpenCL path, compiled OK, Jul 2025); 3.5.2 cache: only conv `.cpp.obj` — BN never cached (compile fails) | see left | — | `miopen/user_kernel_db_listing.txt` |
| V1 | `BatchNorm1d`, 2D input (8,16) | cuda:0 | `.train()` | **PASS** | no MIOpen spatial BN kernel | 0 | `batchnorm/bn_variants.txt` |
| V2 | `BatchNorm1d`, 3D input (8,16,64) | cuda:0 | `.train()` | **FAIL** | `MIOpenBatchNormFwdTrainSpatial` + type_traits chain | 1 | `batchnorm/bn_variants.txt` |
| V3 | `BatchNorm2d` (dup of D) | cuda:0 | `.train()` | **FAIL** | identical | 1 | `batchnorm/bn_variants.txt` |
| V4 | `BatchNorm3d` (2,16,8,16,16) | cuda:0 | `.train()` | **FAIL** | `MIOpenBatchNormFwdTrainSpatial` + type_traits chain | 1 | `batchnorm/bn_variants.txt` |
| V5 | `GroupNorm(4,16)` | cuda:0 | `.train()` | **PASS** | no running stats / no MIOpen BN | 0 | `batchnorm/bn_variants.txt` |

Notes:

- Case E is **diagnostic only**: it shows the failure disappears when the
  MIOpen/cuDNN-compat backend is bypassed for BatchNorm, localizing the
  defect to that backend's runtime-compiled BN path. It is NOT proposed as a
  fix or workaround in Phase 1.
- Case C failing (eval kernel) is consistent with Ultralytics inference
  working: Ultralytics fuses BN into conv weights ("YOLO26n summary
  (fused)" in `predict.txt`), so its predict path never executes an MIOpen
  BatchNorm kernel.
- MIOpen.dll embeds the HIPRTC kernel sources (grep hits inside
  `MIOpen.dll` for `MIOpenBatchNormFwdTrainSpatial.cpp`,
  `#include <type_traits>`, `#include <utility>`, `#include <limits>`);
  the wheel's clang is `x86_64-pc-windows-msvc` target and ships no C++
  standard library — see `docs/RCA.md` evidence chain.
