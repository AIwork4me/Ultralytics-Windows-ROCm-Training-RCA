# Gate 23 — Clean-env reproduction result

Date: 2026-10-07. Environment: curated clean `yolo_amd`
(`docs/PHASE2_CLEAN_ENVIRONMENT.md`; native stack SHA256-identical to
Phase-1 base). Invocation contract: `PYTHONNOUSERSITE=1` +
`envs\yolo_amd\python.exe`, plain shell, no VS/MSVC injection.

## Result matrix (raw logs in `evidence/phase2/raw/clean_env/`)

| Test | What | Result | Exit | Signature |
|---|---|---|---|---|
| A | GPU GEMM control | **PASS** | 0 | `A_gemm.txt` |
| B | GPU Conv2d control | **PASS** | 0 | `B_conv.txt` |
| C | minimal `BatchNorm2d(16)` (8,16,64,64) train | **FAIL** | 1 | `MIOpenBatchNormFwdTrainSpatial.cpp` → `miopen_type_traits.hpp:151 fatal error: 'type_traits' file not found` → `HIPRTC_ERROR_COMPILATION (6)` → `miopenStatusUnknownError` — identical to Phase 1 (`C_bn_minimal_train.txt`) |
| C-3956 | `BatchNorm2d(100)` (20,100,35,45) | **FAIL** | 1 | identical (`C_bn_issue3956.txt`) |
| C-yolo | `BatchNorm2d(16)` (16,16,320,320) | **FAIL** | 1 | identical (`C_bn_yololike.txt`) |
| D | `BatchNorm2d` eval (matrix case C) | **FAIL** | 1 | `MIOpenBatchNormFwdInferSpatial.cpp` variant, same chain (`D_bn_eval.txt`) |
| E | BN with `torch.backends.cudnn.enabled=False` (diagnostic) | **PASS** | 0 | native BN path, mean −0.000000 (`E_bn_cudnn_off.txt`) |
| F | Ultralytics YOLO26n GPU train (coco8, epochs=1, imgsz=640, device=0, workers=0) via Python API | **FAIL** | 1 | identical full chain incl. `RuntimeError: miopenStatusUnknownError` (`F_yolo_train.txt`) |

## Gate decision rule

> Gate passes only if: (A) failure reproduces and signature matches Phase 1,
> or (B) a compelling alternative explanation is established.

**Branch A holds.** Signature match is field-for-field (same kernel source
names, same header, same line number 151, same HIPRTC error code, same
miopenStatusUnknownError terminator, same failure point at first BN in
YOLO's forward).

## Additional provenance captured

`F_yolo_train.txt` exposes the wheel's build path inside the MIOpen error:
`C:/home/runner/_work/rockrel/rockrel/rocm-libraries/projects/miopen/src/hipoc/hipoc_program.cpp:299`
— the ROCm 7.14 Windows wheels were produced by the **rockrel** CI pipeline
from `rocm-libraries` sources. (Consumed by Gate 29 archaeology.)

## Interpretation

- **P2-H1 (dirty base environment causes the failure) is FALSIFIED**: with
  paddlex/paddle/omnidocbench/anaconda-cli/wps-era packages entirely absent,
  every previously-failing case still fails identically and every
  previously-passing control still passes.
- The defect is a property of the (byte-identical) wheel stack + machine
  toolchain state, not of base's package set.
- Clean env does NOT weaken the RCA — it reproduces it exactly.

## One-variable discipline note

Between Phase-1 baseline and this gate the changed variables are: Python
interpreter instance (base 3.13.13 → env 3.13.x, both conda CPython 3.13),
absence of unrelated packages, and `PYTHONNOUSERSITE=1`. The failing
signature is unchanged, and native binaries are SHA256-identical, so the
comparison is decisive for P2-H1 despite the env swap (that swap being the
very variable under test).
