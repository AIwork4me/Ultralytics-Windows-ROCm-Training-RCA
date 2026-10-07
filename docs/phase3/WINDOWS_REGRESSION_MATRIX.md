# Phase-3 Gate 65/68 — Windows Regression Matrix (REAL patched MIOpen build)

Date: 2026-10-07. Build: patched develop `b68f8944` + candidate V1,
MIOpen.dll SHA256 `0a0878db…` loaded by PyTorch (provenance recorded per
run). Raw: `evidence/phase3/raw/regression/`, `evidence/phase3/raw/yolo/`,
`evidence/phase3/raw/runtime/`.

## Gate 65 — BatchNorm shape/variant matrix (default env, fresh caches)

| Case | Result | Numerics vs CPU |
|---|---|---|
| BN2d minimal 8×16×64×64 (train+eval) | PASS | max_abs 7.2e-7; run_mean Δ 1.3e-10; run_var Δ 6.0e-8 |
| BN2d issue-3956 shape 4×64×32×32 | PASS | max_abs 4.8e-7 |
| BN2d YOLO-like 16×32×160×160 | PASS | max_abs 9.5e-7 |
| BN1d with 3D input 8×16×512 | PASS | max_abs 7.2e-7 |
| BN3d 4×8×16³ | PASS | max_abs 4.8e-7 |
| BN2d eval-only | PASS | finite |
| Controls: BN1d(2D), GroupNorm, Conv2d, Linear bwd, GPU GEMM 1024² | all PASS | finite |

All gradients finite; running statistics update correctly (≤1.2e-7 vs
CPU reference) — Gate 66 numerics folded into the same runs
(`g65_66_results.json`; quality matches Phase-2's ≤7.2e-7 on the shim).

## Gate 63/64 — no-MSVC single-variable A/B (MSVC include tree renamed away)

| Arm | MIOpen.dll (SHA256, loaded-path proven) | Result |
|---|---|---|
| A control | wheel `74b4ee03…` | **FAIL** — exact original signature: `miopen_type_traits.hpp:151: 'type_traits' file not found` → `HIPRTC_ERROR_COMPILATION(6)` → exit 1 |
| B treatment | patched build `0a0878db…` | **PASS** — exit 0, finite fwd+bwd, fresh isolated kernel/comgr caches |

The source fix requires NO host C++ standard library. (Emulation
validated by arm A reproducing the pre-MSVC machine state live.)

## Gate 68 — non-BN RTC kernel matrix (mapped to upstream kernels)

| Torch workload | Upstream RTC sources exercised | Default env | No-MSVC env |
|---|---|---|---|
| MaxPool2d fwd+bwd | MIOpenPoolingBwd*.cpp (type_traits via vector_types) | PASS | PASS |
| AvgPool2d fwd+bwd | MIOpenPooling* | PASS | PASS |
| AdaptiveAvgPool2d | MIOpenPooling* | PASS | PASS |
| PReLU fwd+bwd | MIOpenPReLU.cpp (tensor_view, cstdint) | PASS | PASS |
| Conv2d depthwise / grouped / dilated / 1×1 | MIOpenConvDirect*, Winograd, gemm paths | PASS | PASS |
| ConvTranspose2d | MIOpenConvBwdWrapper family | PASS | PASS |
| Softmax (attn-like shapes) | torch-native (no MIOpen) — control | PASS | PASS |
| Dropout2d | torch-native (rocrand-inlined path in MIOpen untouched) | PASS | PASS |

Evidence: `g68_results.json` (default env), `g68_nomsvc_results.json`
(no-MSVC). **11/11 PASS in both environments** — every torch-reachable
MIOpen RTC workload tested works under the patched build with no host
STL. Residual boundary (Gate 54 statics): `MIOpenKthvalue/Getitem/
MultiMarginLoss/ReduceSum/SoftMarginLoss` closures still carry unguarded
`<initializer_list>`/`<limits>` (tensor_view.hpp / radix.hpp); torch does
not route its public ops to those kernels (kthvalue uses torch's own
topk path), but MIOpenDriver/internal paths could — handled in the final
scope decision (Gate 76) with ready-validated fix shapes (canaries
G57-7/G57-8).

## Gate 67 — YOLO26 end-to-end (patched build, fresh MIOpen caches)

| Mode | Epoch | Validation | best/last.pt | Exit | Loaded MIOpen SHA |
|---|---|---|---|---|---|
| amp=False | complete | P .551 R .962 mAP50 .943 mAP50-95 .669 | saved | 0 | 0a0878db… |
| default AMP | complete | P .551 R .961 mAP50 .942 | saved | 0 | 0a0878db… |

No MIOpen compile failures, no CPU fallback, GPU device confirmed.
Numbers match Phase-2's closure quality (functional check on coco8).

Build-config note (documented deviation): this build has
`MIOPEN_USE_COMPOSABLEKERNEL=OFF`, so the separate
`MIOpenCKGroupedConv_gfx1151.dll` companion logs 5 unresolved-symbol
warnings at load — convolutions route through MIOpen's own/Winograd/GEMM
solvers (all green above). This is a build-environment artifact, not a
patch effect.
