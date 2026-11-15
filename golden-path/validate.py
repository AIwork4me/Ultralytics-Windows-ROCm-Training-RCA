# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Golden Path validation (step 6): load the trained best.pt and run real validation on device 0.

Usage:
    python validate.py --run-dir runs/golden/representative
"""

import argparse
import json
import multiprocessing
import sys
from datetime import datetime, timezone
from pathlib import Path

DEVICE = 0  # explicit


def main():
    """Load best.pt from the run dir, validate on device 0, write metrics JSON."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="runs/golden/representative", help="run dir produced by train.py")
    args = ap.parse_args()

    best = Path(args.run_dir) / "weights" / "best.pt"
    if not best.exists():
        print(f"[FAIL] {best} not found — run train.py first (best.pt is the best-validation checkpoint)")
        sys.exit(2)

    import torch
    from ultralytics import YOLO

    if not torch.cuda.is_available():
        print("[FAIL] no GPU visible — refusing CPU-only validation")
        sys.exit(2)

    model = YOLO(str(best))
    metrics = model.val(device=DEVICE)  # uses the dataset from the checkpoint's args

    out = {
        "checkpoint": str(best),
        "validated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "device": DEVICE,
        "map50_95": float(metrics.box.map),
        "map50": float(metrics.box.map50),
        "results_dir": str(metrics.save_dir),
    }
    out_path = Path(args.run_dir) / "golden_val_metrics.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print("VALIDATE: PASS")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
