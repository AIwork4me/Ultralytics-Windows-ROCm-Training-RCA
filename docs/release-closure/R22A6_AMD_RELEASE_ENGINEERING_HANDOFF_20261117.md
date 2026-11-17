# Mission R22A.6 — Windows ROCm MIOpen #13437 Release Engineering Handoff

Date: 2026-11-17. Source: two independently measured physical Windows Radeon GPU experiments, integrated at immutable Git commit 78098c59ad7f89951a0fe99d4b39e2752b803932.

**Status: NIGHTLY_DUAL_ARCH_FUNCTIONAL_EVIDENCE_COMPLETE; FIXED STABLE WINDOWS SDK/PYTORCH ARTIFACT STILL REQUESTED.**

**Audience:** AMD Windows ROCm / TheRock release and packaging owners, and MIOpen reviewers. This document records actual evidence and requested release actions, not a Stable qualification or a broad ROCm training-support announcement.

## 1. What changed since ROCm/rocm-libraries#15862 was filed?

Original Issue #15862 correctly described the situation as of 2026-11-14: the accessible Stable Windows wheel contained MIOpen built before the merged freestanding HIPRTC header fix. That observation must stay in the historical record.

**New evidence, measured 2026-11-17:** an AMD-official Windows Nightly SDK/PyTorch package set from 2026-11-16 now contains the fix. Two different real Windows Radeon GPUs independently downloaded that package set, checked the bytes actually loaded inside the GPU child process, and completed no-host-STL BatchNorm, YOLO26n training, low-precision AMP and interrupted checkpoint resume without private DLL replacement, manual header injection or a modified Ultralytics fork. The negative official pre-fix control still fails with the expected type_traits HIPRTC error.

**Remaining gap:** AMD's public Stable SDK Libraries index currently lists Windows 10.0.0 and 10.1.0, and the already tested 10.1.0 Windows DLL is pre-fix. The published Nightly PASS must not be relabeled Stable. Release owners should nominate the first complete compatible Stable/RC SDK + torch/torchvision + device-wheel set built from the fix, including the Windows install path and supported gfx coverage.

Official Stable SDK Libraries index observed on 2026-11-17:
https://stable.repo.amd.com/rocm/core/whl-next/rocm-sdk-libraries/

Official working Nightly SDK Libraries index (version-specific wheel still listed):
https://nightly.repo.amd.com/rocm/core/whl-next/rocm-sdk-libraries/

Source fix: https://github.com/ROCm/rocm-libraries/pull/13437
Merged fix commit: https://github.com/ROCm/rocm-libraries/commit/f0a5d2664cf3334161f7b82c02dfcd2213988a8a
TheRock source-integration PR: https://github.com/ROCm/TheRock/pull/9359
Issue to update: https://github.com/ROCm/rocm-libraries/issues/15862

## 2. Exact observed, frozen official software identity

| Component | Actual measured Nightly identity |
| --- | --- |
| Channel | AMD official Nightly, 2026-11-16 snapshot |
| Python ABI | cp312 / Windows win_amd64 |
| torch | 2.16.0a0+rocm10.3.0a20261116 |
| torchvision | 0.30.0a0+rocm10.3.0a20261116 |
| ROCm SDK core/libraries/device | 10.3.0a20261116 (device wheel specific to GPU) |
| Ultralytics | 8.4.214, official PyPI release, source not patched |
| SDK Libraries wheel | rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl |
| SDK Libraries wheel SHA256 | b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0 |
| **Real GPU-child-loaded MIOpen.dll SHA256** | **f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6** |
| MIOpen build embedded in that DLL | 3.6.3.25f28906 |
| MIOpen freestanding-header marker | miopen_initializer_list observed 2 times |
| Provenance claim | Build ancestry independently checked against merged f0a5d266; marker alone was not used as definitive ancestry proof |

Frozen file-level package lock:
- gfx1151 (https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n1/R22A5N1-GFX1151-20261117-B/01_package_provenance/resolved_wheel_lock_nightly_gfx1151.json): lock SHA256 cf147540a166a623bcf4f7961e07540980af5e117c7a0cc1f2cf38c2b013a7ac.
- gfx1100 (https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n/R22A5N-GFX1100-20261117-A/01_package_provenance/resolved_wheel_lock_nightly_gfx1100.json): lock SHA256 fd0e898fe88cd79fda81dfc1beea5cc59c1100f0be1486989fd4aa97fc7abe60.

