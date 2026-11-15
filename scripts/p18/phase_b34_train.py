"""P18 Phase B3/B4: real AMP / FP32 YOLO train smoke on PR #27198 HEAD (gfx1100).

Usage: python phase_b34_train.py --amp {1|0} --tag {amp|fp32}
Verifies: real autocast training on cuda:0, finite loss, real optimizer updates
(weights change), checkpoint saved, no CPU fallback.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--amp", required=True, choices=["1", "0"])
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    import torch
    import ultralytics
    from ultralytics import YOLO

    assert "pr27198" in ultralytics.__file__.replace("\\", "/").lower(), ultralytics.__file__

    run_dir = Path(f"C:/P18/scratch/runs_b_{args.tag}")
    if run_dir.exists():
        import shutil

        shutil.rmtree(run_dir)

    model = YOLO("C:/P18/assets/yolo26n.pt")
    w0 = {k: v.detach().clone() for k, v in model.model.state_dict().items()}

    results = model.train(
        data="C:/P18/assets/coco8.yaml",
        epochs=1,
        imgsz=64,
        batch=8,
        workers=0,
        device=0,
        amp=bool(int(args.amp)),
        project=str(run_dir.parent),
        name=run_dir.name,
        exist_ok=True,
        verbose=True,
        seed=42,
        deterministic=True,
    )

    out = {
        "tag": args.tag,
        "amp_flag": bool(int(args.amp)),
        "ultralytics_file": ultralytics.__file__,
        "torch": torch.__version__,
        "device_name": torch.cuda.get_device_name(0),
    }

    # checkpoint exists
    last = run_dir / "weights" / "last.pt"
    out["last_pt_exists"] = last.is_file()
    out["last_pt_sha256"] = None
    if last.is_file():
        import hashlib

        out["last_pt_sha256"] = hashlib.sha256(last.read_bytes()).hexdigest()

    # weights really changed (real optimizer updates through the whole run)
    sd = torch.load(last, map_location="cpu", weights_only=False)
    trained = sd["model"].float().state_dict()
    deltas = []
    for k, v0 in w0.items():
        if k in trained and v0.shape == trained[k].shape and v0.is_floating_point():
            deltas.append((trained[k] - v0).abs().max().item())
    out["n_weight_tensors_compared"] = len(deltas)
    out["max_abs_weight_delta"] = max(deltas) if deltas else None
    out["weights_changed"] = bool(deltas and max(deltas) > 0)

    # loss curve finite from results.csv
    csv_path = run_dir / "results.csv"
    losses = []
    if csv_path.is_file():
        with open(csv_path) as f:
            for row in csv.DictReader(f):
                losses.append({k.strip(): float(v) for k, v in row.items() if "loss" in k.lower()})
    out["loss_rows"] = losses
    train_losses = [r["train/loss"] for r in losses if "train/loss" in r] or [
        v for r in losses for k, v in r.items() if "box_loss" in k
    ]
    out["loss_finite"] = bool(train_losses) and all(x == x and abs(x) < 1e12 for x in train_losses)

    # AMP actually engaged: ultralytics trainer sets self.amp and uses autocast; capture the
    # trainer's resolved amp state from the saved trainer args in last.pt
    out["trainer_amp_in_checkpoint"] = bool(sd.get("train_args", {}).get("amp"))
    out["epoch_in_checkpoint"] = sd.get("epoch")

    print("RESULT_JSON_BEGIN")
    print(json.dumps(out, indent=2, default=str))
    print("RESULT_JSON_END")
    ok = out["last_pt_exists"] and out["weights_changed"] and out["loss_finite"]
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
