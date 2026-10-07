# Root Cause Analysis — Ultralytics YOLO26 training failure on Windows ROCm (gfx1151)

Phase 1 RCA. Date: 2026-10-07. All claims trace to raw evidence — see
`docs/CLAIMS_AND_EVIDENCE.md` (C0xx IDs referenced below).

## Executive Summary

- **What works:** the full ROCm PyTorch stack sees and uses the Radeon
  8060S (gfx1151): GEMM (C005), Ultralytics YOLO26 GPU inference (C006),
  GPU convolutions and autograd (C013), CPU training end-to-end (C008).
- **What fails:** any BatchNorm that maps to MIOpen's *spatial* BN kernels
  on the GPU — `nn.BatchNorm2d`, `nn.BatchNorm3d`, and `nn.BatchNorm1d`
  with 3D input — in **both** training and unfused-eval modes
  (C007/C009/C011/C031) — with `RuntimeError: miopenStatusUnknownError`.
  (`nn.BatchNorm1d` with 2D input and `nn.GroupNorm` pass — different
  kernel paths.)
- **Where the failure occurs:** inside MIOpen's runtime kernel compilation:
  MIOpen extracts an embedded BatchNorm kernel source (`MIOpenBatchNormFwd
  {Train,Infer}Spatial.cpp`) to a comgr temp dir and compiles it with
  HIPRTC; `hiprtcCompileProgram` fails with `HIPRTC_ERROR_COMPILATION (6)`
  because `miopen_type_traits.hpp:151`'s `#include <type_traits>` cannot be
  resolved — no C++ standard library is discoverable by the wheel's
  `x86_64-pc-windows-msvc`-target clang toolchain on this machine (C016–C020).
- **Root-cause depth reached: LEVEL 2** (mechanism isolated). LEVEL 3
  (which layer owns the fix: undeclared MSVC prerequisite vs wheel
  packaging/include-path defect vs MIOpen source change) is **not proven**
  and is explicitly left open.
- **Confidence:** LEVEL 0/1/2 conclusions: High. LEVEL 3: open.
- **Not yet proven:** whether installing Visual Studio / an MSVC STL would
  make HIPRTC resolve `<type_traits>` (no MSVC exists locally to test with,
  and Phase 1 forbids installing one); whether AMD considers MSVC a
  prerequisite of the Windows wheels.

## System Under Test

See `docs/ENVIRONMENT.md`. Windows 11 (10.0.26200), Ryzen AI MAX+ 395,
Radeon 8060S (gfx1151, 20 CUs), ROCm 7.14.0 wheels (pip, site-packages),
PyTorch 2.12.0+rocm7.14.0, torchvision 0.27.0+rocm7.14.0, MIOpen 3.5.2,
HIP 7.14.60850, Python 3.13.13, Ultralytics 8.4.174. Stack lives in conda
base (the `yolo_amd` env is an empty shell — documented inconsistency,
C004).

## Working Baselines

1. GPU GEMM control — PASS (`evidence/raw/gpu-control/gemm.txt`)
2. Ultralytics YOLO26n inference on GPU — PASS, 4 persons + 1 bus
   (`evidence/raw/ultralytics/predict.txt`)

## Failure

`yolo detect train data=coco8.yaml model=yolo26n.pt epochs=1 imgsz=640
device=0 workers=0` fails during the first forward pass at the first
BatchNorm module (`ultralytics/nn/modules/conv.py:87 → batchnorm.py:210 →
torch.batch_norm`), terminating in `RuntimeError: miopenStatusUnknownError`.
Full signature: `evidence/normalized/training_failure_signature.txt`.

## Minimal Reproduction (pure PyTorch, no Ultralytics)

```python
import torch, torch.nn as nn
bn = nn.BatchNorm2d(16).cuda().train()
x = torch.randn(8, 16, 64, 64, device="cuda")
y = bn(x)   # RuntimeError: miopenStatusUnknownError
```

Run: `python scripts/02_batchnorm_minimal.py minimal`
Log: `evidence/raw/batchnorm/minimal.txt` (identical signature to the
Ultralytics failure; also reproduced at shapes (20,100,35,45) and
(16,16,320,320)).

## Experiment Matrix

`docs/EXPERIMENT_MATRIX.md` — 8-case A/B matrix plus Ultralytics variants
and a normalization-op variant sweep. Decisive rows: pure-BN FAIL (D),
eval-BN FAIL (C), cudnn-disabled BN PASS (E, diagnostic only), Conv-only
PASS (F), CPU BN PASS (B), amp=False FAIL (P3b), CPU train PASS (P3c),
BN1d(3D)/BN2d/BN3d FAIL vs BN1d(2D)/GroupNorm PASS (V1–V5).

## Evidence Chain (each arrow locally evidenced)

