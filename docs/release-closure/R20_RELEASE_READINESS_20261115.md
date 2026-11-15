# R20 — Windows ROCm MIOpen Release Readiness and Packaging Escalation

**Created:** 2026-11-15  
**Scope:** Official Windows ROCm binaries / packaging, **not** new MIOpen or Ultralytics source code.  
**Primary issue:** [ROCm/rocm-libraries#15862](https://github.com/ROCm/rocm-libraries/issues/15862)  
**Fix:** [ROCm/rocm-libraries#13437](https://github.com/ROCm/rocm-libraries/pull/13437) merged 2026-10-19, source commit `f0a5d2664cf3334161f7b82c02dfcd2213988a8a`.  
**TheRock integration:** [ROCm/TheRock#9359](https://github.com/ROCm/TheRock/pull/9359) merged; submodule includes fix.

## R20 goal

Obtain a **published, official, compatible Windows wheel** carrying the merged MIOpen freestanding-header fix, so a fresh Windows user can run no-host-STL HIPRTC BatchNorm and standard Ultralytics YOLO training **without** `HIPRTC_COMPILE_OPTIONS_APPEND`, host MSVC STL, DLL replacements, local source builds or cache reuse.

**Already completed:** Ultralytics PR #27203 merged; [v8.4.214](https://github.com/ultralytics/ultralytics/releases/tag/v8.4.214) shipped the AMD device detection change on 2026-11-15. No new Ultralytics PR is required for R20.

## Current verified release cut-point (2026-11-15)

| Area | Evidence | Status |
|---|---|---|
| MIOpen merged source | `f0a5d266` | PASS |
| TheRock submodule | #9359 includes merged source | PASS |
| Legacy Windows wheels | [whl-multi-arch/rocm-sdk-libraries](https://repo.amd.com/rocm/whl-multi-arch/rocm-sdk-libraries/) lists 7.14.1 latest | PRE-FIX / FAIL |
| Stable Windows wheels | [whl-next/rocm-sdk-libraries](https://stable.repo.amd.com/rocm/whl-next/rocm-sdk-libraries/) lists 10.1.0 latest | PRE-FIX / FAIL |
| `rocm_sdk_libraries-10.1.0` Windows | Frozen [P16 audit](P16_OFFICIAL_WHEEL_BINARY_AUDIT.md): DLL version `3.6.1.39d8d603`, pre-2026-10-19; no-STL regression FAIL | BLOCKED |
| Merged-source reference binary | Frozen P14 no-host-STL comparison, same failure reproduced against shipping wheels, fixed reference PASS | ENGINEERING_REFERENCE only |
| Release owner | #15862 currently open, no assignee | NEEDS_ASSIGNMENT |
| Published fixed Windows wheel | No qualifying artifact verified | BLOCKED_RELEASE |

Index listing availability is not binary provenance. A new release must independently pass source/build/SHA256 verification and behavioral tests. `miopen_initializer_list` string is a useful screening signal, **not** sufficient positive proof alone.

See [P14 official wheel audit](P14_OFFICIAL_WINDOWS_WHEEL_AUDIT.md), [P16 binary re-audit](P16_OFFICIAL_WHEEL_BINARY_AUDIT.md), and [RELEASE_LINEAGE.md](../../release-provenance/RELEASE_LINEAGE.md).

## Release owner decision request

Please route #15862 to the Windows ROCm / TheRock package release owner and provide:

1. **Owner and cut-point:** team/contact, planned release branch or snapshot, with source lineage containing `f0a5d266`.
2. **First installable artifact:** an official Windows `rocm_sdk_libraries` wheel or compatible full-stack build for independent verification, with artifact URL, version, SHA256 and publication channel.
3. **Release mechanism:** is an ABI-compatible `rocm_sdk_libraries` patch/post-release (e.g. `.postN`) feasible with the existing 10.1.0 torch/device-wheel dependency set, or does this require a full ROCm SDK / PyTorch wheel cut? **This is a question, not an approved ABI claim.**
4. **Release gate:** run no-host-MSVC-STL HIPRTC BatchNorm forward/backward on cold caches and record Windows gfx1100/gfx1151 GPU coverage before promotion.

TheRock documentation identifies **dev**, **nightly**, **rc**, and **stable** packaging channels, and discusses *exceptional manual post releases*; these are possible release-engineering routes, **not evidence that a compatible patched wheel is already published**. Reference: [TheRock packaging versioning](https://github.com/ROCm/TheRock/blob/main/docs/packaging/versioning.md).

## Candidate acceptance contract (R22 hand-off)

**G0 — Provenance:** Official URL, exact wheel filename/version, SDK dependency set, SHA256 of downloaded package and loaded `MIOpen.dll`, build commit and TheRock submodule ancestry to `f0a5d266`. Distinguish stable vs pre-release channel. No DLL substitution.

**G1 — Unmodified/no-STL:** Fresh Windows Python environment, no VS Build Tools host STL dependency, no `HIPRTC_COMPILE_OPTIONS_APPEND`, no `MIOPEN_*` or host STL overrides, separate cold cache. BatchNorm2d(100) forward/backward and finite gradients pass at the previously failing shape. Record `VCToolsInstallDir` control, loader paths, commands and exit codes.

**G2 — Device-specific packages:** Test Windows gfx1100 (RX 7900 XTX) and gfx1151 (Radeon 8060S) with matching `torch`, `torchvision`, `amd-torch-device-gfx*`, `amd-torchvision-device-gfx*`, and ROCm SDK wheels. Confirm `torchvision.ops.nms` GPU kernel as well as core GEMM/BN.

**G3 — Released Ultralytics workflow:** `ultralytics==8.4.214` (or a newer independently verified release), exact CLI `yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1`; genuine GPU selection, AMP check, finite loss, validation and checkpoints.

**G4 — Model update/resume:** Separate multi-batch AMP test with `named_parameters` delta and actual successful optimizer steps; save/restart/resume with checkpoint state restored.

**G5 — Reliability:** Multiple independent cold starts and warm starts, no unexplained `hipErrorInvalidKernelFile` / MIOpen cache failures. Such failures are separately classified and **not automatically assumed fixed** by #13437.

**G6 — User experience:** Clean Windows VM or freshly installed host, official packages only, no hidden compilers or shims, independent developer replication and install docs.

**Explicit non-goals:** Claiming TensorRT support, ONNX Runtime `CUDAExecutionProvider` on AMD, NVIDIA performance parity or all available GPU features.

## R20 decision log / next actions

| Item | Owner | Present state | Next event |
|---|---|---|---|
| #15862 release routing | AMD ROCm / TheRock release engineering | Owner not yet identified | Assign and answer 4 questions |
| Candidate package provenance | AMD release engineering | No qualified post-fix Windows wheel verified | Publish candidate official artifact with build manifest |
| Candidate smoke verification | Windows gfx1100/gfx1151 validation operator | Script/evidence basis exists in RCA | Run immediately after candidate becomes available |
| Official production release | AMD release engineering | BLOCKED | Publish validated stable SDK wheel(s) |
| Full user Golden Path | ROCm + Ultralytics developer ecosystem | BLOCKED on official artifact | Run R22 and R23 |

**R20 current verdict: RELEASE_REQUEST_READY / BLOCKED_EXTERNAL_PUBLICATION.** No wheel is asserted to have been released. Do not close #15862 until an official post-fix wheel has independent Windows no-STL runtime PASS and provenance closure.
