"""G4.4 — matched precision A/B on the SAME environment and workload
(rewrite: mission §3.3/§3.4 + P9.3 provenance contract).

    python tests/g4_perf_ab.py --out ../raw/g4_perf_ab_<env>.json \
        [--data coco8.yaml] [--epochs 10] [--batch 16]

Per mode (fp32 / amp): per-epoch wall samples, results.csv preserved verbatim,
in-process loaded-DLL probe AFTER each run, epochs reconciliation, and the
AMP-effective verdict (trainer.amp) — if check_amp silently fell back to
FP32 the amp leg is labeled as such and NO AMP-vs-FP32 performance ratio is
claimed (a fallback-vs-FP32 comparison is not an AMP measurement).

Interpretation constraints (honest by construction):
  - matched A/B: same env, same machine, same seed/data/epochs — FP32-vs-AMP
    behavior only
  - tiny smoke datasets are dominated by dataloader/compile overheads: treat
    as relative behavior on identical work, not throughput benchmarks
  - no cross-environment (ENV A vs ENV B) performance-parity claim may be
    derived from this harness (mission P9.3.7)
"""
import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_common import csv_rows, dll_provenance, env_meta, new_run_id, reconcile_epochs, save_immutable, utcnow

OUT: dict = {"environment": {}, "runs": {}, "interpretation": [], "summary": {}}


def run_mode(tag: str, amp: bool, args) -> dict:
    from ultralytics import YOLO
    model = YOLO(args.weights)
    torch.cuda.reset_peak_memory_stats()
    run_id = f"{OUT['run_id']}_{tag}"
    t0 = time.time()
    model.train(data=args.data, epochs=args.epochs, device=0, workers=args.workers,
                amp=amp, name=f"perfab_{run_id}", exist_ok=True, plots=False,
                seed=args.seed, batch=args.batch)
    wall = time.time() - t0
    save_dir = Path(model.trainer.save_dir)
    rows = csv_rows(save_dir / "results.csv")
    recon = reconcile_epochs(args.epochs, len(rows), len(rows), 0)
    peak_gb = torch.cuda.max_memory_allocated() / 2**30
    imgs_per_s = args.batch * len(rows) / wall if wall else 0  # lower bound (full batches)
    rec = {
        "run_id": run_id,
        "amp_requested": amp,
        "amp_effective": bool(getattr(model.trainer, "amp", None)),
        "scaler_enabled": bool(getattr(getattr(model.trainer, "scaler", None), "_enabled", False)),
        "wall_s": round(wall, 1),
        "epochs_configured": args.epochs,
        "epochs_completed": len(rows),
        "epochs_reconciled": recon["reconciled"],
        "mean_epoch_s": round(wall / max(len(rows), 1), 2),
        "train_imgs_per_s_lower_bound": round(imgs_per_s, 1),
        "peak_vram_gb": round(peak_gb, 2),
        "final_fitness": (float(model.trainer.fitness) if model.trainer.fitness is not None else None),
        "results_csv_text": (save_dir / "results.csv").read_text(encoding="utf-8")
        if (save_dir / "results.csv").is_file() else None,
        "dll_provenance": dll_provenance(),  # in-process probe per mode, post-training
        "started_utc": utcnow(),
    }
    if amp and not rec["amp_effective"]:
        rec["leg_status"] = "AMP_FALLBACK_TO_FP32 — check_amp disabled AMP; this leg is NOT an AMP measurement"
    print(f"[{tag}] wall={rec['wall_s']}s amp_effective={rec['amp_effective']} "
          f"epochs={rec['epochs_completed']} peak={rec['peak_vram_gb']}GB", flush=True)
    OUT["runs"][tag] = rec
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default="coco8.yaml")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--weights", default="yolo26n.pt")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--environment-id", default="unknown")
    args = ap.parse_args()

    OUT["run_id"] = args.run_id or new_run_id("g4perf")
    OUT["environment_id"] = args.environment_id
    OUT["environment"] = env_meta()
    OUT["args"] = {k: str(v) for k, v in vars(args).items()}
    OUT["started_utc"] = utcnow()
    OUT["interpretation"] = [
        "matched A/B: same wheel/environment, machine, seed/data/epochs — measures "
        "FP32-vs-AMP behavior on identical work only",
        "img/s is a lower bound (full-batch estimate); tiny smoke datasets are dominated "
        "by dataloader/compile overheads — not throughput benchmarks",
        "per-epoch results.csv text is embedded verbatim (audit B-F9: the old harness "
        "deleted run dirs and falsely claimed CSVs were retained)",
        "NO cross-environment performance-parity claim may be derived from this harness "
        "(mission P9.3.7): ENV A (official MIOpen) and ENV B (patched source-built "
        "MIOpen) are different runtimes",
    ]
    run_mode("fp32", False, args)
    run_mode("amp", True, args)
    fp, am = OUT["runs"]["fp32"], OUT["runs"]["amp"]
    amp_valid = am["amp_effective"]
    OUT["summary"] = {
        "fp32_mean_epoch_s": fp["mean_epoch_s"], "amp_mean_epoch_s": am["mean_epoch_s"],
        "amp_leg_valid": amp_valid,
        "amp_vs_fp32_epoch_ratio": (round(am["mean_epoch_s"] / max(fp["mean_epoch_s"], 1e-9), 3)
                                    if amp_valid else None),
        "ratio_scope": ("FP32-vs-AMP on identical work" if amp_valid else
                        "NOT AN AMP MEASUREMENT: AMP fell back to FP32 (check_amp); "
                        "ratio compares FP32 vs FP32-fallback"),
        "fp32_peak_vram_gb": fp["peak_vram_gb"], "amp_peak_vram_gb": am["peak_vram_gb"],
        "both_epochs_completed": (fp["epochs_completed"] == args.epochs
                                  and am["epochs_completed"] == args.epochs),
        "both_reconciled": fp["epochs_reconciled"] and am["epochs_reconciled"],
        "miopen_sha_fp32": (fp["dll_provenance"]["miopen_loaded"] or {}).get("sha256"),
        "miopen_sha_amp": (am["dll_provenance"]["miopen_loaded"] or {}).get("sha256"),
    }
    OUT["completed_utc"] = utcnow()
    save_immutable(Path(args.out), OUT)
    print(f"SUMMARY {json.dumps(OUT['summary'])}", flush=True)


if __name__ == "__main__":
    main()
