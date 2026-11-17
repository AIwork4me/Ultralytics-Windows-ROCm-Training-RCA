"""G4.1 — long-run training stability harness (rewrite: mission §3.3/§3.4).

    python tests/g4_long_run.py --out ../raw/g4_long_run_<env>.json \
        [--epochs 30] [--data coco128.yaml] [--weights yolo26n.pt] [--batch 16]

Fixes vs the historical harness:
  - epoch accounting: training-epoch callbacks (0..epochs-1) are separated
    from the deliberate upstream final_eval() callback (fires once at index
    == epochs to log best.pt metrics); configured vs observed epochs are
    reconciled and must match, else the record FAILs (§3.3 — the historical
    "31 epochs for 30" was 30 training epochs + 1 final-eval callback)
  - in-process loaded MIOpen DLL SHA256 probe (what the process actually
    loaded, probed AFTER training so lazy loads are covered)
  - per-epoch wall-clock samples + results.csv preserved verbatim (embedded)
  - checkpoint metadata (last.pt epoch/optimizer, best.pt fitness) recorded
  - complete environment identity + immutable run_id output (no overwrite)
  - representative dataset supported (L2); coco128 default retained
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_common import csv_rows, dll_provenance, env_meta, new_run_id, reconcile_epochs, save_immutable, utcnow

OUT: dict = {"environment": {}, "epochs_training": {}, "final_eval": None,
             "wall_samples": [], "summary": {}, "limitations": []}


def epoch_end(trainer):
    rec = {
        "fitness": float(trainer.fitness) if trainer.fitness is not None else None,
        "lr_pg0": float(trainer.optimizer.param_groups[0]["lr"]),
        "epoch_time_s": round(trainer.epoch_time, 2),
        "gpu_mem_gb": round(float(torch.cuda.max_memory_allocated()) / 2**30, 2),
        "wall_s": round(time.time() - OUT["_t0"], 1),
    }
    if trainer.epoch >= OUT["_epochs_configured"]:
        # upstream final_eval() logs best.pt metrics at index == epochs
        OUT["final_eval"] = {"epoch_index": trainer.epoch, **rec,
                             "source": "final_eval() callback (upstream-intentional, "
                                       "trainer.py: log best metrics at step epochs+1)"}
        print(f"[final_eval @ index {trainer.epoch}] fitness={rec['fitness']}", flush=True)
    else:
        OUT["epochs_training"][str(trainer.epoch)] = rec
        OUT["wall_samples"].append({"epoch": trainer.epoch, "epoch_time_s": rec["epoch_time_s"]})
        print(f"[epoch {trainer.epoch}] fitness={rec['fitness']:.4f} "
              f"time={rec['epoch_time_s']}s mem={rec['gpu_mem_gb']}GB", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--data", default="coco128.yaml")
    ap.add_argument("--weights", default="yolo26n.pt")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--environment-id", default="unknown")
    args = ap.parse_args()

    OUT["run_id"] = args.run_id or new_run_id("g4long")
    OUT["environment_id"] = args.environment_id
    OUT["environment"] = env_meta()
    OUT["args"] = {k: str(v) for k, v in vars(args).items()}
    OUT["_epochs_configured"] = args.epochs
    OUT["_t0"] = time.time()

    from ultralytics import YOLO
    model = YOLO(args.weights)
    model.add_callback("on_fit_epoch_end", epoch_end)
    OUT["started_utc"] = utcnow()
    try:
        model.train(data=args.data, epochs=args.epochs, device=0, workers=args.workers,
                    amp=False, name=f"g4long_{OUT['run_id']}", exist_ok=True, plots=False,
                    seed=42, batch=args.batch, imgsz=args.imgsz)
        OUT["summary"]["status"] = "COMPLETED"
    except Exception as exc:  # noqa: BLE001 — first error surfaces
        OUT["summary"]["status"] = f"EXCEPTION {type(exc).__name__}: {exc}"
        OUT["summary"]["first_error"] = str(exc)[:800]
        OUT["completed_utc"] = utcnow()
        OUT.pop("_t0", None), OUT.pop("_epochs_configured", None)
        save_immutable(Path(args.out), OUT)
        raise

    save_dir = Path(model.trainer.save_dir)
    rows = csv_rows(save_dir / "results.csv")
    fit = [v["fitness"] for v in OUT["epochs_training"].values() if v["fitness"] is not None]
    recon = reconcile_epochs(args.epochs, len(rows),
                             len(OUT["epochs_training"]), 1 if OUT["final_eval"] else 0)
    ck_meta = {}
    last_pt = save_dir / "weights" / "last.pt"
    best_pt = save_dir / "weights" / "best.pt"
    if last_pt.is_file():
        ck = torch.load(last_pt, map_location="cpu", weights_only=False)
        ck_meta["last_pt"] = {"epoch_field": ck.get("epoch"),
                              "has_optimizer": ck.get("optimizer") is not None,
                              "note": "final-strip semantics: epoch=-1/optimizer stripped "
                                      "after completion (documented 8.4.182 behavior)"}
    if best_pt.is_file():
        ck_b = torch.load(best_pt, map_location="cpu", weights_only=False)
        ck_meta["best_pt"] = {"fitness": ck_b.get("fitness"), "epoch_field": ck_b.get("epoch")}

    # results.csv preserved verbatim (B-F9: the old harness deleted run dirs)
    OUT["results_csv_text"] = (save_dir / "results.csv").read_text(encoding="utf-8") \
        if (save_dir / "results.csv").is_file() else None

    OUT["epoch_reconciliation"] = recon
    OUT["checkpoint_metadata"] = ck_meta
    OUT["dll_provenance"] = dll_provenance()   # in-process probe AFTER training
    wall = time.time() - OUT["_t0"]
    OUT["summary"].update({
        "epochs_completed": len(OUT["epochs_training"]),
        "epochs_configured": args.epochs,
        "epochs_reconciled": recon["reconciled"],
        "final_eval_callback_present": bool(OUT["final_eval"]),
        "wall_hours": round(wall / 3600, 3),
        "fitness_first": fit[0] if fit else None,
        "fitness_last": fit[-1] if fit else None,
        "fitness_finite_all": all(math.isfinite(f) for f in fit),
        "peak_gpu_mem_gb": max((v["gpu_mem_gb"] for v in OUT["epochs_training"].values()),
                               default=None),
        "mean_epoch_time_s": round(sum(v["epoch_time_s"] for v in OUT["epochs_training"].values())
                                   / max(len(OUT["epochs_training"]), 1), 2),
        "epoch_time_spread_s": [min(v["epoch_time_s"] for v in OUT["epochs_training"].values()),
                                max(v["epoch_time_s"] for v in OUT["epochs_training"].values())],
        "save_dir": str(save_dir),
    })
    OUT["completed_utc"] = utcnow()
    OUT.pop("_t0", None)
    OUT.pop("_epochs_configured", None)
    save_immutable(Path(args.out), OUT)
    print(f"SUMMARY {json.dumps(OUT['summary'])}", flush=True)
    if not recon["reconciled"]:
        print("EPOCH-RECONCILIATION FAILED — record kept for triage", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
