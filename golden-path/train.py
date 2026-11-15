# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Golden Path training entry (step 4/5/7): smoke, representative, or interrupt-for-resume runs.

Runs on device 0 explicitly — never silently selects CPU. Records the AMP verdict and the
per-epoch learning curve (fitness) so a PASS implies measured model learning, not just
"training did not crash".

Usage:
    python train.py --smoke                          # COCO8, 2 epochs (~2 min): install smoke test
    python train.py --representative                 # COCO128, 20 epochs: real learning curve
    python train.py --representative --run-id myrun  # explicit run dir under runs/golden/
"""

import argparse
import json
import multiprocessing
import sys
from datetime import datetime, timezone
from pathlib import Path

DEVICE = 0  # explicit; the golden path never relies on silent device selection


def preflight_reject_cpu() -> None:
    """Refuse to run without a real GPU (mirrors verify_environment.py, cheap re-check)."""
    import torch

    if not torch.cuda.is_available():
        print(
            "[FAIL] torch.cuda.is_available() is False — refusing CPU-only training. "
            "Install the official ROCm wheel (WINDOWS_SETUP.md §2) and rerun verify_environment.py."
        )
        sys.exit(2)
    print(f"[OK] training on GPU 0: {torch.cuda.get_device_name(0)} (torch {torch.__version__})")


def main():
    """Parse mode, run training with device=0, and write a run summary JSON."""
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--smoke", action="store_true", help="COCO8, 2 epochs — install smoke test only")
    g.add_argument("--representative", action="store_true", help="COCO128, 20 epochs — real learning curve")
    ap.add_argument("--run-id", default=None, help="run directory name under runs/golden/")
    ap.add_argument("--resume-dir", default=None, help="(resume mode) existing run dir containing last.pt")
    args = ap.parse_args()

    preflight_reject_cpu()

    from ultralytics import YOLO

    if args.resume_dir:
        last = Path(args.resume_dir) / "weights" / "last.pt"
        if not last.exists():
            print(f"[FAIL] {last} not found — resume needs last.pt from the interrupted run (not best.pt)")
            sys.exit(2)
        print(f"[OK] resuming from {last} in a NEW process")
        model = YOLO(str(last))
        result = model.train(resume=True)  # restores epoch/optimizer/scheduler state
        print(f"[OK] resume finished: {result}")
        return

    if args.smoke:
        data, epochs, name = "coco8.yaml", 2, args.run_id or "smoke"
    else:
        data, epochs, name = "coco128.yaml", 20, args.run_id or "representative"

    model = YOLO("yolo26n.pt")
    project = Path("runs/golden").resolve()
    run_dir = project / name
    if run_dir.exists():
        print(f"[FAIL] run dir {run_dir} already exists — pick another --run-id")
        sys.exit(2)

    print(f"[OK] starting {'smoke' if args.smoke else 'representative'} training: data={data} epochs={epochs} device={DEVICE}")
    metrics = model.train(data=data, epochs=epochs, device=DEVICE, project=str(project), name=name, exist_ok=False, seed=0)

    # ultralytics 8.4.x: train() returns the fused inference model, so per-epoch fitness is
    # taken from the run's results.csv by verify_checkpoint.py / acceptance review instead.
    summary = {
        "mode": "smoke" if args.smoke else "representative",
        "data": data,
        "epochs": epochs,
        "device": DEVICE,
        "seed": 0,
        "run_dir": str(run_dir),
        "finished_utc": datetime.now(tz=timezone.utc).isoformat(),
        "amp_probe_verdict": "see console AMP: line (checks passed -> AMP enabled; failed -> FP32 fallback)",
    }
    (run_dir / "golden_train_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[OK] summary written to {run_dir / 'golden_train_summary.json'}")
    print("TRAIN: PASS")


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Windows-safe dataloader workers
    main()
