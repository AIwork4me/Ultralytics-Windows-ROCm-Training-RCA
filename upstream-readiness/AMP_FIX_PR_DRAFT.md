# PR-C DRAFT — Ultralytics: make the AMP precheck robust to fp16 coordinate quantization

**Target repo**: `ultralytics/ultralytics` · **Status: DRAFT — Owner approval required before any upstream submission** (per mission §2.4)
**Basis**: G3 RCA on Windows ROCm (gfx1151), `windows-training-validation/raw/g3_amp_*`, `amp-rca/ROOT_CAUSE.md`

## Problem

`check_amp`'s probe (`amp_allclose`, `ultralytics/utils/checks.py` @ 8.4.182) compares
FP32 vs autocast(fp16) predictions as raw post-NMS tensors:

```python
a = m(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data  # FP32
b = ... autocast ...                                                    # AMP
return a.shape == b.shape and torch.allclose(a, b.float(), atol=0.5)
```

On Windows ROCm stacks, fp16 conv kernels move box coordinates by **0.15–0.76 px** with
**identical detections, classes and confidences (Δconf ≤ 0.004)**. When the delta exceeds the
hard-coded 0.5 px, the check reports "Anomalies were detected with AMP on your system" and
training **silently falls back to FP32**. The outcome flips on MIOpen cache state (kernel
selection) — measured deterministic 5/5 PASS in one state and 0/5 FAIL in another on the same
binary/image (`g3_amp_envB_patched.json` vs `g3_amp_envB_defaulthome.json`). A 0.5 px absolute
tolerance on coordinates is far tighter than fp16 activation quantization; the check therefore
rejects healthy AMP stacks.

## Minimal fix (one function, ~15 lines)

Match detections geometrically instead of element-wise: identical count, per-class IoU ≥ 0.95
matched boxes, conf within 0.05 — equivalent detections, not pixel-equal tensors:

```python
def amp_allclose(m, im):
    batch = [im] * 8
    imgsz = max(256, int(model.stride.max() * 4))
    a = m(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data  # FP32 inference
    with autocast(enabled=True, device=device.type):
        b = m(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data  # AMP inference
    del m
    if a.shape != b.shape or a.shape[0] == 0:
        return a.shape == b.shape
    a, b = a.float(), b.float()
    if not (torch.isfinite(a).all() and torch.isfinite(b).all()):
        return False
    if not torch.equal(a[:, 5], b[:, 5]) or (a[:, 4] - b[:, 4]).abs().max() > 0.05:
        return False                       # class set or confidence materially different
    iou = torchvision.ops.box_iou(a[:, :4], b[:, :4])
    return bool((iou.diagonal() >= 0.95).all())   # same boxes within fp16 coordinate noise
```

(diagonal IoU applies since both tensors are in deterministic prediction order on the same
input; fall back to shape check when empty.)

## Regression test (cross-platform, no new hardware assumptions)

`tests/test_cuda.py`-style unit test using a tiny in-memory model is preferable; minimal viable
test: assert `check_amp` does not flip between two runs on the same process with an intervening
MIOpen cache change on ROCm, and that a synthetic 1-px coordinate perturbation between `a` and
`b` does NOT disable AMP while a class flip DOES. CPU-safe path unchanged.

## Evidence links

- `amp-rca/ROOT_CAUSE.md` (layered RCA), `amp-rca/PRECISION_COMPARISON.csv`
- Raw JSONs: `g3_amp_envB_patched.json` (PASS 5/5, max diff 0.2333), `g3_amp_envB_defaulthome.json` (FAIL 0/5, max diff 0.7606, conf ≤ 0.0043, cls = 0)
- Real AMP training success once the check passes: `g3_amp10_envA.json` (GradScaler anneal + real updates + fitness 0.662→0.696)

## Reviewer checklist

- [ ] Does not weaken real anomaly detection: NaN/Inf still fail; class flips still fail; conf drift > 0.05 still fails
- [ ] No change to CPU/MPS early-return path
- [ ] No device-specific hardcoding (pure numerics)
- [ ] Works on CUDA NVIDIA (behavior unchanged — element diffs there are already ≤ atol)
