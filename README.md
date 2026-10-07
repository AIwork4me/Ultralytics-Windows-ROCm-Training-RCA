# Ultralytics YOLO Training on Windows ROCm — gfx1151 Root Cause Analysis

An independent, evidence-first reproduction and root-cause analysis of a
specific failure: **YOLO26 GPU training crashes on native Windows with AMD
ROCm PyTorch (Radeon 8060S / gfx1151), while YOLO inference works fine.**

> Not an AMD, ROCm, or Ultralytics official statement — this is an
> independently reproduced engineering investigation. Every claim links to
> raw logs in [`evidence/`](evidence/).

## TL;DR

**Working** (same machine, same stack): `pip install ultralytics` + AMD ROCm
wheels → YOLO26n inference on the Radeon 8060S (4 persons + 1 bus on
bus.jpg), GPU GEMM, GPU convolutions, CPU training.

**Failing**: YOLO26 GPU training dies on the first batch with:

```
MIOpen(HIP): Error [Compile] 'hiprtcCompileProgram(...)' MIOpenBatchNormFwdTrainSpatial.cpp: HIPRTC_ERROR_COMPILATION (6)
...miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found
1 error generated when compiling for gfx1151.
MIOpen Error: ...hipoc_program.cpp:299: Code object build failed.
RuntimeError: miopenStatusUnknownError
```

**Minimal reproduction — 5 lines, no Ultralytics:**

```python
import torch, torch.nn as nn
bn = nn.BatchNorm2d(16).cuda().train()
x = torch.randn(8, 16, 64, 64, device="cuda")
y = bn(x)    # RuntimeError: miopenStatusUnknownError
```

