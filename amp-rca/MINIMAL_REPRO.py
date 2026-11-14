"""G3 MINIMAL_REPRO — Ultralytics AMP precheck flakiness on Windows ROCm.

Reproduces, in one process, the exact mechanism that makes
ultralytics.utils.checks.check_amp disable AMP on Windows ROCm stacks:

  1. check_amp's probe = post-NMS boxes FP32 vs autocast(fp16), allclose(atol=0.5)
  2. on this stack the fp16 conv numerics vary ~0.2-0.8 px depending on which
     MIOpen conv kernel is selected (kernel selection depends on MIOpen cache
     state), so the same probe can PASS in one MIOpen cache context and FAIL
     in another — with identical detection counts, classes and finiteness.

Run inside the environment under test:

    python MINIMAL_REPRO.py            # prints per-column FP32-vs-AMP diffs
    python MINIMAL_REPRO.py --json out.json

Expected output: identical shapes (no NMS flipping), finite everywhere,
per-column max|diff| — coordinate columns typically dominate. If the max
coordinate diff exceeds 0.5, check_amp returns False and Ultralytics training
silently falls back to FP32 even though AMP itself is numerically healthy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=None, help="defaults to ultralytics WEIGHTS_DIR/yolo26n.pt")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    from ultralytics import YOLO
    from ultralytics.utils import ASSETS, WEIGHTS_DIR
    from ultralytics.utils.torch_utils import autocast

    weights = Path(args.weights) if args.weights else (WEIGHTS_DIR / "yolo26n.pt")
    if not weights.is_file():
        weights = Path("yolo26n.pt")
    model = YOLO(str(weights))
    device = torch.device("cuda:0")
    im = ASSETS / "bus.jpg"
    batch = [im] * 8
    imgsz = max(256, int(model.stride.max() * 4))

    a = model(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data  # FP32
    with autocast(enabled=True, device=device.type):
        b = model(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data  # AMP
    cols = ["x1", "y1", "x2", "y2", "conf", "cls"]
    report = {
        "torch": torch.__version__, "hip": torch.version.hip or "",
        "device": torch.cuda.get_device_name(0),
        "imgsz": imgsz, "n_detections_fp32": int(a.shape[0]), "n_detections_amp": int(b.shape[0]),
        "shape_equal": a.shape == b.shape,
        "fp32_finite": bool(torch.isfinite(a).all()), "amp_finite": bool(torch.isfinite(b).all()),
        "check_amp_would_pass": a.shape == b.shape
        and bool(torch.allclose(a.float(), b.float(), atol=0.5)),
        "per_column_max_abs_diff": {},
        "overall_max_abs_diff": float((a.float() - b.float()).abs().max()),
    }
    if a.shape == b.shape:
        diff = (a.float() - b.float()).abs()
        for i, c in enumerate(cols[: a.shape[1]]):
            report["per_column_max_abs_diff"][c] = float(diff[:, i].max())
    print(json.dumps(report, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
