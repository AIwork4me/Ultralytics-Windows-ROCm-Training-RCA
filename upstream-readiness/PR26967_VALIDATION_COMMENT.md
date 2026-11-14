# Comment draft for ultralytics/ultralytics PR #26967 (check_amp redesign) — Windows ROCm gfx1151 validation data

**Status: READY — submits after g3_checkamp84212_* results land (numbers to fill)**

---

Validation data point from a Windows ROCm (AMD iGPU) environment where the **old** check_amp (8.4.182-era, `amp_allclose` with `atol=0.5` on post-NMS boxes) had a real false-failure mode:

**Environment**: AMD Radeon 8060S (gfx1151, Ryzen AI MAX+ 395 iGPU, shared-memory), Windows 11 build 26200, HIP 7.14.60850, torch 2.12.0+rocm7.14.1 (official AMD wheel), ultralytics 8.4.182 installed (8.4.212 injected via PYTHONPATH for this test).

**Old-check failure mode (8.4.182, on this hardware)**: fp16 conv kernels move post-NMS box coordinates 0.07–0.76 px with identical detections/classes/confidences (Δconf ≤ 0.0043); the verdict flipped **deterministically on MIOpen cache state** — 5/5 PASS at 0.233 px vs 0/5 FAIL at 0.7606 px on the same binary/image (kernel selection, not numerics). Silent FP32 fallback was the result — a healthy AMP stack rejected.

**New check (8.4.212, this PR) on the same machine**:

| cache state | ENV A official MIOpen 3.5.2 | ENV B source-built 3.6.2 |
|---|---|---|
| default USERPROFILE | PENDING | PENDING |
| fresh isolated | PENDING | PENDING |
| warm training context (1-epoch AMP train first — the old-check FAIL state) | PENDING | PENDING |

(filled from `g3_checkamp84212_*.json`; verdicts + log lines)

If all PASS: this redesign resolves the only AMP issue we could find on Windows ROCm — the box-coordinate absolute tolerance was the sole false-failure path we could construct, and the per-layer relative-norm criterion is insensitive to it. One observation: the old check also implicitly exercised the full post-NMS pipeline (NMS + decoding) end-to-end; the new one checks layers in isolation — if a stack ever develops an AMP anomaly **between** layers (accumulation through the head/NMS path), the new check would not see it. We could not construct such a case on real hardware (our adversarial suite failed to produce one), so this is a theoretical note, not a request.

Also validated on this stack with 8.4.182→8.4.212: 7-task training lifecycle (detect/segment/classify/pose/obb/semantic/depth) 14/14 each, AMP training on imagenette2-160 with 887 verified optimizer updates and top-1 0.970 vs FP32 0.973.

Evidence repo: AIwork4me/Ultralytics-Windows-ROCm-Training-RCA (raw JSONs with in-process MIOpen DLL SHA256 provenance).