Each run has an independent 46-distribution package lock, package origin/ABI checks, installed-vs-lock reconciliation and actual DLL load evidence. The same SDK Libraries wheel and MIOpen DLL hash were observed on both machines. Architecture-specific wheel filenames and Windows drivers differ.

## 3. Independent physical test A: Radeon 8060S / gfx1151

- Device: AMD Radeon(TM) 8060S Graphics, gfx1151; Windows 11 reported build 10.0.26200.0; driver 32.0.22032.6002.
- Run ID: R22A5N1-GFX1151-20261117-B.
- Original file manifest: **106 independent SHA256 entries**. https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n1/R22A5N1-GFX1151-20261117-B/SHA256MANIFEST.json
- Actual child-loaded binary: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n1/R22A5N1-GFX1151-20261117-B/02_runtime_identity/g0_child_identity.json
- Official candidate cold no-host-STL runs: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n1/R22A5N1-GFX1151-20261117-B/02_nostl_candidate/nostl_candidate_t1.json and https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n1/R22A5N1-GFX1151-20261117-B/02_nostl_candidate/nostl_candidate_t2.json
- Official pre-fix control: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n1/R22A5N1-GFX1151-20261117-B/03_nostl_negative_control/nostl_prefit_control_v2.json
- Full R22A.5N.2 strict acceptance: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n2/R22A5N2-GFX1151-20261117/nightly_acceptance.json

Result: all nine PKG/LK/G0/G1/G2/G3/G4/G5/G7 independently recomputed PASS. G1 includes two positive cold candidate trials and official pre-fix expected-failure control. Real GPU GEMM, autograd, convolution/BatchNorm and torchvision GPU NMS pass. Released YOLO26n trained on COCO128 for 3 epochs with true low-precision output observations and independently verified effective optimizer updates; a deliberate interruption and new-process resume, checkpoint save/load/inference and real Windows multiprocessing lifecycle were verified.

G5 is only **RESUME_PASS_CORE_STATE_VERIFIED**, not FULL: upstream scheduler is NOT_SERIALIZED_BY_UPSTREAM; GradScaler serialization is not equivalent to independently verified restoration.

## 4. Independent physical test B: RX 7900 XTX / gfx1100

- Device: AMD Radeon RX 7900 XTX, gfx1100; Windows 11 reported build 10.0.26300.0; driver 32.0.21030.2001.
- Run ID: R22A5N-GFX1100-20261117-A.
- Original file manifest: **83 independent SHA256 entries**. https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n/R22A5N-GFX1100-20261117-A/SHA256MANIFEST.json
- Actual child-loaded binary: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n/R22A5N-GFX1100-20261117-A/02_runtime_identity/g0_child_identity.json
- Official candidate cold no-host-STL trials: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n/R22A5N-GFX1100-20261117-A/03_nostl_candidate/nostl_candidate_trial1.json and https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n/R22A5N-GFX1100-20261117-A/03_nostl_candidate/nostl_candidate_trial2.json
- Official pre-fix control: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n/R22A5N-GFX1100-20261117-A/04_nostl_negative_control/nostl_prefit_control.json
- Original full gate result: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/78098c59ad7f89951a0fe99d4b39e2752b803932/reports/r22a5n/R22A5N-GFX1100-20261117-A/09_acceptance/nightly_acceptance.json
- Exact merged-integration HEAD re-audit: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/actions/runs/44068854644 ; includes a new derived acceptance JSON artifact, never overwriting historical raw receipts.

Result: nine independent gates PKG/LK/G0/G1/G2/G3/G4/G5/G7 PASS; real GPU training and AMP events, checkpoints, cross-process resume and workers=8 child process provenance verified. An initial truncated worker census failed closed; the failed attempt remains recorded and the corrected original observation passes the strict worker proof. No failure receipts were hidden.

G5 is **RESUME_PASS_CORE_STATE_VERIFIED** only.

## 5. Critical causal contrast (both real physical hosts)

- Matched no-host-STL spatial BatchNorm reproducer uses actual shape [20,100,35,45], real HIPRTC compilation and GPU synchronization; each official post-fix Nightly candidate had two independent cold-cache PASS trials.
- In a separate **official pre-fix 7.14.1** environment on each host, the loaded MIOpen.dll SHA256 was **e97891df7ea0ba2b6eda703bd69499521dc9a38300fe626f412b5544dec647bc** (MIOpen 3.5.2.cd957402; marker 0). Its negative control reliably produced HIPRTC_ERROR_COMPILATION and the original 'type_traits' file not found failure.
- Both physical positive processes loaded the exact **f9312c3e...40cb6** Nightly DLL (marker 2) and completed finite outputs and gradients with no supplied host STL, no header injection, no library swap.
- This is strong causal evidence that the released Nightly build resolved this Windows HIPRTC issue. It is **not** a formal bit-for-bit A/B of all non-MIOpen dependencies and is not a Stable wheel run.