**Root cause (proven through Phase 2, LEVEL 3):** every *spatial* BatchNorm
on the GPU (`BatchNorm2d`, `BatchNorm3d`, `BatchNorm1d` with 3D input) goes
through MIOpen, which runtime-compiles an embedded spatial-BatchNorm kernel
with HIPRTC. For HIP >= 7.0, upstream MIOpen gates
(`miopen_type_traits.hpp` via commit `ce14dab3`/PR #3803;
`miopen_utility.hpp` via `b514736610`/PR #3147) disable the internal
no-STL compatibility shims and unconditionally include real
`<type_traits>`/`<utility>`. That assumption holds on Linux (system STL
always present) but fails on AMD's Windows pip wheels, whose bundled
`x86_64-pc-windows-msvc`-target clang/HIPRTC ships no C++ standard library
and no include-path configuration. The underlying requirement is resolvable
C++ standard-library functionality; MSVC Build Tools is one sufficient
Windows provider of it (not an intrinsic requirement). Full chain:
[`docs/PHASE2_LEVEL3_RCA.md`](docs/PHASE2_LEVEL3_RCA.md).

## Scope

- **PHASE 1 (complete)** = Root Cause Analysis: reproduce, minimize,
  isolate the layer, publish evidence. LEVEL-2 RCA.
- **PHASE 2 (complete)** = LEVEL-3 RCA with exact upstream anchors +
  candidate-remedy validation + YOLO training closure (amp=False and
  default AMP), review panel, checksummed evidence.
- **PHASE 3 (complete)** = Upstream Patch Closure: patch real
  rocm-libraries source, build patched MIOpen on Windows, prove the
  BatchNorm failure disappears via the source fix alone, audit the full
  RTC std-header dependency scope, validate Linux HIP>=7 regression
  safety (done 2026-10-08 on real gfx1151 hardware, including the
  kthvalue runtime radix path), and produce a maintainer-ready patch
  package. **No upstream submission is made in any phase.**

## Environment under test

| Component | Version |
|---|---|
| OS | Windows 11 (10.0.26200), native |
| APU | AMD Ryzen AI MAX+ 395, Radeon 8060S (**gfx1151**, 20 CUs) |
| Python | 3.13.13 (conda base, `C:\Users\rocm\miniconda3`) |
| PyTorch / torchvision | 2.12.0+rocm7.14.0 / 0.27.0+rocm7.14.0 |
| ROCm (pip wheels) | 7.14.0 · HIP 7.14.60850 · MIOpen 3.5.2 |
| Ultralytics | 8.4.174 |

Full baseline: [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

## Key results

| Experiment | Result |
|---|---|
| GPU GEMM 4096² | ✅ PASS |
| `yolo predict` GPU | ✅ PASS |
| `yolo detect train` GPU (epochs=1) | ❌ FAIL — signature above |
| same, `amp=False` | ❌ FAIL (AMP falsified) |
| same, `device=cpu` | ✅ PASS (model/data/Ultralytics exonerated) |
| pure `BatchNorm2d` GPU train | ❌ FAIL (Ultralytics exonerated) |
| pure `BatchNorm2d` GPU **eval** | ❌ FAIL (`MIOpenBatchNormFwdInferSpatial.cpp`) |
| `BatchNorm1d` (3D in) / `BatchNorm3d` GPU train | ❌ FAIL (same spatial kernel) |
| `BatchNorm1d` (2D in) / `GroupNorm` GPU | ✅ PASS |
| `BatchNorm2d` GPU train, `cudnn.enabled=False` *(diagnostic only)* | ✅ PASS (MIOpen BN path bypassed) |
| Conv2d / Linear+backward GPU | ✅ PASS |

Full matrix: [`docs/EXPERIMENT_MATRIX.md`](docs/EXPERIMENT_MATRIX.md).

## Reproduce it yourself

```powershell
# any machine with the same AMD ROCm Windows wheel stack
python scripts\01_gpu_gemm_control.py      # control: PASS
python scripts\02_batchnorm_minimal.py minimal   # repro: FAIL + signature
python scripts\03_batchnorm_matrix.py     # full A/B matrix
```

Or everything: `powershell -File scripts\run_all_rca.ps1`
(evidence lands in `evidence\raw\...`).

## Documentation map

| Doc | Content |
|---|---|
| [`docs/RCA.md`](docs/RCA.md) | Full root-cause analysis, evidence chain, confidence, non-claims |
| [`docs/EXPERIMENT_MATRIX.md`](docs/EXPERIMENT_MATRIX.md) | Every experiment with raw-log links |
| [`docs/HYPOTHESES.md`](docs/HYPOTHESES.md) | H1–H13 with falsification status |
| [`docs/CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md) | Claim ledger (C001–C030) |
| [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | Machine/software baseline |
| [`docs/EXTERNAL_EVIDENCE.md`](docs/EXTERNAL_EVIDENCE.md) | Upstream issue comparison (MIOpen #3956 et al.) |
| [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md) | Phase 2 plan |
| [`findings/phase1_conclusion.json`](findings/phase1_conclusion.json) | Machine-readable conclusion |
| [`evidence/`](evidence) | Raw logs + `manifest.json` + `SHA256SUMS.txt` |

## External correlation

The identical compiler signature (same header, same line 151) is reported
upstream in [ROCm/MIOpen#3956](https://github.com/ROCm/MIOpen/issues/3956)
(open, unanswered) on gfx1200 / ROCm 7.2.1 / Python 3.12 — a different GPU,
Python, and ROCm than here.
[rocm-libraries#2169](https://github.com/ROCm/rocm-libraries/issues/2169)
(same 8060S APU, Oct 2025) is a **different** compile-stage defect — the
gfx1151 DPP inline-asm error fixed by
[TheRock#842](https://github.com/ROCm/TheRock/issues/842) /
[PR#1288](https://github.com/ROCm/rocm-libraries/pull/1288) — but its
Windows log proves another AMD Windows build compiled past the whole
include chain, unlike the ROCm 7.14 wheels here. Details:
[`docs/EXTERNAL_EVIDENCE.md`](docs/EXTERNAL_EVIDENCE.md).

## Status

- **Phase 1: complete — LEVEL-2 RCA** (failure reproduced, minimized,
  layer-isolated; MIOpen HIPRTC std-header resolution identified).
- **Phase 2: complete — LEVEL-3 RCA + candidate validation + YOLO
  closure** (exact upstream commits identified; MSVC-install,
  INCLUDE-injection, and freestanding-shim remedies all validated;
  regression matrix 8/8; numerics <= 7.2e-7 vs CPU; YOLO26n coco8
  epochs=1 train+val closure on GPU in both amp modes).
- **Phase 3: complete — Upstream Patch Closure (cross-platform)**:
  real rocm-libraries develop source patched (two-commit series in
  `patches/phase3/`, P3-FINAL-R3), patched MIOpen BUILT on Windows with
  the wheel toolchain, loaded by PyTorch with SHA-proven provenance, the
  original BatchNorm failure proven FIXED by the source change alone
  with NO host STL (live single-variable A/B), full BN/non-BN/numerics/
  YOLO matrices green, 104-kernel RTC std audit, adversarial 4-reviewer
  panel with all blockers resolved. **Linux independent regression
  validation PASS (2026-10-08, gfx1151, ROCm 7.14 wheel stack)**:
  exact SOURCE_SHA + exact patch bytes consumed unmodified, source-built
  unpatched/patched A/B via LD_PRELOAD+dladdr, fresh caches, BN 8/8,
  numerics bit-identical (max_abs 0.0), non-BN RTC 11/11, YOLO
  predict+train, no-STL/partial-STL canaries, kthvalue runtime
  UNPATCHED PASS → PATCHED PASS, three independent Linux reviews +
  final adversarial audits. Cross-platform: Windows FAIL→PASS, Linux
  PASS→PASS. Final status:
  WINDOWS PATCH CLOSURE PASS · LINUX INDEPENDENT REGRESSION PASS ·
  CROSS-PLATFORM PATCH CLOSURE PASS · UPSTREAM PR NOT CREATED
  (see `docs/phase3/CROSS_PLATFORM_VALIDATION.md`,
  `docs/phase3/linux/LINUX_VALIDATION_SUMMARY.md`,
  `findings/phase3/final_readiness/`).

> Maintainer-ready patch package prepared locally (patches/phase3/
> 0001+0002, PR draft, routing plan, proposed CI test). No upstream
> submission has been made.

**No upstream fix has landed and none is claimed.** Nothing in this
repository implies AMD official support changed. As of Phase 2, two
user-level remedies are validated for affected machines (see
[`docs/PHASE2_SUMMARY.md`](docs/PHASE2_SUMMARY.md)): installing VS 2022
Build Tools with the C++ workload, or a `ROCM_PATH`-based freestanding
shim directory. Neither depends on an upstream change.

## License

[MIT](LICENSE) — scripts and documentation. Third-party trademarks belong
to their owners.

## Phase-2 note on null-result artifacts

`evidence/phase2/raw/candidateB/standalone_compile_ab*.txt` record an
ABANDONED harness (both arms fail on MIOpen option-set divergence before
reaching the include question). They are retained as null results and are
NOT cited by any conclusion; the patched-header validation that IS cited
lives in `candidate_b_v2_validation.txt`.