Ultralytics training first batch (train_gpu.txt:62–132)
→ Conv module forward, first `self.bn(...)` (conv.py:87)
→ `torch.nn.functional.batch_norm` → `torch.batch_norm` with
   `torch.backends.cudnn.enabled=True` (functional.py:2850)
→ MIOpen `miopenBatchNormForwardTrainingActivation_V2`, bn_mode=1 spatial,
   NCHW (minimal_bn_miopen_logging.txt)
→ MIOpen extracts embedded kernel source `MIOpenBatchNormFwdTrainSpatial.cpp`
   to `%TEMP%\comgr-*\{input,include}` (train_gpu.txt:50–56; strings
   physically present inside MIOpen.dll — C018)
→ include chain `.cpp:8 → batchnorm_functions.hpp:30 → configuration.hpp:34
   → vector_types.hpp:8 → miopen_type_traits.hpp:151`
→ `#include <type_traits>` — **fatal error: 'type_traits' file not found**
   (every failure log)
→ `1 error generated when compiling for gfx1151`
→ `hiprtcCompileProgram` = `HIPRTC_ERROR_COMPILATION (6)`
→ MIOpen `hipoc_program.cpp:299: Code object build failed`
→ `RuntimeError: miopenStatusUnknownError`

Supporting physical facts:

- Failing-path DLLs loaded live from the wheels: `MIOpen.dll`,
  `hiprtc0714.dll`, `amd_comgr.dll`, `amdhip64_7.dll` (C021, SHA256s
  recorded).
- MIOpen.dll embeds **all four** BatchNorm kernel sources
  (`MIOpenBatchNormFwd{Train,Infer}{Spatial,PerAct}.cpp`) plus the
  `#include <type_traits>` / `<utility>` / `<limits>` directives —
  `evidence/raw/miopen/miopen_dll_embedded_sources.txt` (C018).
- The wheels ship no C++ standard library: zero hits for `type_traits`,
  `cstddef`, `utility`, `cstdint` across both wheel trees; the bundled
  clang's resource dir contains only HIP/CUDA builtin headers; its target
  triple is `x86_64-pc-windows-msvc` (an MSVC-STL-consuming
  configuration) — `evidence/raw/toolchain/wheel_stl_sweep.txt` (C019).
- No host C++ toolchain exists on the machine (C020) and `INCLUDE`/`CPATH`
  are unset, so nothing outside the wheels could supply the header either.
- MIOpen's own logging confirms the exact API and a standalone driver-level
  command: `MIOpenDriver.exe bnorm -n 8 -c 16 -H 64 -W 64 -m 1 -I 0 --forw 1
  -b 0 -r 1 -s 1 --layout NCHW` (the MIOpenDriver binary is not shipped in
  the wheel).

## Falsified Hypotheses (experimentally)

- H1 Ultralytics-specific bug (pure-PyTorch repro; CPU training passes)
- H2 YOLO26 model/checkpoint bug (random-init BN fails; CPU train passes)
- H3 COCO8 dataset problem (synthetic randn input fails identically)
- H4 AMP (amp=False fails identically)
- H5 general ROCm GPU compute failure (GEMM/Conv/autograd pass)
- H12 pip dependency conflicts (no mechanism; native-layer failure)
- H13 virtual-display-adapter interference (single device; compile-layer
  error)

See `docs/HYPOTHESES.md` for confidence and the H8/H9 external-evidence
caveats (Python-3.13 and gfx1151 specificity are falsified only by
*external* evidence from MIOpen #3956, not by local experiment).

## Remaining Hypotheses

The exact reason `<type_traits>` is unresolvable, in ownership terms:

1. **H10 — undeclared host prerequisite:** Windows users of the ROCm wheels
   are expected to have an MSVC C++ STL installed (docs currently say
   otherwise — see `docs/EXTERNAL_EVIDENCE.md` §C); none is present here.
2. **H11 — wheel packaging / include-path defect:** the wheels should ship
   (or point HIPRTC at) a C++ standard library for the bundled
   msvc-target clang, or MIOpen's HIPRTC sources should avoid std headers.
3. A HIPRTC-side default-include-path defect cannot yet be excluded.

Deciding between (1) and (2) requires an A/B run on a machine with Visual
Studio installed (or adding an STL to this one) — explicitly out of Phase-1
scope. Additionally resolved post-review: why case F (Conv2d via MIOpen) succeeds
while BN fails — the MIOpen user kernel DB shows conv kernels
(`MIOpenIm2d2Col.cpp.obj`) runtime-compile successfully through the same
HIPRTC `.cpp` path, so the asymmetry is the std-header includes in the BN
sources specifically (see Mechanism addendum).

## External Correlation

`docs/EXTERNAL_EVIDENCE.md`. MIOpen #3956 (open, unanswered since
2026-04-22) shows the identical compiler-diagnostic signature on gfx1200 /
ROCm 7.2.1 / Python 3.12 — same defect class across gfx targets, Python
versions, and ROCm releases. rocm-libraries #2169 (Oct 2025, same 8060S
APU) is a **different compile-stage defect** — the gfx1151 DPP inline-asm
error fixed by TheRock#842 / PR #1288, *not* a `type_traits` failure (the
archived #2169 log contains zero `type_traits` occurrences; corrected after
independent review). Notably, #2169's Windows log shows TheRock's Oct-2025
build compiled **past the entire include chain** before failing at inline
asm — unlike the ROCm 7.14 rockrel wheels here, which fail at the first
standard header. That contrast is a Phase-2 lead toward a packaging
difference between AMD Windows builds.

