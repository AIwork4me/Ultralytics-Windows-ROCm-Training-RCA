# Comment draft for ultralytics/ultralytics PR #26967 (check_amp redesign) — Windows ROCm gfx1151 validation data

**Status: READY — submits after g3_checkamp84212_* results land (numbers to fill)**

---

Validation data point from a Windows ROCm (AMD iGPU) environment where the **old** check_amp (8.4.182-era, `amp_allclose` with `atol=0.5` on post-NMS boxes) had a real false-failure mode:

**Environment**: AMD Radeon 8060S (gfx1151, Ryzen AI MAX+ 395 iGPU, shared-memory), Windows 11 build 26200, HIP 7.14.60850, torch 2.12.0+rocm7.14.1 (official AMD wheel), ultralytics 8.4.182 installed (8.4.212 injected via PYTHONPATH for this test).

**Old-check failure mode (8.4.182, on this hardware)**: fp16 conv kernels move post-NMS box coordinates 0.07–0.76 px with identical detections/classes/confidences (Δconf ≤ 0.0043); the verdict flipped **deterministically on MIOpen cache state** — 5/5 PASS at 0.233 px vs 0/5 FAIL at 0.7606 px on the same binary/image (kernel selection, not numerics). Silent FP32 fallback was the result — a healthy AMP stack rejected.

**New check (8.4.212, this PR) on the same machine**:

| cache state | ENV A official MIOpen 3.5.2 | ENV B source-built 3.6.2 hybrid |
|---|---|---|
| default USERPROFILE | **PASS** (9.1 s, deterministic) | **CRASH — `torch.AcceleratorError: CUDA error: invalid kernel file`** (3/3 attempts) |
| warm training context (1-epoch AMP train first — the old-check FAIL state) | **PASS** (AMP effective under 8.4.212) | **CRASH** (the in-trainer probe raises → training aborts) |

ENV A: the redesign fully resolves the box-tolerance false-failure — the previously cache-flipping stack now passes deterministically.

ENV B: on a source-built-MIOpen hybrid (kernel fingerprint DB `gfx115128.HIP.fdb.txt` unreadable in the package bin dir), the per-layer fp16 recompute hits `hipErrorInvalidKernelFile` and — because this PR also removed 8.4.182's `try/except` guards — the exception propagates into `trainer.train()` setup and **aborts the run** instead of disabling AMP with a warning. Two asks:

1. **Restore the resilience contract**: wrap the probe forward in `except Exception → LOGGER.error(...) + return False` (KeyboardInterrupt/SystemExit still propagate). On 8.4.182 a probe-time backend failure degraded to FP32 training; on 8.4.197+ it crashes training. Draft diff + regression test: `upstream-readiness/patches/CHECKAMP_ROBUSTNESS_PR.md` (happy to open this as a PR).
2. The `hipErrorInvalidKernelFile` itself is a MIOpen-side packaging/integrity issue (tracked separately with ROCm) — Ultralytics cannot prevent it, but it is exactly the failure class the removed guards existed for.

If all PASS: this redesign resolves the only AMP issue we could find on Windows ROCm — the box-coordinate absolute tolerance was the sole false-failure path we could construct, and the per-layer relative-norm criterion is insensitive to it. One observation: the old check also implicitly exercised the full post-NMS pipeline (NMS + decoding) end-to-end; the new one checks layers in isolation — if a stack ever develops an AMP anomaly **between** layers (accumulation through the head/NMS path), the new check would not see it. We could not construct such a case on real hardware (our adversarial suite failed to produce one), so this is a theoretical note, not a request.

Also validated on this stack (8.4.182 lifecycle, 8.4.212 check): 7-task training lifecycle 14/14 each; matched FP32-vs-AMP classify on imagenette2-160 with 887 verified optimizer updates, top-1 0.970 (AMP) vs 0.973 (FP32).

Evidence repo: AIwork4me/Ultralytics-Windows-ROCm-Training-RCA (raw JSONs with in-process MIOpen DLL SHA256 provenance).
