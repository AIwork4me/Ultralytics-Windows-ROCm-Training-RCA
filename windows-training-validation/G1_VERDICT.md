# G1 VERDICT — Windows Native HIP / PyTorch / MIOpen Training Primitives

Date: 2026-11-14 · Machine: Ryzen AI MAX+ 395 / Radeon 8060S (gfx1151) / driver 32.0.22032.6002
HIP 7.14.60850 · torch 2.12.0 · Python 3.13.16 · Verdict: **PASS (on ENV B patched build)** · ENV A official-wheel baseline PASS with exact #3956 negative control

## Environments & binaries (provenance per leg)

| Leg | Env | MIOpen.dll actually loaded (in-process probe) | Classification |
|---|---|---|---|
| envB_stl_rep1..3, envB_nostl_rep1..3 | pm13437_merged | `ed7c67a9…` (source-built from f0a5d266, marker=2) | SOURCE_BUILT_PATCHED |
| gtest_nostl_r1..3 | b58m build tree | same patched binary (cache label `3.6.2.f0a5d266` printed in logs) | SOURCE_BUILT_PATCHED |
| envA_stl | pm13437_official | `e97891df…` (official 7.14.1 wheel, marker=0) | OFFICIAL_RELEASE |
| envA_nostl_neg | pm13437_official | official (at rest, hash-verified) | OFFICIAL_RELEASE |

## Matrix (16 primitives) — `tests/g1_primitives.py`

GEMM FP32; Conv2d fwd+bwd (grad_input/weight/bias); BatchNorm2d train fwd (output +
running_mean + running_var **unbiased**) + train bwd (3 grads); BatchNorm2d eval (running-stat
semantics); BatchNorm1d 2-D; BatchNorm1d 3-D (spatial → MIOpen); BatchNorm3d; GroupNorm;
LayerNorm; kthvalue FP32/FP16/BF16 (tie-free exactly-representable values, value+index exact);
optimizer.step (matches CPU SGD formula bit-exactly); GPU sync (event timing > 0).
All with CPU float64 references, declared tolerances, NaN/Inf checks, device checks.

## Results

| Leg group | Mode | Reps | Result |
|---|---|---|---|
| ENV B patched | STL visible | 3 independent cold cache homes | **16/16 PASS ×3** (`reports/G1_MATRIX_pm13437_merged_stl.json`) |
| ENV B patched | **host STL hidden** (VCToolsInstallDir redirect + INCLUDE='') | 3 independent cold cache homes | **16/16 PASS ×3** (`reports/G1_MATRIX_pm13437_merged_nostl.json`) |
| gtest `CPU_HipRtcSelfContained_NONE.RtCompilesInlineKernelWithoutHostStl` | ambient + no-STL | 3 fresh cache homes ×2 variants | **PASS ×6** (`raw/gtest_nostl_r*.log`; real HIPRTC compiles 12–16 s each; cache `.ukdb` created per home) |
| ENV A official | STL visible | 1 cold | **16/16 PASS** (`reports/G1_MATRIX_pm13437_official_stl.json`) — pre-fix wheel works normally when host STL present |
| ENV A official | host STL hidden | 1 cold | **EXPECTED_FAIL with exact #3956 signature** (`reports/G1_NEGATIVE_CONTROL.json`; raw stderr carries all four signature elements) |

## Negative-control signature (stderr, verbatim elements)

`hiprtcCompileProgram(…)` · `HIPRTC_ERROR_COMPILATION (6)` · `MIOpenBatchNormFwdTrainSpatial.cpp` ·
`miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found` ·
`hipoc_program.cpp:299: Code object build failed` — identical to the original MIOpen #3956 /
Ultralytics-failure signature.

## Honest changelog (failures found & fixed during this gate)

1. **First envB STL matrix run: 13/16** — all three failures were **test-reference bugs**, not GPU bugs, each root-caused before any fix:
   - BN train forward: reference double-applied the running-stat update (read post-update running stats). Isolated probe (`tests/g1_bn_estimator_probe.py`) proved GPU running_var matches the unbiased float64 reference to **6.8e-08** and matches PyTorch semantics (old "biased estimator" caveat from phase5_7/5_8 is resolved: this stack uses the unbiased estimator correctly).
   - BN eval: reference wrongly used this-batch statistics instead of running statistics.
   - kthvalue bf16: my value grid created bf16 ties (bf16 spacing = 2 above 256), making the returned index implementation-defined; value agreed (256.0) but index differed. Fixed with tie-free exactly-representable grids per dtype.
2. **Negative-control verdict initially read UNEXPECTED_FAIL** — Python's RuntimeError carries only `miopenStatusUnknownError`; the full signature lives on stderr. Runner now re-derives the signature from captured stderr. No GPU behavior change involved.

## Limitations

- ENV B is **source-built**, not an official wheel (G0 BLOCKED_RELEASE) — G1 PASS therefore validates the MIOpen binary built from the merged PR, not a shipped package.
- No cache-hit masking: every leg ran a fresh USERPROFILE cache home; `.ukdb`/cache artifacts enumerated per leg (`cache_files_created` in runner reports).
- gfx1100/gfx1200/Linux legs: BLOCKED_HARDWARE (not connected).
- Two zombie processes incident (see `environment/INCIDENT_ZOMBIE_PROCESSES.md`): env-B restore deferred; env-B remains intentionally in patched state for G2/G3.
- 1/15 GPU processes today hung at normal exit (exit-time cleanup hang) — recorded for G4.3.

## G1 PASS condition — met

All P0 primitives executed on the real Windows ROCm GPU, numerically validated against CPU
references, no CPU fallback (device checks + loaded-DLL probes per leg), negative control
reproduces the original failure exactly, positive path passes without host STL.