## Mechanism addendum (post-review evidence)

Two artifacts archived after the independent reviews sharpened the
mechanism:

1. **Version-gated no-STL shim.** The `miopen_type_traits.hpp` embedded in
   MIOpen.dll contains preprocessor gates including
   `#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` (twice — matching the
   two `#include <type_traits>` sites). On this stack HIP is 7.14.60850
   (≥ 7.0), so the no-STL compatibility shim is disabled and MIOpen's
   BatchNorm HIPRTC sources **unconditionally require a real
   `<type_traits>`** — which neither the machine nor the wheels provide.
   (`evidence/raw/miopen/miopen_dll_shim_gate.txt`)
2. **MIOpen user kernel DB lineage.** `~/.miopen/cache/3.5.1.*/gfx1151_20.ukdb`
   (older stack, July 2025) contains successfully compiled
   `MIOpenBatchNormFwdInferSpatial.cl.obj` — BN compiled via the **OpenCL
   `.cl` path** then. The current `3.5.2.*` cache contains only conv
   kernels (`MIOpenIm2d2Col.cpp.obj`) — the HIPRTC `.cpp` path works for
   conv sources (which do not include C++ std headers) but contains no BN
   entries because those compiles fail. This explains the conv-passes /
   BN-fails asymmetry with direct cache evidence, and indicates the BN
   path moved from OpenCL to HIPRTC compilation between the MIOpen
   3.5.1-era and 3.5.2 rockrel builds.
   (`evidence/raw/miopen/user_kernel_db_listing.txt`)

## Root Cause Statement (evidence-qualified)

The failure is not attributable to Ultralytics, YOLO26, the COCO8 dataset,
AMP, or general ROCm GPU compute. It is reproducible with a standalone
PyTorch `BatchNorm2d` forward on the GPU. The failure occurs inside the
ROCm MIOpen BatchNorm path when MIOpen's runtime compilation of its
embedded spatial-BatchNorm kernels (both training and inference variants)
fails in HIPRTC because the C++ standard library header `<type_traits>`
cannot be resolved by the wheel's Windows clang toolchain on a machine
with no MSVC/C++ STL installed — and the wheels ship no such library
themselves. Which layer owns the remedy (user prerequisite vs wheel
packaging vs MIOpen sources) is not established by Phase 1 evidence.

## Confidence

- LEVEL 0 (symptom): High
- LEVEL 1 (component isolation — Ultralytics removed): High
- LEVEL 2 (mechanism — HIPRTC cannot resolve `<type_traits>` for MIOpen BN
  kernels): High
- LEVEL 3 (exact defect + owning layer): **not claimed**

## What Phase 1 Does NOT Claim

- Does not claim which repository should receive the fix (MIOpen /
  rocm-libraries / HIPRTC / PyTorch / AMD wheel packaging — all remain
  candidates pending the VS-installed A/B test).
- Does not claim installing Visual Studio is the fix (untested; no VS on
  this machine).
- Does not claim the defect is gfx1151-specific (external evidence shows
  gfx1200 affected) or Python-3.13-specific (external: 3.12 affected).
- Does not claim PyTorch is responsible (PyTorch correctly calls MIOpen and
  surfaces its error).
- Does not claim MIOpen source logic is defective (the BN algorithm is not
  implicated; the failure is in building its runtime-compiled kernel on
  Windows without a resolvable C++ STL).
- Does not propose or validate any workaround as a solution; the
  `torch.backends.cudnn.enabled=False` observation is diagnostic only.

## Next Step

Phase 2: decide H10 vs H11 (A/B on a VS-equipped machine or a controlled
addition of an MSVC STL to a test box), identify the correct fix layer,
implement the smallest valid fix, validate against this repo's reproduction
suite, and prepare the upstream report/PR (likely rocm-libraries/MIOpen or
TheRock wheel pipelines, plus doc fix if a prerequisite is intended).
