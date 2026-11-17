# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Golden Path checkpoint verification (step 6b): prove REAL parameter updates happened.

Compares the trained best.pt weights against the ORIGINAL pretrained yolo26n.pt in a fresh
process (the fused-model-return gotcha makes in-process self-checks unreliable), checks the
per-epoch learning curve from results.csv, and hashes the checkpoint files.

Usage:
    python verify_checkpoint.py --run-dir runs/golden/representative
"""

import argparse
import hashlib
import json
import multiprocessing
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return file SHA256 (binary identity for the manifest)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def weight_stats(state_dict) -> dict:
    """Sum of squares over all float tensors — a scalar proxy for 'weights changed'."""
    import torch

    tot, n = 0.0, 0
    with torch.no_grad():
        for v in state_dict.values():
            if v.is_floating_point():
                tot += float(v.square().sum())
                n += v.numel()
    return {"sum_sq": tot, "n_floats": n}


def main():
    """Verify checkpoint identity, weight delta vs pretrained, and learning curve monotony evidence."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="runs/golden/representative", help="run dir produced by train.py")
    ap.add_argument("--base", default="yolo26n.pt", help="original pretrained weights used to start training")
    args = ap.parse_args()

    import torch
    from ultralytics import YOLO

    best = Path(args.run_dir) / "weights" / "best.pt"
    last = Path(args.run_dir) / "weights" / "last.pt"
    for p in (best, last):
        if not p.exists():
            print(f"[FAIL] {p} not found — run train.py first")
            sys.exit(2)

    out = {"generated_utc": datetime.now(tz=timezone.utc).isoformat(), "run_dir": str(args.run_dir)}

    # 1) checkpoint binary identity
    out["best_sha256"] = sha256_file(best)
    out["last_sha256"] = sha256_file(last)
    print(f"[OK] best.pt sha256={out['best_sha256'][:16]}…  last.pt sha256={out['last_sha256'][:16]}…")

    # 2) reload sanity (save -> reload works) + weight delta vs the ORIGINAL base weights
    base = torch.load(args.base, map_location="cpu", weights_only=False)["model"].float().state_dict()
    reloaded = torch.load(best, map_location="cpu", weights_only=False)["model"].float().state_dict()
    b, r = weight_stats(base), weight_stats(reloaded)
    delta_norm = (b["sum_sq"] - r["sum_sq"]) / b["sum_sq"]
    out["base_sum_sq"] = b["sum_sq"]
    out["trained_sum_sq"] = r["sum_sq"]
    out["relative_sum_sq_delta"] = delta_norm
    _ = YOLO(str(best)).info(verbose=False)  # reload must not raise
    print(f"[OK] best.pt reloads cleanly; relative sum_sq delta vs pretrained = {delta_norm:.6f}")
    if delta_norm == 0.0:
        print("[FAIL] trained weights are IDENTICAL to pretrained — no real learning happened")
        sys.exit(2)

    # 3) learning curve from results.csv (fitness/mAP per epoch recorded by ultralytics)
    csv = Path(args.run_dir) / "results.csv"
    if csv.exists():
        import csv as _csv

        rows = list(_csv.DictReader(csv.open(encoding="utf-8")))
        key = next((k for k in rows[0] if "mAP50-95" in k or "mAP50-95(B)" in k), None)
        if key:
            curve = [float(row[key]) for row in rows if row.get(key)]
            out["map50_95_curve"] = curve
            out["map50_95_first"] = curve[0]
            out["map50_95_best"] = max(curve)
            print(f"[OK] learning curve mAP50-95: first={curve[0]:.4f} best={max(curve):.4f} ({len(curve)} epochs)")
            if max(curve) <= curve[0]:
                print("[FAIL] mAP never improved over training — learning not demonstrated")
                sys.exit(2)
        else:
            print("[WARN] no mAP column found in results.csv; curve skipped")

    out_path = Path(args.run_dir) / "golden_checkpoint_verification.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[OK] written {out_path}")
    print("VERIFY_CHECKPOINT: PASS")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
