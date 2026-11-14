"""G4.1 — long-run training: detect on coco128 (public), 30 epochs, FP32.

Records per-epoch loss/metrics/lr/GPU-mem from results.csv, wall time per
epoch, and completion status. A crash keeps partial evidence (JSON written
incrementally per epoch via callback).

    python tests/g4_long_run.py --out ../raw/g4_long_run_coco128.json
"""
import json
import math
import sys
import time
from pathlib import Path

import torch
from ultralytics import YOLO

OUT_PATH = Path(sys.argv[sys.argv.index("--out") + 1])
OUT = {"environment": {}, "epochs": {}, "summary": {}, "limitations": []}


def env_meta():
    OUT["environment"] = {
        "torch": torch.__version__, "hip": torch.version.hip or "",
        "device": torch.cuda.get_device_name(0),
        "total_mem_gb": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1),
    }


def epoch_end(trainer):
    e = str(trainer.epoch)
    OUT["epochs"][e] = {
        "fitness": float(trainer.fitness) if trainer.fitness is not None else None,
        "lr_pg0": float(trainer.optimizer.param_groups[0]["lr"]),
        "epoch_time_s": round(trainer.epoch_time, 2),
        "gpu_mem_gb": round(float(torch.cuda.max_memory_allocated()) / 2**30, 2),
    }
    OUT_PATH.write_text(json.dumps(OUT, indent=2))
    print(f"[epoch {e}] fitness={OUT['epochs'][e]['fitness']:.4f} "
          f"time={OUT['epochs'][e]['epoch_time_s']}s mem={OUT['epochs'][e]['gpu_mem_gb']}GB", flush=True)


def save():
    OUT_PATH.write_text(json.dumps(OUT, indent=2))


def main():
    env_meta()
    model = YOLO("yolo26n.pt")
    model.add_callback("on_fit_epoch_end", epoch_end)
    t0 = time.time()
    try:
        model.train(data="coco128.yaml", epochs=30, device=0, workers=2, amp=False,
                    name="g4_coco128_30ep", exist_ok=True, plots=False, seed=42,
                    batch=16, imgsz=640)
        OUT["summary"]["status"] = "COMPLETED"
    except Exception as exc:
        OUT["summary"]["status"] = f"EXCEPTION {type(exc).__name__}: {exc}"
        OUT["summary"]["first_error"] = str(exc)[:800]
        save()
        raise
    wall = time.time() - t0
    fit = [v["fitness"] for v in OUT["epochs"].values() if v["fitness"] is not None]
    OUT["summary"].update({
        "epochs_completed": len(OUT["epochs"]),
        "wall_hours": round(wall / 3600, 3),
        "fitness_first": fit[0] if fit else None,
        "fitness_last": fit[-1] if fit else None,
        "fitness_finite_all": all(math.isfinite(f) for f in fit),
        "peak_gpu_mem_gb": max(v["gpu_mem_gb"] for v in OUT["epochs"].values()),
        "mean_epoch_time_s": round(sum(v["epoch_time_s"] for v in OUT["epochs"].values()) / max(len(OUT["epochs"]), 1), 2),
    })
    save()
    print(f"SUMMARY {json.dumps(OUT['summary'])}", flush=True)


if __name__ == "__main__":
    main()