## 6. Independent audit and merge freeze

- gfx1151 evidence source PR: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/pull/22 (merged).
- gfx1100 evidence source PR: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/pull/23 (merged).
- Frozen dual-architecture integration SHA: 78098c59ad7f89951a0fe99d4b39e2752b803932.
- Combined post-merge exact-HEAD GitHub Actions: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/actions/runs/44068854644 — **419 CPU contract tests PASS, 902 release verifier checks / 0 violations, gfx1100 83-entry manifest PASS and strict gfx1100 9/9 full evidence replay PASS.**
- gfx1151 final strict gate report and its 106-file manifest are committed at the same frozen SHA; the post-merge CI is a CPU-only **replay of original physical GPU receipts**, not a fresh hardware measurement.
- Both raw-data failure/retry attempts were preserved, checkpoint bytes committed or separately accounted for according to their evidence ledgers. Historical verdicts were not silently rewritten.

Aggregated (and strictly scoped) verdict: **NIGHTLY_DUAL_ARCH_FUNCTIONAL_EVIDENCE_COMPLETE**. This is two separately measured physical GPU machines, not simultaneous GPU experimentation.

## 7. Requested concrete AMD Release Engineering actions

1. **Identify the Windows SDK/PyTorch publication DRI.** Who owns rocm_sdk_libraries Windows packaging and the associated torch, torchvision, and gfx1100/gfx1151 device wheel release set?
2. **Nominate the first eligible target.** Stable vs RC, exact ROCm SDK / MIOpen build and Git ancestry including f0a5d266, package repository/index URL, planned Python ABI and Windows gfx coverage. Please share the first obtainable artifact URL/manifest once it exists. An approximate target release date is helpful if known; we do not infer one.
3. **Clarify package compatibility.** Can the Windows SDK Libraries package be republished alone with a fully supported compatible set, or does it require a coordinated versioned torch/torchvision/SDK/device-wheel release? We are not requesting a manual end-user DLL patch.
4. **Make no-host-STL HIPRTC a Windows release gate.** Execute the spatial-BatchNorm fwd/bwd case with intentionally unavailable host MSVC STL and a clean MIOpen cache, capture loaded DLL identity and validate outputs/gradients. Detect unexpected CPU fallback, missing device kernel images, mixed wheel families and unintended manual workarounds.
5. **Confirm platform-support terminology.** Does a successful fixed Stable release qualify GPU training as a supported Windows use case, or is additional AMD product/support qualification required beyond these experiments?

We can run the **first official eligible Stable/RC build** on physical gfx1151 and gfx1100 using the existing SHA256 locking and strict numeric/worker/AMP/resume evidence tools. We will post both results and failures back to Issue #15862, including the required **G9 fresh Windows install** assessment. No target release date, owner or Stable acceptance is claimed without an AMD response.

## 8. What this handoff does NOT assert

- **No OFFICIAL_STABLE_PASS:** only the specific 2026-11-16 Nightly has these two physical full evidence packs. Existing Stable Windows 10.1.0 has been observed pre-fix; current official index has not shown a newer eligible Stable version.
- **No clean Windows G9 PASS:** these were controlled physical Windows test hosts, not the independent fresh-system user installation flow.
- **No FULL_TRAINING_STATE_RESTORE_PASS:** scheduler was not serialized by the tested upstream Ultralytics version.
- **No all-architecture/all-YOLO certification:** validated YOLO26n lifecycle on two gfx targets, not every Radeon GPU or task/size. RX 9070 XT/gfx1201 testing has a **separate Draft community test plan** (PR #24), with no gfx1201 GPU measurements yet.
- **No hidden code patch:** production software installed from official AMD Nightly wheels plus published Ultralytics 8.4.214, not a private wheel or patched Ultralytics tree.

### Final ask

Release Engineering: please identify the Windows owner and **first published supported Windows Stable/RC package set containing the merged MIOpen f0a5d266 fix**, so we can close the last user-facing gap: *official install → Radeon GPU YOLO train / validate / save / resume, without replacing DLLs or shipping header workarounds*.