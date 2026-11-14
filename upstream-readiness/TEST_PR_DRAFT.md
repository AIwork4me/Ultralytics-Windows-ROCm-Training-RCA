# PR-B DRAFT — Ultralytics: Windows AMD ROCm training regression test

**Target repo**: `ultralytics/ultralytics` · **Status: DRAFT — Owner approval required before any upstream submission**
**Basis**: validated G1/G2 harnesses in this RCA repo (see `windows-training-validation/G1_VERDICT.md`, `G2_VERDICT.md`)

## Purpose

One small, strict test that proves the thing users actually need: *YOLO training really runs
forward → backward → optimizer step on a Windows AMD ROCm GPU and produces a valid checkpoint.*
It must not damage CPU/CUDA CI.

## Proposed test — `tests/test_windows_rocm_training.py`

```python
import pytest
import torch

test = pytest.mark.skipif(
    not (torch.cuda.is_available() and torch.version.hip),
    reason="requires native HIP ROCm GPU (Windows or Linux)",
)

@test
def test_hip_training_primitives_and_lifecycle(tmp_path):
    # 1. MIOpen-sensitive primitive: spatial BatchNorm2d train fwd/bwd (the historical
    #    Windows-failure path, MIOpen issue #3956)
    bn = torch.nn.BatchNorm2d(16).cuda().train()
    y = bn(torch.randn(8, 16, 64, 64, device="cuda"))
    y.mean().backward()
    assert torch.isfinite(y).all() and torch.isfinite(bn.weight.grad).all()

    # 2. One-epoch YOLO26n detect train on coco8 with device=0, amp=False
    from ultralytics import YOLO
    model = YOLO("yolo26n.pt")
    model.train(data="coco8.yaml", epochs=1, device=0, workers=0, amp=False,
                project=tmp_path, exist_ok=True, plots=False, seed=42)
    # 3. Strict completion semantics: 1 results row, finite losses, checkpoint loadable
    import csv
    rows = list(csv.DictReader(open(f"{model.trainer.save_dir}/results.csv")))
    assert len(rows) == 1
    assert all(math.isfinite(float(v)) for k, v in rows[0].items() if "loss" in k and v)
    ckpt = torch.load(f"{model.trainer.save_dir}/weights/last.pt", map_location="cpu", weights_only=False)
    assert "model" in ckpt
```

## Design constraints honored

- Uses the standard install path and public coco8 (tiny, official); no new datasets
- SKIPs cleanly when no HIP GPU (`torch.version.hip` empty) — CUDA CI unaffected; CPU CI unaffected
- No device hardcoding in production code (test-only)
- Strict pass/fail: no print-based PASS; exit codes and assertions only
- Real-GPU enforcement: `torch.version.hip` non-empty + actual forward/backward/optimizer assertions

## CI strategy (separate from this PR)

- GitHub-hosted runners have no AMD GPUs: the test SKIPs there (by design).
- Real validation requires a self-hosted Windows runner with an AMD GPU; see
  `upstream-readiness/G5_VERDICT.md` §CI for the runner spec, security constraints
  (no untrusted-PR execution on credentialed hosts), and JUnit/provenance artifact plan.
- This repo's own evidence of the test passing: `windows-training-validation/raw/g2_detect_fp32.json`
  (lifecycle superset) and `G1` primitive matrix (16/16 × 3 cold homes × STL/no-STL).
