# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Golden Path resume (step 7): continue an INTERRUPTED run from last.pt in a NEW process.

`resume=True` restores epoch/optimizer/scheduler state — this is different from re-opening a
finished model. The run must have been actually interrupted (killed process) after at least
one valid last.pt checkpoint.

Usage:
    python resume.py --run-dir runs/golden/resumetest
"""

import argparse
import multiprocessing
import sys
from pathlib import Path


def main():
    """Resume the interrupted run from its last.pt on device 0."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="run dir of the interrupted training")
    args = ap.parse_args()

    last = Path(args.run_dir) / "weights" / "last.pt"
    if not last.exists():
        print(f"[FAIL] {last} not found — resume needs last.pt from the interrupted run (not best.pt)")
        sys.exit(2)

    import torch
    from ultralytics import YOLO

    if not torch.cuda.is_available():
        print("[FAIL] no GPU visible — refusing CPU-only resume")
        sys.exit(2)

    print(f"[OK] resuming {last} on device 0 in a NEW process (pid {multiprocessing.current_process().pid})")
    model = YOLO(str(last))
    model.train(resume=True)  # continues to the original epoch target with restored state
    print("RESUME: PASS")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
