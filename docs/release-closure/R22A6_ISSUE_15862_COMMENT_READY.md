## R22A.6 update — 2026-11-17: official post-fix Windows Nightly independently passes gfx1100 + gfx1151; Stable publication is the remaining blocker

This updates the Nov 14–15 findings in this issue: **there now is an AMD-official Windows Nightly wheel containing the merged MIOpen #13437 fix**. The prior finding that the published Windows **Stable 10.1.0** MIOpen was pre-fix remains true. These are different release channels.

**Source fix:** [ROCm/rocm-libraries#13437](https://github.com/ROCm/rocm-libraries/pull/13437) merged as [f0a5d266](https://github.com/ROCm/rocm-libraries/commit/f0a5d2664cf3334161f7b82c02dfcd2213988a8a); [TheRock#9359](https://github.com/ROCm/TheRock/pull/9359) integrated that source lineage.

**Exact independently checked official Nightly identity (2026-11-16, Windows cp312):**
- PyTorch 2.16.0a0+rocm10.3.0a20261116, torchvision 0.30.0a0+rocm10.3.0a20261116, ROCm SDK 10.3.0a20261116, released PyPI Ultralytics 8.4.214. Each machine has its own 46-package version/URL/SHA256 lock and matching GPU-specific device wheels.
- Official Windows rocm_sdk_libraries-10.3.0a20261116 wheel **SHA256 b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0**.
- **Actual GPU child-loaded** MIOpen.dll **SHA256 f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6** on both machines, embedded MIOpen 3.6.3.25f28906, marker miopen_initializer_list observed 2×. Source ancestry was independently checked against f0a5d266; the marker by itself is only a screening signal.

**Two separate real Windows Radeon GPU experiments:**

| Real hardware | Auditable original evidence | Verdict |
| --- | --- | --- |
| Radeon 8060S / **gfx1151**; Win 26200, driver 32.0.22032.6002 | [106-entry SHA256 physical pack](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n1/R22A5N1-GFX1151-20261117-B/SHA256MANIFEST.json), [final strict acceptance](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n2/R22A5N2-GFX1151-20261117/nightly_acceptance.json) | **PKG/LK/G0/G1/G2/G3/G4/G5/G7: 9/9 PASS** |
| RX 7900 XTX / **gfx1100**; Win 26300, driver 32.0.21030.2001 | [83-entry SHA256 physical pack](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n/R22A5N-GFX1100-20261117-A/SHA256MANIFEST.json), [exact integration HEAD CI](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/actions/runs/44068854644) | **9/9 PASS** |

Each host ran **two independent no-host-STL cold-cache BatchNorm forward/backward** tests successfully with the official Nightly DLL, plus a matched official **pre-fix** control that failed with HIPRTC_ERROR_COMPILATION / 'type_traits' file not found. The actually loaded pre-fix DLL was SHA256 **e97891df7ea0ba2b6eda703bd69499521dc9a38300fe626f412b5544dec647bc** (marker 0). No manual DLL replacement, header injection, HIPRTC shim or custom Ultralytics source branch was used in the positive trials.

On both actual GPUs, the same official Nightly stack also completed YOLO26n/COCO128 training, GPU GEMM/Conv/BatchNorm/NMS, genuinely observed low-precision AMP and effective optimizer updates, checkpoint save/reload, controlled interrupt + new-process resume, and Windows worker lifecycle. **G5 is deliberately capped at RESUME_PASS_CORE_STATE_VERIFIED** (upstream LR scheduler not serialized); no FULL state-restoration claim.

**Independence:** [PR #22](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/pull/22) (gfx1151) and [PR #23](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/pull/23) (gfx1100) merged with unchanged original raw receipts. Frozen integration HEAD **78098c59ad7f89951a0fe99d4b39e2752b803932**. [Post-merge exact-HEAD CI 44068854644](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/actions/runs/44068854644) verified the same checkout, 419 CPU contract tests, 902 release checks / 0 violations, the gfx1100 83-file manifest and independent nine-gate replay. The CI replays **previous physical evidence**, not fresh GPU execution.

**Detailed bilingual-audit-ready Release Engineering dossier:** [R22A.6 handoff](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/f6829bd7ccf932ecc5c6e90e3e2f56469a1ae262/docs/release-closure/R22A6_AMD_RELEASE_ENGINEERING_HANDOFF_20261117.md).

### Concrete request for AMD Windows ROCm / TheRock Release Engineering

1. **Owner:** Who is the DRI for the Windows rocm_sdk_libraries wheel and the matching torch / torchvision / gfx1100 / gfx1151 device-wheel publication?
2. **First Stable/RC artifact:** Which exact release/branch/build contains f0a5d266, what Python ABI and GPU architectures will it cover, and where will the official index and package manifest be published? Please identify the first available compatible candidate.
3. **Packaging:** Is a supported libraries-only patch feasible, or must Windows SDK / PyTorch / device wheels be released together as a version-aligned set? We do not want an end-user DLL-swap workaround.
4. **Regression protection:** Could no-host-STL cold-cache spatial-BatchNorm forward/backward with actual child DLL identity, finite gradients and no CPU fallback become a Windows release gate?
5. **Qualification:** What additional platform-support validation is required before Windows Radeon YOLO training can be claimed officially supported (as opposed to demonstrated experimentally)?

As checked 2026-11-17, the [official Stable SDK Libraries index](https://stable.repo.amd.com/rocm/core/whl-next/rocm-sdk-libraries/) still lists Windows 10.0.0 and 10.1.0; our tested 10.1.0 MIOpen is pre-fix. **A post-fix Stable/RC GPU validation, fresh-Windows G9 installation and independent end-user workflow have not yet been completed.** We can promptly test the first eligible official Stable/RC wheel set on both physical GPU architectures and report the original results back to this issue.

Thanks for identifying the release owner and first supported artifact.