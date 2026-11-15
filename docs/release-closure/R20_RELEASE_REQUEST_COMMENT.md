# R20 — Ready-to-post upstream comment for ROCm/rocm-libraries#15862

**Status:** Draft ready for manual posting. **Not posted automatically:** the connected GitHub integration returned HTTP 403 `Resource not accessible by integration` when attempting to comment on the upstream issue on 2026-11-15.

**Target:** https://github.com/ROCm/rocm-libraries/issues/15862

---

**R20 release-engineering handoff — request for owner, artifact cut-point, and Windows acceptance gate (2026-11-15)**

Thanks for the merged MIOpen fix in #13437 (`f0a5d266`) and the subsequent TheRock submodule bump in [ROCm/TheRock#9359](https://github.com/ROCm/TheRock/pull/9359). The source side is complete; the remaining gap is **official Windows binary publication**.

Current public Windows wheel indexes still list:
- [Legacy `whl-multi-arch`](https://repo.amd.com/rocm/whl-multi-arch/rocm-sdk-libraries/): latest `rocm_sdk_libraries` **7.14.1**.
- [Stable `whl-next`](https://stable.repo.amd.com/rocm/whl-next/rocm-sdk-libraries/): latest `rocm_sdk_libraries` **10.1.0**. The Windows 10.1.0 wheel was byte-audited and the shipped `MIOpen.dll` traces to pre-fix `39d8d603`; the original **no-host-STL HIPRTC BatchNorm** reproducer still fails, while the merged-source reference build passes. These are *artifact-specific* results, not a claim that every ordinary YOLO run fails.

Could the Windows ROCm / TheRock release owner help close four decisions?

1. **Ownership and source cut:** Who owns the Windows `rocm_sdk_libraries` release, and which release branch/snapshot will first include `f0a5d266`?
2. **First official candidate:** Can a candidate Windows wheel with an exact filename/version, source manifest, SHA256, and index URL be made available via the appropriate dev/RC channel for independent testing on **gfx1100 + gfx1151**?
3. **Packaging route:** Is an ABI/dependency-compatible `rocm_sdk_libraries` patch/post-release possible against the current torch/ROCm 10.1.0 packages, or must this wait for a full SDK/framework release? This is a release-team decision; I am **not** assuming interchangeability.
4. **Promotion gate:** Could a fresh-cache Windows BatchNorm forward/backward test with host MSVC STL unavailable, no injected HIPRTC headers, and no replaced DLL be required before stable publication?

We can validate a candidate on real **Windows RX 7900 XTX (gfx1100)** and **Radeon 8060S (gfx1151)** and return wheel/DLL provenance, original no-STL reproducer, then Ultralytics v8.4.214 training + AMP + checkpoint/resume evidence. Note: unrelated intermittent `hipErrorInvalidKernelFile` faults will remain separately tracked rather than assumed fixed by this patch.

**R20 release handoff / evidence and pass criteria:** [R20_RELEASE_READINESS_20261115.md](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/blob/work/windows-rocm-training-release-closure/docs/release-closure/R20_RELEASE_READINESS_20261115.md)

**Request:** please assign or route this issue to the release owner and identify the target official artifact or candidate channel. No additional source-code change is being requested here.
