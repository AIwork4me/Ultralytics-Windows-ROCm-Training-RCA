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

- **P2-H1 (dirty base environment causes the failure) is FALSIFIED for the
  package-set reading**: with paddlex/paddle/omnidocbench/anaconda-cli
  packages absent, the re-run subset of previously-failing cases (C, C-3956,
  C-yolo, D, F) still fails identically and the re-run controls (A, B, E)
  still pass. Not re-run here: matrix G, H, B(CPU), amp-off variant, and the
  bn_variants sweep (Phase-1 falsifications unaffected by package set).
- The defect is a property of the (byte-identical) wheel stack + machine
  toolchain state, not of base's Python package set. Machine-level causes
  (MSVC STL absence, driver, wheel bytes) are NOT excluded by this gate —
  they are exactly what Gates 24–28 test.
- Clean env does NOT weaken the RCA — it reproduces it exactly (audit:
  normalized 0-line diff on the three BN repros; 12/12 canonical signature
  fields on F; 10/10 DLL SHA256 identity).

## Caveats (per Gate-23 independent audit, `subagent_gate_23_review.md`)

1. **Interpreter delta is real**: base runs CPython 3.13.13 (Anaconda),
  yolo_amd runs conda-forge CPython 3.13.16 plus its own vc14_runtime
  14.44 CRT DLLs. The failure signature is unchanged and the failing path
  is native code identical by SHA256, so this delta does not affect the
  conclusion, but it is a changed variable and is recorded here.
2. **B_conv is a cache-warm pass** (0.03 s vs Phase-1's 16.76 s cold
  first-call compile): the MIOpen user kernel DB (~/.miopen/cache — shared,
  env-independent machine state) already contains the conv code objects.
  That same DB contains **zero BatchNorm entries**, so the shared cache can
  only have biased this gate AGAINST reproducing the BN failure — it cannot
  explain the reproduction.
3. The A–E logs as first committed lacked embedded capture headers; the
  committed runner `scripts/phase2/21_clean_repro.ps1` now regenerates all
  Gate-23 artifacts with headers, commands, env flags, and exit codes, and
  its output supersedes the bare logs (signatures unchanged).
4. `gate22_env_verify.txt` pip-check row correction: the in-clone pip check
  complaints are `soundfile requires cffi` (plus the two pre-existing
  matplotlib gaps noted in PHASE2_CLEAN_ENVIRONMENT.md), and that verify run
  itself was made WITHOUT `PYTHONNOUSERSITE=1` (hence `onnxruntime
  present`); all experiment runs use the flag per the invocation contract.

## One-variable discipline note

Between Phase-1 baseline and this gate the changed variables are: Python
interpreter instance/build (base 3.13.13 → env 3.13.16, both conda CPython
3.13), absence of unrelated packages, user-site removal
(`PYTHONNOUSERSITE=1`), and warm MIOpen conv cache. The failing signature
is unchanged, and native binaries are SHA256-identical, so the comparison
is decisive for P2-H1 (the package-set variable) despite the env swap
(that swap being the very variable under test).
