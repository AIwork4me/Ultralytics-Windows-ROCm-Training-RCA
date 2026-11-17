# Release Engineering Handoff — MIOpen PR #13437 Windows validation status

**For owner review before any external send. Draft — not sent.**

## One-paragraph summary

The MIOpen no-host-STL fix (ROCm/rocm-libraries#13437, merged `f0a5d266`,
tracking #15862) is now physically validated on **both** Windows RDNA
architectures using the **same audited official nightly bytes**: gfx1151
(Radeon 8060S, PR #22) and gfx1100 (Radeon RX 7900 XTX, this PR). On
gfx1100, a stock `pip` install of the 2026-11-16 nightly snapshot
(torch `2.16.0a0+rocm10.3.0a20261116` cp312 + matching torchvision/SDK
wheels + released `ultralytics==8.4.214`) — with **zero workarounds**
(no DLL swaps, no STL header injection, no HIPRTC shims, no CPU
fallbacks) — completes the full Windows YOLO lifecycle: real FP16 AMP
training with effective AdamW updates, checkpoint kill/resume across
processes, workers=8 multiprocess DataLoader, and GPU inference.

## Identity anchors

- SDK Libraries wheel `rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl`
  SHA256 `b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0`
  (byte-identical artifact verified independently on both hosts)
- Embedded `MIOpen.dll` SHA256
  `f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6`,
  build `3.6.3.25f28906`, GitHub compare `f0a5d266…25f28906`:
  ahead_by=1074, behind_by=0
- Pre-fix negative control (official 7.14.1 wheel DLL `e97891df…`,
  marker=0) still fails with the exact #15862 signature
  (`MIOpenBatchNormFwdTrainSpatial.cpp`, `HIPRTC_ERROR_COMPILATION`,
  `'type_traits' file not found`) under matched no-STL isolation —
  strong paired behavioral evidence (not single-variable; version sets
  differ, disclosed in both packs)

## gfx1100 gate matrix (all independently recomputed from raw evidence)

PKG ✓ LK ✓ G0 ✓ G1(2 cold trials + matched control) ✓ G2(9/9 ops,
FP16 GEMM + GPU NMS) ✓ G3(YOLO26n/COCO128/3ep) ✓ G4(FP16 AMP,
11/7/4 steps, 4 scaler backoffs) ✓ G5(kill→resume→infer; scheduler
NOT serialized by upstream → honestly capped at CORE_STATE_VERIFIED)
✓ G7(16/16 simultaneous spawn_main workers, orphan recomputed CLEAN)
→ **R22A5N_GFX1100_NIGHTLY_EVIDENCE_AUDITED_PASS**

## What is still blocked

- **Stable channel**: `stable.repo.amd.com` (10.1.0) MIOpen is still
  pre-fix. Users on Stable Windows wheels keep hitting #15862. Request:
  ship the fix (or a 10.2.0rc3+ candidate) into an official Stable
  Windows release.
- **G9 clean-Windows acceptance** is defined and ready to run the moment
  a Stable (or RC) candidate exists: fresh Windows + fresh venv + stock
  `pip install` + full lifecycle, no dev-host artifacts in the path.
- Dual-arch claim `NIGHTLY_DUAL_ARCH_FUNCTIONAL_EVIDENCE_COMPLETE` is
  supported by both physical packs but remains gated on owner review of
  PR #22 + this PR.

## Reviewer pointers

- gfx1100 pack: `reports/r22a5n/R22A5N-GFX1100-20261117-A/`
  (start: `09_acceptance/nightly_acceptance.json`, then
  `R22A5N_GFX1100_FINAL_REPORT_zh.md`)
- gfx1151 pack: `reports/r22a5n1/R22A5N1-GFX1151-20261117-B/` (PR #22)
- Cross-arch comparison + two disclosed engine-hardening deltas
  (G5 verdict semantics; G7 census cmdline capture):
  `R22A5N_GFX1100_VS_GFX1151_COMPARISON.md`
- CPU-only adversarial verification: 61 new + 311 historical tests
  (372/372), repo verifier 902 checks / 0 violations
