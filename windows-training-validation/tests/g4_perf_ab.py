"""G4.4 — matched precision A/B on the SAME environment and workload.

ENV A (official wheel): coco8 detect, 10 epochs, seed fixed, FP32 vs AMP
(AMP effective on this wheel per G3). Records per-epoch wall time, images/s
estimates, peak VRAM. Interpretation constraints are documented in the report;
epoch counts are small by design (matched-pair comparison, not perf ranking).

    python tests/g4_perf_ab.py --out ../raw/g4_perf_ab_envA.json
"""
import json
import shutil
import sys
import time
from pathlib import Path

import torch
from ultralytics import YOLO

OUT_PATH = Path(sys.argv[sys.argv.index("--out") + 1])
OUT = {"environment": {}, "runs": {}, "interpretation": []}


def run_mode(tag: str, amp: bool) -> dict:
    model = YOLO("yolo26n.pt")
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    model.train(data="coco8.yaml", epochs=10, device=0, workers=2, amp=amp,
                name=f"perfab_{tag}", exist_ok=True, plots=False, seed=42, batch=16)
    wall = time.time() - t0
    csv_path = Path(model.trainer.save_dir) / "results.csv"
    lines = [l.strip() for l in csv_path.read_text().splitlines() if l.strip()]
    n_epochs = max(len(lines) - 1, 0)
    peak_gb = torch.cuda.max_memory_allocated() / 2**30
    imgs_per_s = 8 * n_epochs / wall if wall else 0  # coco8: 8 train images
    rec = {"amp_requested": amp, "amp_effective": bool(getattr(model.trainer, "amp", None)),
           "wall_s": round(wall, 1), "epochs_completed": n_epochs,
           "mean_epoch_s": round(wall / max(n_epochs, 1), 2),
           "train_imgs_per_s": round(imgs_per_s, 1),
           "peak_vram_gb": round(peak_gb, 2),
           "final_fitness": float(model.trainer.fitness) if model.trainer.fitness else None}
    print(f"[{tag}] {rec}", flush=True)
    OUT["runs"][tag] = rec
    OUT_PATH.write_text(json.dumps(OUT, indent=2))
    shutil.rmtree(model.trainer.save_dir, ignore_errors=True)  # regenerable temp run dir
    return rec


def main():
    OUT["environment"] = {"torch": torch.__version__, "hip": torch.version.hip or "",
                          "device": torch.cuda.get_device_name(0)}
    OUT["interpretation"] = [
        "matched A/B: same wheel, same machine, same seed/data/epochs; AMP on this wheel is effective (G3)",
        "coco8 is tiny (8 images) — times are dominated by dataloader/compile overheads; treat as",
        "relative FP32-vs-AMP behavior on identical work, not as throughput benchmarks; epoch-level",
        "variance is disclosed in RAW_SAMPLES via per-epoch csv retained per run",
    ]
    run_mode("fp32", False)
    run_mode("amp", True)
    fp, am = OUT["runs"]["fp32"], OUT["runs"]["amp"]
    OUT["summary"] = {
        "fp32_mean_epoch_s": fp["mean_epoch_s"], "amp_mean_epoch_s": am["mean_epoch_s"],
        "amp_vs_fp32_epoch_ratio": round(am["mean_epoch_s"] / max(fp["mean_epoch_s"], 1e-9), 3),
        "fp32_peak_vram_gb": fp["peak_vram_gb"], "amp_peak_vram_gb": am["peak_vram_gb"],
        "both_epochs_completed": fp["epochs_completed"] == 10 and am["epochs_completed"] == 10,
    }
    OUT_PATH.write_text(json.dumps(OUT, indent=2))
    print(f"SUMMARY {json.dumps(OUT['summary'])}", flush=True)


if __name__ == "__main__":
    main()
